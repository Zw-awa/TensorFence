from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _finite_float(value: object) -> float | None:
    result = float(value)
    return result if np.isfinite(result) else None


@dataclass(frozen=True)
class TensorSummary:
    shape: tuple[int, ...]
    dtype: str
    minimum: float | None
    maximum: float | None
    mean: float | None
    std: float | None
    zero_fraction: float | None
    finite_fraction: float | None
    nan_count: int
    positive_inf_count: int
    negative_inf_count: int
    saturation_fraction: float | None
    clipping_fraction: float | None


@dataclass(frozen=True)
class TensorDiff:
    shape_match: bool
    dtype_match: bool
    max_abs_error: float | None
    mean_abs_error: float | None
    rms_error: float | None
    cosine_similarity: float | None
    max_relative_error: float | None = None
    mean_relative_error: float | None = None
    left_zero_fraction: float | None = None
    right_zero_fraction: float | None = None
    left_nan_count: int = 0
    right_nan_count: int = 0
    left_inf_count: int = 0
    right_inf_count: int = 0
    finite_pair_fraction: float | None = None
    left_saturation_fraction: float | None = None
    right_saturation_fraction: float | None = None
    left_clipping_fraction: float | None = None
    right_clipping_fraction: float | None = None
    small_value_threshold: float | None = None
    small_value_count: int | None = None
    small_value_fraction: float | None = None
    small_value_zero_fraction: float | None = None
    quantization_step_min: float | None = None
    quantization_step_max: float | None = None
    under_resolution_count: int | None = None
    under_resolution_fraction: float | None = None
    under_resolution_zero_fraction: float | None = None


def _saturation_fraction(values: np.ndarray) -> float | None:
    if values.size == 0 or not np.issubdtype(values.dtype, np.integer):
        return None
    limits = np.iinfo(values.dtype)
    return float(np.mean((values == limits.min) | (values == limits.max)))


def _clipping_fraction(values: np.ndarray) -> float | None:
    if values.size == 0 or not np.issubdtype(values.dtype, np.number):
        return None
    numeric = values.astype(np.float64, copy=False).ravel()
    finite = numeric[np.isfinite(numeric)]
    if finite.size == 0:
        return None
    minimum = np.min(finite)
    maximum = np.max(finite)
    return float(np.mean((finite == minimum) | (finite == maximum)))


def summarize_array(array: np.ndarray) -> TensorSummary:
    values = np.asarray(array)
    if values.size == 0:
        return TensorSummary(
            tuple(values.shape), str(values.dtype), None, None, None, None,
            None, None, 0, 0, 0, None, None,
        )

    numeric = values.astype(np.float64, copy=False)
    finite_mask = np.isfinite(numeric)
    finite = numeric[finite_mask]
    nan_count = int(np.count_nonzero(np.isnan(numeric)))
    positive_inf_count = int(np.count_nonzero(np.isposinf(numeric)))
    negative_inf_count = int(np.count_nonzero(np.isneginf(numeric)))

    return TensorSummary(
        shape=tuple(int(dim) for dim in values.shape),
        dtype=str(values.dtype),
        minimum=_finite_float(np.min(finite)) if finite.size else None,
        maximum=_finite_float(np.max(finite)) if finite.size else None,
        mean=_finite_float(np.mean(finite)) if finite.size else None,
        std=_finite_float(np.std(finite)) if finite.size else None,
        zero_fraction=float(np.mean(values == 0)),
        finite_fraction=float(np.mean(finite_mask)),
        nan_count=nan_count,
        positive_inf_count=positive_inf_count,
        negative_inf_count=negative_inf_count,
        saturation_fraction=_saturation_fraction(values),
        clipping_fraction=_clipping_fraction(values),
    )


def compare_arrays(
    left: np.ndarray,
    right: np.ndarray,
    *,
    relative_error_epsilon: float = 1e-12,
    small_value_threshold: float | None = None,
    small_value_relative_threshold: float = 1e-4,
    small_value_min_threshold: float = 1e-6,
    small_value_max_threshold: float = 1e-3,
) -> TensorDiff:
    left_values = np.asarray(left)
    right_values = np.asarray(right)

    shape_match = tuple(left_values.shape) == tuple(right_values.shape)
    dtype_match = left_values.dtype == right_values.dtype

    left_numeric = left_values.astype(np.float64, copy=False).ravel()
    right_numeric = right_values.astype(np.float64, copy=False).ravel()
    left_nan_count = int(np.count_nonzero(np.isnan(left_numeric)))
    right_nan_count = int(np.count_nonzero(np.isnan(right_numeric)))
    left_inf_count = int(np.count_nonzero(np.isinf(left_numeric)))
    right_inf_count = int(np.count_nonzero(np.isinf(right_numeric)))
    left_zero_fraction = float(np.mean(left_values == 0)) if left_values.size else None
    right_zero_fraction = float(np.mean(right_values == 0)) if right_values.size else None
    left_saturation_fraction = _saturation_fraction(left_values)
    right_saturation_fraction = _saturation_fraction(right_values)
    left_clipping_fraction = _clipping_fraction(left_values)
    right_clipping_fraction = _clipping_fraction(right_values)

    if not shape_match:
        return TensorDiff(
            shape_match=shape_match,
            dtype_match=dtype_match,
            max_abs_error=None,
            mean_abs_error=None,
            rms_error=None,
            cosine_similarity=None,
            left_zero_fraction=left_zero_fraction,
            right_zero_fraction=right_zero_fraction,
            left_nan_count=left_nan_count,
            right_nan_count=right_nan_count,
            left_inf_count=left_inf_count,
            right_inf_count=right_inf_count,
            left_saturation_fraction=left_saturation_fraction,
            right_saturation_fraction=right_saturation_fraction,
            left_clipping_fraction=left_clipping_fraction,
            right_clipping_fraction=right_clipping_fraction,
        )

    finite_pair_mask = np.isfinite(left_numeric) & np.isfinite(right_numeric)
    finite_pair_fraction = float(np.mean(finite_pair_mask)) if finite_pair_mask.size else None
    left_finite = left_numeric[finite_pair_mask]
    right_finite = right_numeric[finite_pair_mask]
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        delta = left_finite - right_finite
        abs_delta = np.abs(delta)
        max_abs_error = _finite_float(np.max(abs_delta)) if abs_delta.size else None
        mean_abs_error = _finite_float(np.mean(abs_delta)) if abs_delta.size else None
        rms_error = _finite_float(np.sqrt(np.mean(np.square(delta)))) if delta.size else None

    with np.errstate(over="ignore", invalid="ignore"):
        denominator = float(np.linalg.norm(left_finite) * np.linalg.norm(right_finite))
    cosine_similarity = None
    if np.isfinite(denominator) and denominator > 0:
        cosine_similarity = float(np.dot(left_finite, right_finite) / denominator)

    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        relative_error = abs_delta / np.maximum(np.abs(left_finite), relative_error_epsilon)
        max_relative_error = _finite_float(np.max(relative_error)) if relative_error.size else None
        mean_relative_error = _finite_float(np.mean(relative_error)) if relative_error.size else None

    left_abs = np.abs(left_numeric)
    finite_left_abs = left_abs[np.isfinite(left_abs)]
    left_max_abs = float(np.max(finite_left_abs)) if finite_left_abs.size else 0.0
    effective_small_value_threshold = small_value_threshold
    if effective_small_value_threshold is None and finite_left_abs.size:
        effective_small_value_threshold = max(
            small_value_min_threshold,
            min(small_value_max_threshold, left_max_abs * small_value_relative_threshold),
        )
    small_value_mask = (
        np.isfinite(left_abs) & (left_abs > 0) & (left_abs <= effective_small_value_threshold)
        if effective_small_value_threshold is not None
        else None
    )
    small_value_count = int(np.count_nonzero(small_value_mask)) if small_value_mask is not None else None
    small_value_fraction = (
        float(small_value_count / left_numeric.size)
        if small_value_count is not None and left_numeric.size
        else None
    )
    small_value_zero_fraction = None
    if small_value_mask is not None and small_value_count:
        small_value_zero_fraction = float(np.mean(right_numeric[small_value_mask] == 0))

    return TensorDiff(
        shape_match=shape_match,
        dtype_match=dtype_match,
        max_abs_error=max_abs_error,
        mean_abs_error=mean_abs_error,
        rms_error=rms_error,
        cosine_similarity=cosine_similarity,
        max_relative_error=max_relative_error,
        mean_relative_error=mean_relative_error,
        left_zero_fraction=left_zero_fraction,
        right_zero_fraction=right_zero_fraction,
        left_nan_count=left_nan_count,
        right_nan_count=right_nan_count,
        left_inf_count=left_inf_count,
        right_inf_count=right_inf_count,
        finite_pair_fraction=finite_pair_fraction,
        left_saturation_fraction=left_saturation_fraction,
        right_saturation_fraction=right_saturation_fraction,
        left_clipping_fraction=left_clipping_fraction,
        right_clipping_fraction=right_clipping_fraction,
        small_value_threshold=effective_small_value_threshold,
        small_value_count=small_value_count,
        small_value_fraction=small_value_fraction,
        small_value_zero_fraction=small_value_zero_fraction,
    )
