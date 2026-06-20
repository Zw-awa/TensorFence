from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..artifacts.contracts.draft_contract import (
    DraftConfirmation,
    DraftContractReport,
    DraftFieldDecision,
    DraftIssue,
)
from ..artifacts.facts.model_facts import ModelFacts, TensorFact
from ..core.contracts import DecodeSpec, ModelContract, NmsSpec, PreprocessSpec, QuantizationSpec, ResizeSpec, TensorSpec
from ..core.validation import validate_contract
from .schema import DraftRuleSet


class DraftContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class DraftContractBundle:
    contract: ModelContract
    report: DraftContractReport


def _require_concrete_shape(tensor: TensorFact, field_name: str) -> list[int]:
    if tensor.shape is None:
        raise DraftContractError(f"{field_name} tensor {tensor.name} has no shape information")

    concrete: list[int] = []
    for dim in tensor.shape:
        if not isinstance(dim, int):
            raise DraftContractError(
                f"{field_name} tensor {tensor.name} has non-concrete shape {tensor.shape}; use a fixed-shape export first"
            )
        concrete.append(int(dim))
    return concrete


def _select_input(model_facts: ModelFacts, rules: DraftRuleSet) -> TensorFact:
    if not model_facts.inputs:
        raise DraftContractError("model facts do not contain any input tensors")

    selection = rules.selection.input
    if selection.strategy == "first":
        return model_facts.inputs[0]

    assert selection.name is not None
    for tensor in model_facts.inputs:
        if tensor.name == selection.name:
            return tensor
    raise DraftContractError(f"input tensor not found in model facts: {selection.name}")


def _select_outputs(model_facts: ModelFacts, rules: DraftRuleSet) -> list[TensorFact]:
    if not model_facts.outputs:
        raise DraftContractError("model facts do not contain any output tensors")

    selection = rules.selection.outputs
    if selection.strategy == "all":
        return list(model_facts.outputs)

    selected: list[TensorFact] = []
    for name in selection.names:
        matched = next((tensor for tensor in model_facts.outputs if tensor.name == name), None)
        if matched is None:
            raise DraftContractError(f"output tensor not found in model facts: {name}")
        selected.append(matched)
    return selected


def _resolve_task(rules: DraftRuleSet, task_override: str) -> str:
    return task_override if task_override != "auto" else rules.defaults.task


def _resolve_family(rules: DraftRuleSet, family_override: str) -> str:
    if family_override != "auto":
        return family_override
    if rules.templates.decode.enabled:
        return rules.templates.decode.family
    return rules.defaults.family


def _render_name(template: str, model_facts: ModelFacts, task: str, family: str) -> str:
    model_name = Path(model_facts.model_path).stem
    try:
        return template.format(model_name=model_name, task=task, family=family)
    except KeyError as exc:
        raise DraftContractError(f"unknown name template variable: {exc.args[0]}") from exc


def _resolve_input_layout(shape: list[int], rules: DraftRuleSet) -> str:
    rank = len(shape)
    layout_rules = rules.mapping.input.layout_from_rank
    if rank == 4:
        return layout_rules.rank4
    if rank == 2 and layout_rules.rank2 is not None:
        return layout_rules.rank2
    raise DraftContractError(f"no input layout rule for input tensor rank {rank}")


def _infer_spatial_size(shape: list[int], output_layout: str) -> list[int]:
    if len(shape) != 4:
        raise DraftContractError("preprocess resize target size can only be inferred from 4D input tensors")
    if output_layout == "NCHW":
        return [int(shape[2]), int(shape[3])]
    if output_layout == "NHWC":
        return [int(shape[1]), int(shape[2])]
    raise DraftContractError(f"cannot infer resize target size for preprocess output layout {output_layout}")


def _build_preprocess(shape: list[int], rules: DraftRuleSet) -> PreprocessSpec:
    template = rules.templates.preprocess
    target_size = template.resize.target_size or _infer_spatial_size(shape, template.output_layout)
    return PreprocessSpec.model_validate(
        {
            "input_color_space": template.input_color_space,
            "output_color_space": template.output_color_space,
            "input_layout": template.input_layout,
            "output_layout": template.output_layout,
            "resize": {
                "mode": template.resize.mode,
                "target_size": target_size,
                "interpolation": template.resize.interpolation,
                "keep_aspect_ratio": template.resize.keep_aspect_ratio,
            },
            "normalize": template.normalize.model_dump(mode="python") if template.normalize is not None else None,
            "pad_value": template.pad_value,
        }
    )


def _build_decode(output_names: list[str], rules: DraftRuleSet, family: str) -> DecodeSpec | None:
    template = rules.templates.decode
    if not template.enabled:
        return None

    head_names = template.head_names or output_names
    return DecodeSpec(
        family=family,
        mode=template.mode,
        num_classes=int(template.num_classes),
        strides=list(template.strides),
        anchors=template.anchors,
        head_names=head_names,
        reg_max=template.reg_max,
        score_activation=template.score_activation,
        box_activation=template.box_activation,
    )


def _build_nms(rules: DraftRuleSet) -> NmsSpec | None:
    template = rules.templates.nms
    if not template.enabled:
        return None
    return NmsSpec(
        score_threshold=template.score_threshold,
        iou_threshold=template.iou_threshold,
        class_agnostic=template.class_agnostic,
        max_detections=template.max_detections,
        method=template.method,
    )


def _build_quantization(rules: DraftRuleSet) -> QuantizationSpec:
    template = rules.templates.quantization
    return QuantizationSpec(
        enabled=template.enabled,
        calibration_dataset=template.calibration_dataset,
        calibration_samples=template.calibration_samples,
        match_preprocess=template.match_preprocess,
    )


def build_draft_contract_bundle(
    model_facts: ModelFacts,
    rules: DraftRuleSet,
    rules_path: str | Path,
    generated_contract_path: str | Path,
    task_override: Literal["auto", "detection", "classification", "segmentation", "pose", "ocr"] = "auto",
    family_override: Literal["auto", "yolo", "ppyoloe"] = "auto",
    facts_path: str | Path | None = None,
) -> DraftContractBundle:
    decisions: list[DraftFieldDecision] = []
    issues: list[DraftIssue] = []
    confirmations: list[DraftConfirmation] = []

    def record(
        path: str,
        value: object,
        source: Literal["facts", "rules", "default", "override"],
        confidence: Literal["high", "medium", "low"] = "high",
        note: str | None = None,
    ) -> None:
        decisions.append(DraftFieldDecision(path=path, value=value, source=source, confidence=confidence, note=note))

    task = _resolve_task(rules, task_override)
    family = _resolve_family(rules, family_override)
    input_fact = _select_input(model_facts, rules)
    output_facts = _select_outputs(model_facts, rules)

    input_shape = _require_concrete_shape(input_fact, "input")
    input_layout = _resolve_input_layout(input_shape, rules)
    input_dtype = input_fact.dtype or rules.mapping.input.dtype_fallback
    output_names = [fact.name for fact in output_facts]

    record("task", task, "override" if task_override != "auto" else "rules")
    record("name", _render_name(rules.defaults.name, model_facts, task, family), "rules", note="rendered from rule template")
    record("source_framework", rules.defaults.source_framework, "rules", confidence="medium")
    record("target_runtime", rules.defaults.target_runtime, "rules")
    record("input.name", input_fact.name, "facts")
    record("input.shape", input_shape, "facts")
    record("input.dtype", input_dtype, "facts" if input_fact.dtype is not None else "rules")
    record("input.layout", input_layout, "rules", confidence="medium", note="layout selected from rank mapping")
    record("input.semantic", rules.mapping.input.semantic, "rules")

    outputs: list[TensorSpec] = []
    for index, output_fact in enumerate(output_facts):
        output_shape = _require_concrete_shape(output_fact, "output")
        output_dtype = output_fact.dtype or rules.mapping.outputs.dtype_fallback
        record(f"outputs[{index}].name", output_fact.name, "facts")
        record(f"outputs[{index}].shape", output_shape, "facts")
        record(f"outputs[{index}].dtype", output_dtype, "facts" if output_fact.dtype is not None else "rules")
        record(f"outputs[{index}].layout", rules.mapping.outputs.layout, "rules", confidence="medium")
        record(
            f"outputs[{index}].semantic",
            rules.mapping.outputs.semantic,
            "rules",
            confidence="low",
            note="semantic label is rule-based, not graph-inferred",
        )
        outputs.append(
            TensorSpec(
                name=output_fact.name,
                shape=output_shape,
                dtype=output_dtype,
                layout=rules.mapping.outputs.layout,
                semantic=rules.mapping.outputs.semantic,
            )
        )

    preprocess = _build_preprocess(input_shape, rules)
    record("preprocess.input_layout", preprocess.input_layout, "rules", confidence="medium")
    record("preprocess.output_layout", preprocess.output_layout, "rules", confidence="medium")
    record("preprocess.resize.target_size", preprocess.resize.target_size, "facts" if rules.templates.preprocess.resize.target_size is None else "rules")

    decode = _build_decode(output_names, rules, family)
    if decode is not None:
        record("decode.family", decode.family, "override" if family_override != "auto" else "rules")
        record("decode.num_classes", decode.num_classes, "rules", confidence="medium")
        record("decode.strides", decode.strides, "rules", confidence="medium")
        record(
            "decode.head_names",
            decode.head_names,
            "facts" if not rules.templates.decode.head_names else "rules",
            confidence="medium",
        )

    nms = _build_nms(rules)
    quantization = _build_quantization(rules)
    record("quantization.enabled", quantization.enabled, "rules")
    if quantization.enabled:
        record("quantization.calibration_dataset", quantization.calibration_dataset, "rules", confidence="medium")
        record("quantization.calibration_samples", quantization.calibration_samples, "rules", confidence="medium")

    contract = ModelContract(
        name=_render_name(rules.defaults.name, model_facts, task, family),
        task=task,
        source_framework=rules.defaults.source_framework,
        target_runtime=rules.defaults.target_runtime,
        input=TensorSpec(
            name=input_fact.name,
            shape=input_shape,
            dtype=input_dtype,
            layout=input_layout,
            semantic=rules.mapping.input.semantic,
        ),
        outputs=outputs,
        preprocess=preprocess,
        decode=decode,
        nms=nms,
        quantization=quantization,
        notes=list(rules.notes),
    )

    confirmations.append(
        DraftConfirmation(
            path="preprocess",
            reason="preprocess is template-driven and cannot be proven from graph facts alone",
            suggested_action="verify color order, resize mode, normalization, and pad value against the original pipeline",
        )
    )
    confirmations.append(
        DraftConfirmation(
            path="outputs",
            reason="output semantics were assigned by rules, not inferred from graph meaning",
            suggested_action="confirm tensor order and semantics against the exporting framework",
        )
    )
    if decode is not None:
        confirmations.append(
            DraftConfirmation(
                path="decode",
                reason="decode settings come from rules and common conventions, not from reliable graph semantics",
                suggested_action="verify family, strides, num_classes, and head_names",
            )
        )
    confirmations.append(
        DraftConfirmation(
            path="source_framework",
            reason="the original source framework cannot be recovered reliably from imported ONNX facts",
            suggested_action="set source_framework to the actual training/export framework if known",
        )
    )
    if not quantization.enabled:
        confirmations.append(
            DraftConfirmation(
                path="quantization",
                reason="quantization is disabled in the draft",
                suggested_action="if the RKNN path uses INT8, fill in calibration_dataset and calibration_samples",
            )
        )

    if len(outputs) > 1:
        issues.append(
            DraftIssue(
                code="outputs.multiple",
                severity="warning",
                message="multiple outputs were selected; verify output order and decode head mapping manually",
                path="outputs",
            )
        )

    for issue in validate_contract(contract):
        issues.append(
            DraftIssue(
                code=issue.code,
                severity="error" if issue.severity == "error" else "warning",
                message=issue.message,
                path=issue.field,
            )
        )

    report = DraftContractReport(
        model_path=model_facts.model_path,
        facts_path=str(facts_path) if facts_path is not None else None,
        rules_path=str(rules_path),
        task=task,
        family=family,
        generated_contract_path=str(generated_contract_path),
        decisions=decisions,
        issues=issues,
        needs_confirmation=confirmations,
    )
    return DraftContractBundle(contract=contract, report=report)
