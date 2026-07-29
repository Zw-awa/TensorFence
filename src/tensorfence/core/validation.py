from __future__ import annotations

import math
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
    if contract.preprocess.output_layout == "NHWC":
        return shape[1], shape[2]
    return None


def _channel_count(contract: ModelContract) -> int | None:
    shape = contract.input.shape
    if len(shape) != 4:
        return None
    if contract.preprocess.output_layout == "NCHW":
        return shape[1]
    if contract.preprocess.output_layout == "NHWC":
        return shape[3]
    return None


def _validate_vector(
    issues: list[ContractIssue],
    *,
    field: str,
    values: list[float],
    channels: int | None,
    allow_empty: bool,
    allow_zero: bool = True,
) -> None:
    if not values:
        if not allow_empty:
            issues.append(_error(f"{field}.empty", field, f"{field} must not be empty"))
        return
    if channels is not None and len(values) not in {1, channels}:
        issues.append(
            _error(
                f"{field}.length",
                field,
                f"{field} length must be 1 or match the {channels} output channels",
            )
        )
    if any(not math.isfinite(value) for value in values):
        issues.append(_error(f"{field}.non_finite", field, f"{field} values must be finite"))
    if not allow_zero and any(value == 0 for value in values):
        issues.append(_error(f"{field}.zero", field, f"{field} values cannot be zero"))


def validate_contract(contract: ModelContract) -> list[ContractIssue]:
    issues: list[ContractIssue] = []

    image_layout = contract.preprocess.output_layout in {"NCHW", "NHWC"}
    if image_layout and len(contract.input.shape) != 4:
        issues.append(
            _error(
                "input.shape.rank",
                "input.shape",
                f"{contract.preprocess.output_layout} preprocessing requires a 4D input tensor",
            )
        )

    if contract.task == "detection" and not image_layout:
        issues.append(
            _error(
                "input.layout.detection",
                "preprocess.output_layout",
                "detection contracts require NCHW or NHWC image preprocessing",
            )
        )

    if contract.input.layout is None:
        issues.append(
            _warning(
                "input.layout.missing",
                "input.layout",
                "input tensor layout should be declared explicitly",
            )
        )
    elif (
        contract.preprocess.output_layout != "N/A"
        and contract.input.layout != contract.preprocess.output_layout
    ):
        issues.append(
            _error(
                "input.layout.mismatch",
                "input.layout",
                f"input layout {contract.input.layout} does not match preprocessing output layout "
                f"{contract.preprocess.output_layout}",
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

    if contract.input.dtype not in {"float32", "float"}:
        issues.append(
            _warning(
                "input.dtype.preprocess_unsupported",
                "input.dtype",
                "inspect-image and compare-stages currently produce float32 preprocessing tensors",
            )
        )

    channels = _channel_count(contract)
    output_color_space = (
        contract.preprocess.output_color_space or contract.preprocess.input_color_space
    )
    expected_color_channels = 1 if output_color_space == "GRAY" else 3
    if channels is not None and channels != expected_color_channels:
        issues.append(
            _error(
                "preprocess.channels.mismatch",
                "input.shape",
                f"input declares {channels} channels but {output_color_space} preprocessing produces "
                f"{expected_color_channels}",
            )
        )

    normalize = contract.preprocess.normalize
    if normalize is not None:
        scale_values = normalize.scale if isinstance(normalize.scale, list) else [normalize.scale]
        _validate_vector(
            issues,
            field="preprocess.normalize.scale",
            values=scale_values,
            channels=channels,
            allow_empty=False,
        )
        _validate_vector(
            issues,
            field="preprocess.normalize.mean",
            values=normalize.mean,
            channels=channels,
            allow_empty=True,
        )
        _validate_vector(
            issues,
            field="preprocess.normalize.std",
            values=normalize.std,
            channels=channels,
            allow_empty=True,
            allow_zero=False,
        )

    pad_values = (
        contract.preprocess.pad_value
        if isinstance(contract.preprocess.pad_value, list)
        else [contract.preprocess.pad_value]
    )
    if not pad_values:
        issues.append(
            _error("preprocess.pad_value.empty", "preprocess.pad_value", "pad_value must not be empty")
        )
    else:
        if channels is not None and len(pad_values) not in {1, channels}:
            issues.append(
                _error(
                    "preprocess.pad_value.length",
                    "preprocess.pad_value",
                    f"pad_value length must be 1 or match the {channels} output channels",
                )
            )
        if any(value < 0 or value > 255 for value in pad_values):
            issues.append(
                _error(
                    "preprocess.pad_value.range",
                    "preprocess.pad_value",
                    "pad_value components must be between 0 and 255",
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

    if contract.decode is not None:
        if contract.decode.num_classes <= 0:
            issues.append(_error("decode.num_classes.invalid", "decode.num_classes", "num_classes must be positive"))

        if not contract.decode.strides:
            issues.append(_error("decode.strides.missing", "decode.strides", "decode strides must be declared"))
        elif any(stride <= 0 for stride in contract.decode.strides):
            issues.append(
                _error(
                    "decode.strides.invalid",
                    "decode.strides",
                    "decode strides must contain only positive values",
                )
            )

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

    if contract.nms is not None:
        if not 0 <= contract.nms.score_threshold <= 1:
            issues.append(
                _error(
                    "nms.score_threshold.invalid",
                    "nms.score_threshold",
                    "score_threshold must be between 0 and 1",
                )
            )
        if not 0 <= contract.nms.iou_threshold <= 1:
            issues.append(
                _error(
                    "nms.iou_threshold.invalid",
                    "nms.iou_threshold",
                    "iou_threshold must be between 0 and 1",
                )
            )
        if contract.nms.max_detections <= 0:
            issues.append(
                _error(
                    "nms.max_detections.invalid",
                    "nms.max_detections",
                    "max_detections must be positive",
                )
            )

    if contract.task == "detection" and contract.nms is None:
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
