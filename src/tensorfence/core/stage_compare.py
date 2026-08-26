from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal

import numpy as np

from ..adapters.framework import FrameworkAdapterError, load_framework_outputs, run_framework_outputs
from ..adapters.onnxruntime import OnnxRuntimeAdapterError, load_onnx_outputs, run_onnx_model
from ..adapters.rknn import RknnAdapterError, load_rknn_outputs, run_rknn_model
from ..artifacts.reports.stage_report import (
    StageCompareReport,
    StageFinalSummary,
    StagePairDiffEntry,
    StageRecord,
    StageTensorSummaryEntry,
    write_final_summary_json,
    write_stage_report_html,
    write_stage_report_json,
    write_stage_report_markdown,
    write_tensor_diffs_json,
)
from ..artifacts.tensor_artifact import QuantizationMetadata, TensorArtifactError, load_tensor_artifact
from .contracts import ModelContract, TensorSpec, load_contract
from .diff import TensorDiff, compare_arrays, summarize_array
from .preprocess import PreprocessError, prepare_image
from .validation import has_errors, validate_contract


class StageCompareError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageCompareArtifacts:
    report_json: Path
    tensor_diffs_json: Path
    final_summary_json: Path
    report_markdown: Path | None
    report_html: Path | None


@dataclass(frozen=True)
class ComparisonThresholds:
    max_abs_error: float = 1e-3
    min_cosine_similarity: float = 0.999
    max_mean_relative_error: float = 0.05
    relative_error_epsilon: float = 1e-12
    small_value_threshold: float | None = None
    small_value_relative_threshold: float = 1e-4
    small_value_min_threshold: float = 1e-6
    small_value_max_threshold: float = 1e-3
    small_value_min_count: int = 4
    small_value_min_fraction: float = 0.01
    small_value_zero_fraction: float = 0.95
    clipping_ratio_threshold: float = 0.1
    clipping_ratio_increase: float = 0.05
    clipping_min_count: int = 32

    def validate(self) -> None:
        numeric = {
            "max_abs_error": self.max_abs_error,
            "min_cosine_similarity": self.min_cosine_similarity,
            "max_mean_relative_error": self.max_mean_relative_error,
            "relative_error_epsilon": self.relative_error_epsilon,
            "small_value_relative_threshold": self.small_value_relative_threshold,
            "small_value_min_threshold": self.small_value_min_threshold,
            "small_value_max_threshold": self.small_value_max_threshold,
            "small_value_min_fraction": self.small_value_min_fraction,
            "small_value_zero_fraction": self.small_value_zero_fraction,
            "clipping_ratio_threshold": self.clipping_ratio_threshold,
            "clipping_ratio_increase": self.clipping_ratio_increase,
        }
        if self.small_value_threshold is not None:
            numeric["small_value_threshold"] = self.small_value_threshold
        for name, value in numeric.items():
            if not math.isfinite(value):
                raise StageCompareError(f"comparison threshold {name} must be finite")
        for name in {
            "max_abs_error",
            "max_mean_relative_error",
            "relative_error_epsilon",
            "small_value_relative_threshold",
            "small_value_min_threshold",
            "small_value_max_threshold",
            "small_value_threshold",
            "clipping_ratio_increase",
        }:
            if name not in numeric:
                continue
            value = numeric[name]
            if value < 0:
                raise StageCompareError(f"comparison threshold {name} must be nonnegative")
        if self.relative_error_epsilon <= 0:
            raise StageCompareError("comparison threshold relative_error_epsilon must be positive")
        if self.small_value_min_threshold > self.small_value_max_threshold:
            raise StageCompareError("small_value_min_threshold cannot exceed small_value_max_threshold")
        for name, value in {
            "min_cosine_similarity": self.min_cosine_similarity,
            "small_value_min_fraction": self.small_value_min_fraction,
            "small_value_zero_fraction": self.small_value_zero_fraction,
            "clipping_ratio_threshold": self.clipping_ratio_threshold,
        }.items():
            if not 0 <= value <= 1:
                raise StageCompareError(f"comparison threshold {name} must be between 0 and 1")
        if self.small_value_min_count < 1 or self.clipping_min_count < 1:
            raise StageCompareError("comparison count thresholds must be positive")


@dataclass(frozen=True)
class _ResolvedStage:
    stage: Literal["framework", "onnx", "rknn"]
    source_kind: str
    source_path: str | None
    outputs: dict[str, object]
    quantization: dict[str, QuantizationMetadata]
    artifact_source: str | None
    provenance: dict[str, object]
    warnings: list[str]
    available: bool


def _coerce_outputs(
    outputs: dict[str, object],
    expected_names: list[str],
    stage_name: str,
    map_by_order: bool,
) -> tuple[dict[str, object], list[str]]:
    warnings: list[str] = []
    if set(outputs) == set(expected_names):
        return {name: outputs[name] for name in expected_names}, warnings

    keys = list(outputs.keys())
    if map_by_order and len(keys) == len(expected_names):
        warnings.append(
            f"{stage_name} output names {keys} do not match contract outputs {expected_names}; "
            "mapped outputs by order because --map-by-order was explicitly enabled"
        )
        return {expected_names[index]: outputs[key] for index, key in enumerate(keys)}, warnings

    raise StageCompareError(
        f"{stage_name} outputs {keys} do not match expected outputs {expected_names}; "
        "rename outputs or explicitly opt in with --map-by-order"
    )


@dataclass(frozen=True)
class _ArtifactMetadata:
    quantization: dict[str, QuantizationMetadata]
    source: str | None
    provenance: dict[str, object]


def _load_artifact_metadata(
    path: str | Path,
    expected_names: list[str],
    map_by_order: bool,
) -> _ArtifactMetadata:
    try:
        artifact = load_tensor_artifact(path)
    except TensorArtifactError as exc:
        raise StageCompareError(str(exc)) from exc
    if artifact.manifest is None:
        return _ArtifactMetadata({}, None, {})

    records = {record.name: record.quantization for record in artifact.manifest.tensors}
    keys = list(artifact.tensors)
    if set(keys) == set(expected_names):
        quantization = {
            name: records[name]
            for name in expected_names
            if records.get(name) is not None
        }
    elif map_by_order and len(keys) == len(expected_names):
        quantization = {
            expected_names[index]: records[key]
            for index, key in enumerate(keys)
            if records.get(key) is not None
        }
    else:
        quantization = {}
    return _ArtifactMetadata(
        quantization=quantization,
        source=artifact.manifest.source,
        provenance=dict(artifact.manifest.provenance),
    )


def _make_stage_record(stage: _ResolvedStage) -> StageRecord:
    outputs = []
    for name, value in stage.outputs.items():
        quantization = stage.quantization.get(name)
        raw_values = np.asarray(value)
        summary = summarize_array(raw_values)
        dequantized_summary = (
            summarize_array(_dequantize(raw_values, quantization))
            if quantization is not None
            else None
        )
        outputs.append(
            StageTensorSummaryEntry(
                name=name,
                shape=list(summary.shape),
                dtype=summary.dtype,
                minimum=summary.minimum,
                maximum=summary.maximum,
                mean=summary.mean,
                std=summary.std,
                zero_fraction=summary.zero_fraction,
                finite_fraction=summary.finite_fraction,
                nan_count=summary.nan_count,
                positive_inf_count=summary.positive_inf_count,
                negative_inf_count=summary.negative_inf_count,
                saturation_fraction=_raw_saturation_fraction(raw_values, quantization),
                clipping_fraction=summary.clipping_fraction,
                quantization=quantization.to_dict() if quantization is not None else None,
                summary_domain="raw",
                dequantized_minimum=(dequantized_summary.minimum if dequantized_summary else None),
                dequantized_maximum=(dequantized_summary.maximum if dequantized_summary else None),
                dequantized_zero_fraction=(dequantized_summary.zero_fraction if dequantized_summary else None),
            )
        )
    return StageRecord(
        stage=stage.stage,
        source_kind=stage.source_kind,
        source_path=stage.source_path,
        artifact_source=stage.artifact_source,
        provenance=stage.provenance,
        available=stage.available,
        warnings=stage.warnings,
        outputs=outputs,
    )


def _with_contract_warnings(stage: _ResolvedStage, output_specs) -> _ResolvedStage:
    if not stage.available:
        return stage
    warnings = list(stage.warnings)
    for spec in output_specs:
        value = stage.outputs[spec.name]
        actual_shape = [int(dim) for dim in getattr(value, "shape", ())]
        actual_dtype = str(getattr(value, "dtype", "unknown"))
        if actual_shape != spec.shape:
            warnings.append(
                f"{stage.stage} tensor {spec.name!r} shape {actual_shape} does not match contract {spec.shape}"
            )
        if spec.name in stage.quantization:
            warnings.append(
                f"{stage.stage} tensor {spec.name!r} uses raw {actual_dtype} values; "
                "numerical comparison dequantizes them with artifact scale/zero_point metadata"
            )
        elif actual_dtype != spec.dtype:
            warnings.append(
                f"{stage.stage} tensor {spec.name!r} dtype {actual_dtype!r} does not match contract {spec.dtype!r}"
            )
    return replace(stage, warnings=warnings)


def _quantization_parameter(
    value: float | int | list[float] | list[int],
    metadata: QuantizationMetadata,
    rank: int,
) -> float | np.ndarray:
    values = np.asarray(value, dtype=np.float64)
    if values.size == 1:
        return float(values.reshape(-1)[0])
    if metadata.axis is None:
        raise StageCompareError("per-channel quantization metadata requires axis")
    axis = metadata.axis % rank
    shape = [1] * rank
    shape[axis] = values.size
    return values.reshape(shape)


def _dequantize(values: np.ndarray, metadata: QuantizationMetadata) -> np.ndarray:
    scale = _quantization_parameter(metadata.scale, metadata, values.ndim)
    zero_point = _quantization_parameter(metadata.zero_point, metadata, values.ndim)
    return (values.astype(np.float64) - zero_point) * scale


def _raw_saturation_fraction(
    values: np.ndarray,
    metadata: QuantizationMetadata | None,
) -> float | None:
    if values.size == 0 or not np.issubdtype(values.dtype, np.integer):
        return None
    limits = np.iinfo(values.dtype)
    qmin = metadata.qmin if metadata is not None and metadata.qmin is not None else limits.min
    qmax = metadata.qmax if metadata is not None and metadata.qmax is not None else limits.max
    saturated = (values == qmin) | (values == qmax)
    if metadata is not None:
        zero_point = _quantization_parameter(metadata.zero_point, metadata, values.ndim)
        saturated &= values != zero_point
    return float(np.mean(saturated))


def _comparison_arrays(
    left: _ResolvedStage,
    right: _ResolvedStage,
    tensor_name: str,
) -> tuple[np.ndarray, np.ndarray, str, float | None, float | None]:
    left_raw = np.asarray(left.outputs[tensor_name])
    right_raw = np.asarray(right.outputs[tensor_name])
    left_quantization = left.quantization.get(tensor_name)
    right_quantization = right.quantization.get(tensor_name)
    left_integer = np.issubdtype(left_raw.dtype, np.integer)
    right_integer = np.issubdtype(right_raw.dtype, np.integer)

    if (left_integer and left_quantization is None) or (right_integer and right_quantization is None):
        raise StageCompareError(
            f"cannot compare raw integer tensor {tensor_name!r} without quantization metadata; "
            "capture dequantized float output or provide scale/zero_point in every canonical integer artifact"
        )

    left_values = _dequantize(left_raw, left_quantization) if left_quantization is not None else left_raw
    right_values = _dequantize(right_raw, right_quantization) if right_quantization is not None else right_raw
    comparison_domain = "raw"
    if left_quantization is not None or right_quantization is not None:
        left_values = left_values.astype(np.float64, copy=False)
        right_values = right_values.astype(np.float64, copy=False)
        comparison_domain = "dequantized"

    return (
        left_values,
        right_values,
        comparison_domain,
        _raw_saturation_fraction(left_raw, left_quantization),
        _raw_saturation_fraction(right_raw, right_quantization),
    )


def _with_quantization_resolution(
    diff: TensorDiff,
    left_values: np.ndarray,
    right_values: np.ndarray,
    metadata: QuantizationMetadata | None,
) -> TensorDiff:
    if metadata is None or not diff.shape_match or left_values.size == 0:
        return diff

    scale = _quantization_parameter(metadata.scale, metadata, left_values.ndim)
    scale_values = np.broadcast_to(np.asarray(scale, dtype=np.float64), left_values.shape)
    left_numeric = left_values.astype(np.float64, copy=False)
    right_numeric = right_values.astype(np.float64, copy=False)
    mask = (
        np.isfinite(left_numeric)
        & np.isfinite(right_numeric)
        & (left_numeric != 0)
        & (np.abs(left_numeric) < scale_values * 0.5)
    )
    count = int(np.count_nonzero(mask))
    zero_fraction = float(np.mean(right_numeric[mask] == 0)) if count else None
    return replace(
        diff,
        quantization_step_min=float(np.min(scale_values)),
        quantization_step_max=float(np.max(scale_values)),
        under_resolution_count=count,
        under_resolution_fraction=float(count / left_values.size),
        under_resolution_zero_fraction=zero_fraction,
    )


def _classification_under_resolution_reason(
    contract: ModelContract,
    output_spec: TensorSpec,
    left_values: np.ndarray,
    right_values: np.ndarray,
    metadata: QuantizationMetadata | None,
    thresholds: ComparisonThresholds,
) -> str | None:
    """Attribute collapse to score channels only when their axis is structurally unambiguous."""
    decode = contract.decode
    if metadata is None or decode is None or not left_values.shape == right_values.shape:
        return None
    if output_spec.semantic not in {"raw_predictions", "scores", "class_scores"}:
        return None
    class_count = decode.num_classes
    candidate_axes = [
        index
        for index, dimension in enumerate(left_values.shape)
        if index > 0 and dimension in {class_count, class_count + 4}
    ]
    if len(candidate_axes) != 1:
        return None
    axis = candidate_axes[0]
    if left_values.shape[axis] == class_count + 4:
        selector: list[slice] = [slice(None)] * left_values.ndim
        selector[axis] = slice(4, None)
        selected = tuple(selector)
        channel_label = f"axis {axis}, channels 4..{class_count + 3}"
    else:
        selected = tuple(slice(None) for _ in range(left_values.ndim))
        channel_label = f"axis {axis}, {class_count} class channel(s)"

    scale = _quantization_parameter(metadata.scale, metadata, left_values.ndim)
    scale_values = np.broadcast_to(np.asarray(scale, dtype=np.float64), left_values.shape)[selected]
    reference = left_values[selected].astype(np.float64, copy=False)
    candidate = right_values[selected].astype(np.float64, copy=False)
    mask = np.isfinite(reference) & np.isfinite(candidate) & (reference != 0) & (np.abs(reference) < scale_values * 0.5)
    count = int(np.count_nonzero(mask))
    if not count:
        return None
    fraction = count / reference.size
    zero_fraction = float(np.mean(candidate[mask] == 0))
    if (
        count < thresholds.small_value_min_count
        or fraction < thresholds.small_value_min_fraction
        or zero_fraction < thresholds.small_value_zero_fraction
    ):
        return None
    return (
        "classification-score quantization under-resolution: "
        f"{channel_label}; {zero_fraction:.1%} of {count} sub-half-step reference scores became zero"
    )


_PROVENANCE_IDENTITY_KEYS = (
    "input_id",
    "input_path",
    "input_sha256",
    "sample_id",
    "preprocess_id",
    "contract_id",
    "model_id",
    "model_revision",
)


def _provenance_conflict_warnings(stages: list[_ResolvedStage]) -> list[str]:
    warnings: list[str] = []
    for key in _PROVENANCE_IDENTITY_KEYS:
        values = [(stage.stage, stage.provenance[key]) for stage in stages if key in stage.provenance]
        if len(values) < 2:
            continue
        first_value = values[0][1]
        if any(value != first_value for _, value in values[1:]):
            details = ", ".join(f"{stage}={value!r}" for stage, value in values)
            warnings.append(f"artifact provenance mismatch for {key}: {details}")
    return warnings


def _diff_status(diff: TensorDiff, thresholds: ComparisonThresholds, element_count: int) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not diff.shape_match:
        reasons.append("shape mismatch")
        return "shape_mismatch", reasons
    if not diff.dtype_match:
        reasons.append("dtype mismatch")
    if diff.left_nan_count or diff.left_inf_count:
        reasons.append(f"reference contains non-finite values: nan={diff.left_nan_count}, inf={diff.left_inf_count}")
    if diff.right_nan_count or diff.right_inf_count:
        reasons.append(f"candidate contains non-finite values: nan={diff.right_nan_count}, inf={diff.right_inf_count}")
    if diff.max_abs_error is not None and diff.max_abs_error > thresholds.max_abs_error:
        reasons.append(f"max_abs_error>{thresholds.max_abs_error}")
    if (
        diff.mean_relative_error is not None
        and diff.mean_relative_error > thresholds.max_mean_relative_error
    ):
        reasons.append(f"mean_relative_error>{thresholds.max_mean_relative_error}")
    if (
        diff.cosine_similarity is not None
        and diff.cosine_similarity < thresholds.min_cosine_similarity
    ):
        reasons.append(f"cosine_similarity<{thresholds.min_cosine_similarity}")
    quantization_under_resolution = (
        diff.under_resolution_count is not None
        and diff.under_resolution_count >= thresholds.small_value_min_count
        and diff.under_resolution_fraction is not None
        and diff.under_resolution_fraction >= thresholds.small_value_min_fraction
        and diff.under_resolution_zero_fraction is not None
        and diff.under_resolution_zero_fraction >= thresholds.small_value_zero_fraction
    )
    if quantization_under_resolution:
        reasons.append(
            "possible quantization under-resolution: "
            f"candidate step={diff.quantization_step_min}..{diff.quantization_step_max}; "
            f"{diff.under_resolution_zero_fraction:.1%} of {diff.under_resolution_count} "
            "sub-half-step reference values became zero"
        )
    elif (
        diff.small_value_count is not None
        and diff.small_value_count >= thresholds.small_value_min_count
        and diff.small_value_fraction is not None
        and diff.small_value_fraction >= thresholds.small_value_min_fraction
        and diff.small_value_zero_fraction is not None
        and diff.small_value_zero_fraction >= thresholds.small_value_zero_fraction
    ):
        reasons.append(
            "possible quantization under-resolution: "
            f"{diff.small_value_zero_fraction:.1%} of {diff.small_value_count} small reference values became zero"
        )
    if element_count >= thresholds.clipping_min_count:
        if (
            diff.right_saturation_fraction is not None
            and diff.right_saturation_fraction >= thresholds.clipping_ratio_threshold
            and diff.right_saturation_fraction
            - (diff.left_saturation_fraction or 0.0)
            >= thresholds.clipping_ratio_increase
        ):
            reasons.append(
                "possible integer saturation: "
                f"candidate endpoint ratio={diff.right_saturation_fraction:.1%}"
            )
        if (
            diff.right_clipping_fraction is not None
            and diff.right_clipping_fraction >= thresholds.clipping_ratio_threshold
            and diff.right_clipping_fraction
            - (diff.left_clipping_fraction or 0.0)
            >= thresholds.clipping_ratio_increase
        ):
            reasons.append(
                "possible clipping: "
                f"candidate observed-extreme ratio={diff.right_clipping_fraction:.1%}"
            )
    if reasons:
        return "drift", reasons
    return "aligned", reasons


def _resolve_framework_stage(
    framework_out: str | Path | None,
    framework_runner: str | None,
    contract_path: str | Path,
    image_path: str | Path,
    input_tensor,
    expected_names: list[str],
    map_by_order: bool,
) -> _ResolvedStage:
    if framework_out:
        outputs, warnings = load_framework_outputs(framework_out, expected_names, map_by_order=map_by_order)
        metadata = _load_artifact_metadata(framework_out, expected_names, map_by_order)
        return _ResolvedStage(
            stage="framework",
            source_kind="npz",
            source_path=str(framework_out),
            outputs=outputs,
            quantization=metadata.quantization,
            artifact_source=metadata.source,
            provenance=metadata.provenance,
            warnings=warnings,
            available=True,
        )
    if framework_runner:
        try:
            outputs, warnings = run_framework_outputs(
                framework_runner,
                contract_path=contract_path,
                image_path=image_path,
                input_tensor=input_tensor,
                expected_names=expected_names,
            )
            mapped, name_warnings = _coerce_outputs(outputs, expected_names, "framework", map_by_order)
            return _ResolvedStage(
                stage="framework",
                source_kind=f"runner:{framework_runner}",
                source_path=None,
                outputs=mapped,
                quantization={},
                artifact_source=None,
                provenance={},
                warnings=warnings + name_warnings,
                available=True,
            )
        except FrameworkAdapterError as exc:
            return _ResolvedStage(
                stage="framework",
                source_kind=f"runner:{framework_runner}",
                source_path=None,
                outputs={},
                quantization={},
                artifact_source=None,
                provenance={},
                warnings=[str(exc)],
                available=False,
            )
    return _ResolvedStage(
        stage="framework",
        source_kind="not-provided",
        source_path=None,
        outputs={},
        quantization={},
        artifact_source=None,
        provenance={},
        warnings=[],
        available=False,
    )


def _resolve_onnx_stage(
    onnx_model: str | Path | None,
    onnx_out: str | Path | None,
    input_tensor,
    expected_names: list[str],
    map_by_order: bool,
) -> _ResolvedStage:
    if onnx_out:
        outputs, warnings = load_onnx_outputs(onnx_out, expected_names, map_by_order=map_by_order)
        metadata = _load_artifact_metadata(onnx_out, expected_names, map_by_order)
        return _ResolvedStage(
            stage="onnx",
            source_kind="npz",
            source_path=str(onnx_out),
            outputs=outputs,
            quantization=metadata.quantization,
            artifact_source=metadata.source,
            provenance=metadata.provenance,
            warnings=warnings,
            available=True,
        )
    if onnx_model:
        outputs, warnings = run_onnx_model(onnx_model, input_tensor)
        mapped, name_warnings = _coerce_outputs(outputs, expected_names, "onnx", map_by_order)
        return _ResolvedStage(
            stage="onnx",
            source_kind="onnxruntime",
            source_path=str(onnx_model),
            outputs=mapped,
            quantization={},
            artifact_source=None,
            provenance={},
            warnings=warnings + name_warnings,
            available=True,
        )
    return _ResolvedStage(
        stage="onnx",
        source_kind="not-provided",
        source_path=None,
        outputs={},
        quantization={},
        artifact_source=None,
        provenance={},
        warnings=[],
        available=False,
    )


def _resolve_rknn_stage(
    rknn_model: str | Path | None,
    rknn_out: str | Path | None,
    input_tensor,
    expected_names: list[str],
    map_by_order: bool,
    stage_name: str = "rknn",
) -> _ResolvedStage:
    if rknn_out:
        outputs, warnings = load_rknn_outputs(rknn_out, expected_names, map_by_order=map_by_order)
        metadata = _load_artifact_metadata(rknn_out, expected_names, map_by_order)
        return _ResolvedStage(
            stage=stage_name,
            source_kind="npz",
            source_path=str(rknn_out),
            outputs=outputs,
            quantization=metadata.quantization,
            artifact_source=metadata.source,
            provenance=metadata.provenance,
            warnings=warnings,
            available=True,
        )
    if rknn_model:
        try:
            outputs, warnings = run_rknn_model(
                rknn_model,
                input_tensor=input_tensor,
                expected_names=expected_names,
            )
            mapped, name_warnings = _coerce_outputs(outputs, expected_names, "rknn", map_by_order)
            return _ResolvedStage(
                stage=stage_name,
                source_kind="rknn-runtime",
                source_path=str(rknn_model),
                outputs=mapped,
                quantization={},
                artifact_source=None,
                provenance={},
                warnings=warnings + name_warnings,
                available=True,
            )
        except RknnAdapterError as exc:
            return _ResolvedStage(
                stage=stage_name,
                source_kind="rknn-runtime",
                source_path=str(rknn_model),
                outputs={},
                quantization={},
                artifact_source=None,
                provenance={},
                warnings=[str(exc)],
                available=False,
            )
    return _ResolvedStage(
        stage=stage_name,
        source_kind="not-provided",
        source_path=None,
        outputs={},
        quantization={},
        artifact_source=None,
        provenance={},
        warnings=[],
        available=False,
    )


def compare_stages(
    contract_path: str | Path,
    image_path: str | Path,
    out_dir: str | Path,
    framework_out: str | Path | None = None,
    framework_runner: str | None = None,
    onnx_model: str | Path | None = None,
    onnx_out: str | Path | None = None,
    rknn_model: str | Path | None = None,
    rknn_out: str | Path | None = None,
    fp16_out: str | Path | None = None,
    int8_out: str | Path | None = None,
    report_format: str = "json",
    map_by_order: bool = False,
    thresholds: ComparisonThresholds | None = None,
) -> StageCompareArtifacts:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    thresholds = thresholds or ComparisonThresholds()
    thresholds.validate()

    try:
        contract = load_contract(contract_path)
        contract_issues = validate_contract(contract)
        if has_errors(contract_issues):
            details = "; ".join(
                f"{issue.code} ({issue.field}): {issue.message}"
                for issue in contract_issues
                if issue.severity == "error"
            )
            raise StageCompareError(f"contract has validation errors: {details}")
        preprocess = prepare_image(contract, image_path)
    except (OSError, RuntimeError, PreprocessError) as exc:
        raise StageCompareError(str(exc)) from exc

    expected_names = [output.name for output in contract.outputs]
    try:
        stages = [
            _resolve_framework_stage(
                framework_out,
                framework_runner,
                contract_path,
                image_path,
                preprocess.input_tensor,
                expected_names,
                map_by_order,
            ),
            _resolve_onnx_stage(onnx_model, onnx_out, preprocess.input_tensor, expected_names, map_by_order),
            _resolve_rknn_stage(rknn_model, rknn_out, preprocess.input_tensor, expected_names, map_by_order),
        ]
        if fp16_out:
            stages.append(_resolve_rknn_stage(None, fp16_out, preprocess.input_tensor, expected_names, map_by_order, "fp16"))
        if int8_out:
            stages.append(_resolve_rknn_stage(None, int8_out, preprocess.input_tensor, expected_names, map_by_order, "int8"))
        stages = [_with_contract_warnings(stage, contract.outputs) for stage in stages]
    except (FrameworkAdapterError, OnnxRuntimeAdapterError, RknnAdapterError) as exc:
        raise StageCompareError(str(exc)) from exc

    available = [stage for stage in stages if stage.available]
    if len(available) < 2:
        raise StageCompareError(
            "compare-stages needs at least two available stages; provide framework/onnx/rknn outputs or install required runtimes"
        )

    pair_diffs: list[StagePairDiffEntry] = []
    for left, right in zip(available, available[1:], strict=False):
        for output_name in expected_names:
            (
                left_values,
                right_values,
                comparison_domain,
                left_saturation_fraction,
                right_saturation_fraction,
            ) = _comparison_arrays(left, right, output_name)
            diff = compare_arrays(
                left_values,
                right_values,
                relative_error_epsilon=thresholds.relative_error_epsilon,
                small_value_threshold=thresholds.small_value_threshold,
                small_value_relative_threshold=thresholds.small_value_relative_threshold,
                small_value_min_threshold=thresholds.small_value_min_threshold,
                small_value_max_threshold=thresholds.small_value_max_threshold,
            )
            diff = _with_quantization_resolution(
                diff,
                left_values,
                right_values,
                right.quantization.get(output_name),
            )
            diff = replace(
                diff,
                left_saturation_fraction=left_saturation_fraction,
                right_saturation_fraction=right_saturation_fraction,
            )
            element_count = int(getattr(left.outputs[output_name], "size", 0))
            status, reasons = _diff_status(diff, thresholds, element_count)
            output_spec = next(spec for spec in contract.outputs if spec.name == output_name)
            score_reason = _classification_under_resolution_reason(
                contract,
                output_spec,
                left_values,
                right_values,
                right.quantization.get(output_name),
                thresholds,
            )
            if score_reason is not None:
                reasons.append(score_reason)
                status = "drift"
            pair_diffs.append(
                StagePairDiffEntry(
                    left_stage=left.stage,
                    right_stage=right.stage,
                    tensor_name=output_name,
                    status=status,  # type: ignore[arg-type]
                    shape_match=diff.shape_match,
                    dtype_match=diff.dtype_match,
                    max_abs_error=diff.max_abs_error,
                    mean_abs_error=diff.mean_abs_error,
                    rms_error=diff.rms_error,
                    cosine_similarity=diff.cosine_similarity,
                    reasons=reasons,
                    comparison_domain=comparison_domain,  # type: ignore[arg-type]
                    left_raw_dtype=str(getattr(left.outputs[output_name], "dtype", "unknown")),
                    right_raw_dtype=str(getattr(right.outputs[output_name], "dtype", "unknown")),
                    max_relative_error=diff.max_relative_error,
                    mean_relative_error=diff.mean_relative_error,
                    left_zero_fraction=diff.left_zero_fraction,
                    right_zero_fraction=diff.right_zero_fraction,
                    left_nan_count=diff.left_nan_count,
                    right_nan_count=diff.right_nan_count,
                    left_inf_count=diff.left_inf_count,
                    right_inf_count=diff.right_inf_count,
                    finite_pair_fraction=diff.finite_pair_fraction,
                    left_saturation_fraction=diff.left_saturation_fraction,
                    right_saturation_fraction=diff.right_saturation_fraction,
                    left_clipping_fraction=diff.left_clipping_fraction,
                    right_clipping_fraction=diff.right_clipping_fraction,
                    small_value_threshold=diff.small_value_threshold,
                    small_value_count=diff.small_value_count,
                    small_value_fraction=diff.small_value_fraction,
                    small_value_zero_fraction=diff.small_value_zero_fraction,
                    quantization_step_min=diff.quantization_step_min,
                    quantization_step_max=diff.quantization_step_max,
                    under_resolution_count=diff.under_resolution_count,
                    under_resolution_fraction=diff.under_resolution_fraction,
                    under_resolution_zero_fraction=diff.under_resolution_zero_fraction,
                )
            )

    first_drift = next((item for item in pair_diffs if item.status != "aligned"), None)
    warnings = [
        f"contract warning {issue.code} ({issue.field}): {issue.message}"
        for issue in contract_issues
        if issue.severity == "warning"
    ]
    for stage in stages:
        warnings.extend(stage.warnings)
    warnings.extend(_provenance_conflict_warnings(available))

    final_summary = StageFinalSummary(
        available_stages=[stage.stage for stage in available],
        compared_pairs=list(
            dict.fromkeys(f"{item.left_stage}->{item.right_stage}" for item in pair_diffs)
        ),
        drift_detected=first_drift is not None,
        first_drift_stage=first_drift.right_stage if first_drift is not None else None,
        first_drift_pair=f"{first_drift.left_stage}->{first_drift.right_stage}" if first_drift is not None else None,
        warning_count=len(warnings),
    )
    report = StageCompareReport(
        contract_name=contract.name,
        image_path=str(Path(image_path)),
        input_tensor_shape=list(preprocess.input_tensor.shape),
        input_tensor_dtype=str(preprocess.input_tensor.dtype),
        stages=[_make_stage_record(stage) for stage in stages],
        pair_diffs=pair_diffs,
        final_summary=final_summary,
        warnings=warnings,
        comparison_thresholds=asdict(thresholds),
    )

    report_json = write_stage_report_json(report, out / "report.json")
    tensor_diffs_json = write_tensor_diffs_json(pair_diffs, out / "tensor_diffs.json")
    final_summary_json = write_final_summary_json(final_summary, out / "final_summary.json")
    report_markdown = None
    report_html = None
    try:
        if report_format == "md":
            report_markdown = write_stage_report_markdown(report, out / "report.md")
        elif report_format == "html":
            report_html = write_stage_report_html(report, out / "report.html")
    except RuntimeError as exc:
        raise StageCompareError(str(exc)) from exc

    return StageCompareArtifacts(
        report_json=report_json,
        tensor_diffs_json=tensor_diffs_json,
        final_summary_json=final_summary_json,
        report_markdown=report_markdown,
        report_html=report_html,
    )
