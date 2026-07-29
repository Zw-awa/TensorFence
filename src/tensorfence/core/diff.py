from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TensorSummary:
    shape: tuple[int, ...]
    dtype: str
    minimum: float | None
    maximum: float | None
    mean: float | None
    std: float | None


@dataclass(frozen=True)
class TensorDiff:
    shape_match: bool
    dtype_match: bool
    max_abs_error: float | None
    mean_abs_error: float | None
    rms_error: float | None
    cosine_similarity: float | None
    right_zero_fraction: float | None = None
    small_value_threshold: float | None = None
    small_value_count: int | None = None
    small_value_fraction: float | None = None
    small_value_zero_fraction: float | None = None


def summarize_array(array: np.ndarray) -> TensorSummary:
    values = np.asarray(array)
    if values.size == 0:
        return TensorSummary(tuple(values.shape), str(values.dtype), None, None, None, None)

    return TensorSummary(
        shape=tuple(int(dim) for dim in values.shape),
        dtype=str(values.dtype),
        minimum=float(np.min(values)),
        maximum=float(np.max(values)),
        mean=float(np.mean(values)),
        std=float(np.std(values)),
    )


def compare_arrays(left: np.ndarray, right: np.ndarray) -> TensorDiff:
    left_values = np.asarray(left)
    right_values = np.asarray(right)

    shape_match = tuple(left_values.shape) == tuple(right_values.shape)
    dtype_match = left_values.dtype == right_values.dtype

    if not shape_match:
        return TensorDiff(shape_match, dtype_match, None, None, None, None)

    delta = left_values.astype(np.float64) - right_values.astype(np.float64)
    abs_delta = np.abs(delta)
    max_abs_error = float(np.max(abs_delta)) if abs_delta.size else None
    mean_abs_error = float(np.mean(abs_delta)) if abs_delta.size else None
    rms_error = float(np.sqrt(np.mean(np.square(delta)))) if delta.size else None

    left_flat = left_values.astype(np.float64).ravel()
    right_flat = right_values.astype(np.float64).ravel()
    denominator = float(np.linalg.norm(left_flat) * np.linalg.norm(right_flat))
    cosine_similarity = None
    if denominator > 0:
        cosine_similarity = float(np.dot(left_flat, right_flat) / denominator)

    right_flat = right_values.ravel()
    right_zero_fraction = float(np.mean(right_flat == 0)) if right_flat.size else None
    left_abs = np.abs(left_flat)
    left_max_abs = float(np.max(left_abs)) if left_abs.size else 0.0
    small_value_threshold = max(1e-6, min(1e-3, left_max_abs * 1e-4)) if left_abs.size else None
    small_value_mask = (
        (left_abs > 0) & (left_abs <= small_value_threshold)
        if small_value_threshold is not None
        else None
    )
    small_value_count = int(np.count_nonzero(small_value_mask)) if small_value_mask is not None else None
    small_value_fraction = (
        float(small_value_count / left_abs.size)
        if small_value_count is not None and left_abs.size
        else None
    )
    small_value_zero_fraction = None
    if small_value_mask is not None and small_value_count:
        small_value_zero_fraction = float(np.mean(right_flat[small_value_mask] == 0))

    return TensorDiff(
        shape_match,
        dtype_match,
        max_abs_error,
        mean_abs_error,
        rms_error,
        cosine_similarity,
        right_zero_fraction,
        small_value_threshold,
        small_value_count,
        small_value_fraction,
        small_value_zero_fraction,
    )
