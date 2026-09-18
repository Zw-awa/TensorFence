from __future__ import annotations

from pathlib import Path

import numpy as np

from .._npz import NpzAdapterError, load_npz_outputs


class RknnAdapterError(RuntimeError):
    pass


def load_rknn_outputs(
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
            expected_stage="rknn",
        )
    except NpzAdapterError as exc:
        raise RknnAdapterError(str(exc)) from exc


def run_rknn_model(
    model_path: str | Path,
    *,
    input_tensor: np.ndarray,
    expected_names: list[str],
    target: str | None = None,
    device_id: str | None = None,
) -> tuple[dict[str, np.ndarray], list[str]]:
    try:
        from rknn.api import RKNN
    except ImportError as exc:
        raise RknnAdapterError(
            "RKNN Toolkit2 could not be imported; run this command through `tensorfence rknn-run` "
            f"and check its WSL environment ({exc})"
        ) from exc
    source = Path(model_path)
    if not source.is_file():
        raise RknnAdapterError(f"RKNN model does not exist: {source}")
    rknn = RKNN(verbose=False)
    warnings: list[str] = []
    try:
        if rknn.load_rknn(str(source)) != 0:
            raise RknnAdapterError(f"failed to load RKNN model: {source}")
        kwargs = {key: value for key, value in {"target": target, "device_id": device_id}.items() if value}
        if rknn.init_runtime(**kwargs) != 0:
            raise RknnAdapterError("failed to initialize RKNN runtime/simulator; use --device-id for a connected board")
        values = rknn.inference(inputs=[np.asarray(input_tensor)])
        if len(values) != len(expected_names):
            raise RknnAdapterError(f"RKNN returned {len(values)} outputs, but contract declares {len(expected_names)}")
        return {name: np.asarray(value) for name, value in zip(expected_names, values, strict=True)}, warnings
    except RknnAdapterError:
        raise
    except Exception as exc:
        raise RknnAdapterError(f"RKNN inference failed: {exc}") from exc
    finally:
        try:
            rknn.release()
        except Exception:
            pass
