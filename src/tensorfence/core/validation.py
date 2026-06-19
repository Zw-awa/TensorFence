from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .contracts import ModelContract


@dataclass(frozen=True)
class ContractIssue:
    severity: Literal["error", "warning"]
    code: str
    field: str
    message: str


def _error(code: str, field: str, message: str) -> ContractIssue:
    return ContractIssue("error", code, field, message)


def _warning(code: str, field: str, message: str) -> ContractIssue:
    return ContractIssue("warning", code, field, message)


def _spatial_dims(contract: ModelContract) -> tuple[int, int] | None:
    shape = contract.input.shape
    if len(shape) != 4:
        return None
    if contract.preprocess.output_layout == "NCHW":
        return shape[2], shape[3]
    return shape[1], shape[2]


def validate_contract(contract: ModelContract) -> list[ContractIssue]:
    issues: list[ContractIssue] = []

    if len(contract.input.shape) != 4:
        issues.append(
            _error(
                "input.shape.rank",
                "input.shape",
                "detection contracts should start with a 4D input tensor",
            )
        )

    if any(dim <= 0 for dim in contract.input.shape):
        issues.append(
            _error(
                "input.shape.value",
                "input.shape",
                "input shape must be fully positive in this foundation schema",
            )
        )

    if not contract.input.semantic.strip():
        issues.append(_error("input.semantic.missing", "input.semantic", "input semantic must be explicit"))

    if not contract.outputs:
        issues.append(_error("outputs.empty", "outputs", "at least one output tensor must be declared"))

    seen_output_names: set[str] = set()
    for index, output in enumerate(contract.outputs):
        field_prefix = f"outputs[{index}]"
        if output.name in seen_output_names:
            issues.append(
                _error(
                    "output.name.duplicate",
                    f"{field_prefix}.name",
                    f"duplicate output tensor name: {output.name}",
                )
            )
        seen_output_names.add(output.name)

        if not output.semantic.strip():
            issues.append(
                _error(
                    "output.semantic.missing",
                    f"{field_prefix}.semantic",
                    "output semantic must be explicit",
                )
            )

    if contract.task == "detection" and contract.decode is None:
        issues.append(_error("decode.missing", "decode", "detection contracts should declare decode rules"))

    if contract.preprocess.input_layout is None:
        issues.append(
            _warning(
                "preprocess.input_layout.missing",
                "preprocess.input_layout",
                "preprocess input layout should be declared explicitly to avoid ambiguity",
            )
        )

    if contract.decode is not None:
        if contract.decode.num_classes <= 0:
            issues.append(_error("decode.num_classes.invalid", "decode.num_classes", "num_classes must be positive"))

        if not contract.decode.strides:
            issues.append(_error("decode.strides.missing", "decode.strides", "decode strides must be declared"))

        if contract.decode.mode == "anchor_based" and not contract.decode.anchors:
            issues.append(_error("decode.anchors.missing", "decode.anchors", "anchor-based decode requires anchors"))

        if contract.decode.head_names and len(contract.decode.head_names) != len(contract.outputs):
            issues.append(
                _warning(
                    "decode.head_names.mismatch",
                    "decode.head_names",
                    "head_names count does not match output tensor count",
                )
            )

    if contract.nms is None:
        issues.append(_warning("nms.missing", "nms", "nms rules are not declared yet"))

    if contract.quantization.enabled:
        if not contract.quantization.calibration_dataset:
            issues.append(
                _error(
                    "quantization.calibration_dataset.missing",
                    "quantization.calibration_dataset",
                    "quantization requires a calibration dataset reference",
                )
            )
        if not contract.quantization.calibration_samples or contract.quantization.calibration_samples <= 0:
            issues.append(
                _error(
                    "quantization.calibration_samples.invalid",
                    "quantization.calibration_samples",
                    "quantization requires a positive calibration sample count",
                )
            )

    target_size = contract.preprocess.resize.target_size
    spatial_dims = _spatial_dims(contract)
    if spatial_dims is not None:
        expected_h, expected_w = spatial_dims
        if list(target_size) != [expected_h, expected_w]:
            issues.append(
                _error(
                    "preprocess.resize.mismatch",
                    "preprocess.resize.target_size",
                    f"resize target size {target_size} does not match fixed input spatial dims {[expected_h, expected_w]}",
                )
            )

    return issues


def has_errors(issues: list[ContractIssue]) -> bool:
    return any(issue.severity == "error" for issue in issues)

