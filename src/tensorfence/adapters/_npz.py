from __future__ import annotations

from pathlib import Path

import numpy as np

from ..artifacts.tensor_artifact import TensorArtifactError, load_tensor_artifact


class NpzAdapterError(RuntimeError):
    pass


def load_npz_outputs(
    path: str | Path,
    expected_names: list[str],
    *,
    map_by_order: bool = False,
    expected_stage: str | None = None,
) -> tuple[dict[str, np.ndarray], list[str]]:
    source = Path(path)
    if not source.exists():
        raise NpzAdapterError(f"npz artifact does not exist: {source}")

    try:
        artifact = load_tensor_artifact(source)
    except TensorArtifactError as exc:
        raise NpzAdapterError(str(exc)) from exc

    keys = list(artifact.tensors)
    warnings: list[str] = []
    if artifact.manifest is not None and expected_stage is not None:
        if artifact.manifest.stage != expected_stage:
            raise NpzAdapterError(
                f"tensor artifact stage {artifact.manifest.stage!r} does not match expected stage {expected_stage!r}"
            )
    if set(keys) == set(expected_names):
        outputs = {name: artifact.tensors[name] for name in expected_names}
        return outputs, warnings

    if map_by_order and len(keys) == len(expected_names):
        warnings.append(
            f"npz keys {keys} do not match expected output names {expected_names}; "
            "mapped outputs by file order because --map-by-order was explicitly enabled"
        )
        outputs = {expected_names[index]: artifact.tensors[key] for index, key in enumerate(keys)}
        return outputs, warnings

    raise NpzAdapterError(
        f"npz keys {keys} do not match expected outputs {expected_names}; "
        "rename keys or explicitly opt in with --map-by-order"
    )
