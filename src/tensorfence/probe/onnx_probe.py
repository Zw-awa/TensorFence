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
from .base import ProbeArtifacts, ProbeError


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
        warnings=[],
    )


def probe_onnx_model(model_path: str | Path, out_dir: str | Path, output_format: str = "both") -> ProbeArtifacts:
    facts = collect_onnx_model_facts(model_path)
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
    )
