from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..artifacts.facts.model_facts import (
    ModelFacts,
    NodeFact,
    TensorFact,
    write_graph_summary_markdown,
    write_model_facts_json,
    write_ops_summary_json,
)
from ..core.contracts import ModelContract
from .base import ProbeArtifacts, ProbeError


_KNOWN_NMS_OPS = {
    "batchednms",
    "batchednmsdynamictrt",
    "efficientnms",
    "efficientnmstrt",
    "matrixnms",
    "multiclassnms",
    "multiclassnms2",
    "multiclassnms3",
    "nms",
    "nonmaxsuppression",
}


def _normalized_name(value: str) -> str:
    return "".join(character for character in value.lower() if character.isalnum())


def _detect_embedded_postprocess(nodes: list[NodeFact], outputs: list[TensorFact]) -> list[str]:
    warnings: list[str] = []
    nms_nodes = [
        node
        for node in nodes
        if _normalized_name(node.op_type) in _KNOWN_NMS_OPS or "nms" in _normalized_name(node.op_type)
    ]
    if nms_nodes:
        evidence = ", ".join(f"{node.name or '<unnamed>'}:{node.op_type}" for node in nms_nodes)
        warnings.append(
            "embedded postprocess detected (high confidence): "
            f"ONNX graph contains NMS operator(s) [{evidence}]. Model outputs may already be filtered; "
            "applying external NMS again can duplicate postprocessing."
        )

    normalized_outputs = {_normalized_name(output.name) for output in outputs}
    final_detection_names = {
        "detectionboxes",
        "detectionscores",
        "detectionclasses",
    }
    matched_names = sorted(normalized_outputs & final_detection_names)
    has_detection_count = bool(normalized_outputs & {"numdetections", "numdets", "validdetections"})
    if not nms_nodes and (has_detection_count or len(matched_names) >= 2):
        evidence = sorted(output.name for output in outputs)
        warnings.append(
            "embedded postprocess possible (medium confidence): "
            f"graph outputs look like final detection results {evidence}. Verify whether decode/NMS already runs "
            "inside the model before applying external postprocessing."
        )

    return warnings


def _is_static_integer(value: int | str | None) -> bool:
    return isinstance(value, int) and value > 0


def _detect_output_contract(nodes: list[NodeFact], outputs: list[TensorFact]) -> dict[str, object]:
    """Classify only output structures with direct graph evidence; otherwise remain unknown."""
    nms_nodes = [
        node
        for node in nodes
        if _normalized_name(node.op_type) in _KNOWN_NMS_OPS or "nms" in _normalized_name(node.op_type)
    ]
    evidence = [f"output {item.name}: shape={item.shape}" for item in outputs]
    if nms_nodes:
        evidence.append("graph contains " + ", ".join(node.op_type for node in nms_nodes))
        return {"kind": "end_to_end_nms", "confidence": "high", "evidence": evidence}

    shapes = [output.shape for output in outputs]
    if len(outputs) == 2 and all(shape is not None and len(shape) == 3 for shape in shapes):
        left, right = shapes  # type: ignore[misc]
        if left[2] == 4 and right[2] == left[1] and _is_static_integer(right[1]):
            return {"kind": "ppyoloe_boxes_scores", "confidence": "high", "evidence": evidence}

    if len(outputs) == 1 and shapes[0] is not None and len(shapes[0]) == 3:
        shape = shapes[0]
        assert shape is not None
        channels = [item for item in shape[1:] if _is_static_integer(item)]
        if any(item >= 5 for item in channels):
            return {
                "kind": "yolo_raw_predictions",
                "confidence": "medium",
                "evidence": evidence + ["single rank-3 prediction tensor; decode/NMS is not proven to be in graph"],
            }

    rank4_outputs = [shape for shape in shapes if shape is not None and len(shape) == 4]
    if len(outputs) >= 6 and len(rank4_outputs) == len(outputs) and len(outputs) % 3 == 0:
        return {
            "kind": "rockchip_yolo_multiscale_heads",
            "confidence": "medium",
            "evidence": evidence + ["multiple rank-4 outputs in groups of three; verify decoder against exporter version"],
        }

    names = {_normalized_name(output.name) for output in outputs}
    if names & {"numdetections", "numdets", "validdetections"}:
        return {"kind": "end_to_end_detections", "confidence": "medium", "evidence": evidence}
    return {
        "kind": "unknown",
        "confidence": "low",
        "evidence": evidence + ["output structure is not a recognized TensorFence contract; do not infer a decoder"],
    }


def contract_postprocess_warnings(
    contract: ModelContract,
    output_contract: dict[str, object],
) -> list[str]:
    """Report only explicit model/contract conflicts; this does not run a decoder."""
    kind = output_contract.get("kind")
    warnings: list[str] = []
    if kind == "end_to_end_nms" and contract.nms is not None:
        warnings.append(
            "duplicate postprocessing detected (high confidence): ONNX graph contains NMS while the contract "
            "also declares external NMS. Disable neither automatically; verify the deployed pipeline ownership."
        )
    if kind == "end_to_end_nms" and contract.decode is not None:
        warnings.append(
            "duplicate decode risk (high confidence): end-to-end/NMS graph output is paired with an external "
            "decode contract. Verify whether the application still decodes final detections."
        )
    if kind == "ppyoloe_boxes_scores" and contract.decode is not None and contract.decode.family != "ppyoloe":
        warnings.append(
            "output contract mismatch (high confidence): model exposes PP-YOLOE boxes+scores, but contract "
            f"declares {contract.decode.family} decode. These decoders are not interchangeable."
        )
    if kind == "rockchip_yolo_multiscale_heads" and contract.decode is None:
        warnings.append(
            "decoder evidence required (medium confidence): model looks like multi-scale Rockchip YOLO heads, "
            "but the contract has no decode specification."
        )
    return warnings


def _import_onnx():
    try:
        import onnx
    except ModuleNotFoundError as exc:
        raise ProbeError("onnx is not installed. Install the tensorfence conda environment first.") from exc
    return onnx


def _dtype_name(tensor_type) -> str | None:
    if tensor_type is None:
        return None
    elem_type = getattr(tensor_type, "elem_type", None)
    if elem_type is None:
        return None
    try:
        onnx = _import_onnx()
        return str(onnx.helper.tensor_dtype_to_np_dtype(elem_type).name)
    except Exception:
        return str(elem_type)


def _shape_from_value_info(value_info) -> list[int | str] | None:
    tensor_type = value_info.type.tensor_type if value_info.type.HasField("tensor_type") else None
    if tensor_type is None or not tensor_type.HasField("shape"):
        return None
    dims: list[int | str] = []
    for dim in tensor_type.shape.dim:
        if dim.HasField("dim_value"):
            dims.append(int(dim.dim_value))
        elif dim.HasField("dim_param"):
            dims.append(dim.dim_param)
        else:
            dims.append("?")
    return dims


def _tensor_fact_from_value_info(value_info) -> TensorFact:
    tensor_type = value_info.type.tensor_type if value_info.type.HasField("tensor_type") else None
    dtype = _dtype_name(tensor_type)
    shape = _shape_from_value_info(value_info)
    return TensorFact(name=value_info.name, dtype=dtype, shape=shape)


def _tensor_fact_from_initializer(initializer) -> TensorFact:
    shape = [int(dim) for dim in initializer.dims]
    try:
        onnx = _import_onnx()
        dtype = str(onnx.helper.tensor_dtype_to_np_dtype(initializer.data_type).name)
    except Exception:
        dtype = str(initializer.data_type)
    return TensorFact(name=initializer.name, dtype=dtype, shape=shape)

def collect_onnx_model_facts(model_path: str | Path) -> ModelFacts:
    onnx = _import_onnx()
    model_file = Path(model_path)
    if not model_file.exists():
        raise ProbeError(f"model file does not exist: {model_file}")
    if model_file.suffix.lower() != ".onnx":
        raise ProbeError(f"probe-model currently only supports ONNX files: {model_file}")

    model = onnx.load_model(str(model_file))
    onnx.checker.check_model(model)
    inferred_model = onnx.shape_inference.infer_shapes(model)
    graph = inferred_model.graph

    inputs = [_tensor_fact_from_value_info(value_info) for value_info in graph.input]
    outputs = [_tensor_fact_from_value_info(value_info) for value_info in graph.output]
    value_info = [_tensor_fact_from_value_info(value) for value in graph.value_info]
    initializers = [_tensor_fact_from_initializer(initializer) for initializer in graph.initializer]

    nodes = [
        NodeFact(
            name=node.name,
            op_type=node.op_type,
            domain=node.domain,
            inputs=list(node.input),
            outputs=list(node.output),
            attribute_names=[attribute.name for attribute in node.attribute],
        )
        for node in graph.node
    ]
    histogram = dict(sorted(Counter(node.op_type for node in nodes).items()))
    warnings = _detect_embedded_postprocess(nodes, outputs)
    output_contract = _detect_output_contract(nodes, outputs)

    return ModelFacts(
        format="onnx",
        model_path=str(model_file),
        ir_version=int(inferred_model.ir_version) if inferred_model.ir_version else None,
        producer_name=inferred_model.producer_name or None,
        producer_version=inferred_model.producer_version or None,
        opsets=[
            {
                "domain": opset.domain,
                "version": int(opset.version),
            }
            for opset in inferred_model.opset_import
        ],
        inputs=inputs,
        outputs=outputs,
        value_info=value_info,
        initializers=initializers,
        nodes=nodes,
        operator_histogram=histogram,
        warnings=warnings,
        output_contract=output_contract,
    )


def probe_onnx_model(
    model_path: str | Path,
    out_dir: str | Path,
    output_format: str = "both",
    contract: ModelContract | None = None,
) -> ProbeArtifacts:
    facts = collect_onnx_model_facts(model_path)
    if contract is not None:
        facts.warnings.extend(contract_postprocess_warnings(contract, facts.output_contract))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    facts_json = write_model_facts_json(facts, out / "model_facts.json")
    ops_json = write_ops_summary_json(facts, out / "ops_summary.json")
    graph_md = None
    if output_format in {"md", "both"}:
        graph_md = write_graph_summary_markdown(facts, out / "graph_summary.md")

    return ProbeArtifacts(
        model_facts_json=facts_json,
        ops_summary_json=ops_json,
        graph_summary_md=graph_md,
        warnings=list(facts.warnings),
    )
