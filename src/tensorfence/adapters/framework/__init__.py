from __future__ import annotations

from pathlib import Path

import numpy as np

from .._npz import NpzAdapterError, load_npz_outputs


class FrameworkAdapterError(RuntimeError):
    pass


def load_framework_outputs(
    path: str | Path,
    expected_names: list[str],
    *,
    map_by_order: bool = False,
) -> tuple[dict[str, np.ndarray], list[str]]:
    try:
        return load_npz_outputs(
            path,
            expected_names,
            map_by_order=map_by_order,
            expected_stage="framework",
        )
    except NpzAdapterError as exc:
        raise FrameworkAdapterError(str(exc)) from exc


def run_framework_outputs(
    _runner: str,
    *,
    contract_path: str | Path,
    image_path: str | Path,
    input_tensor: np.ndarray,
    expected_names: list[str],
) -> tuple[dict[str, np.ndarray], list[str]]:
    raise FrameworkAdapterError(
        "direct framework execution is not implemented in v1; provide --framework-out with an .npz artifact"
    )
