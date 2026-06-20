from __future__ import annotations

from pathlib import Path

import numpy as np

from .._npz import NpzAdapterError, load_npz_outputs


class RknnAdapterError(RuntimeError):
    pass


def load_rknn_outputs(path: str | Path, expected_names: list[str]) -> tuple[dict[str, np.ndarray], list[str]]:
    try:
        return load_npz_outputs(path, expected_names)
    except NpzAdapterError as exc:
        raise RknnAdapterError(str(exc)) from exc


def run_rknn_model(
    _model_path: str | Path,
    *,
    input_tensor: np.ndarray,
    expected_names: list[str],
) -> tuple[dict[str, np.ndarray], list[str]]:
    raise RknnAdapterError(
        "direct RKNN execution is not implemented in v1; provide --rknn-out with an .npz artifact"
    )
