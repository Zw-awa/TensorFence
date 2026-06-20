from __future__ import annotations

from pathlib import Path

import numpy as np


class NpzAdapterError(RuntimeError):
    pass


def load_npz_outputs(path: str | Path, expected_names: list[str]) -> tuple[dict[str, np.ndarray], list[str]]:
    source = Path(path)
    if not source.exists():
        raise NpzAdapterError(f"npz artifact does not exist: {source}")

    try:
        with np.load(source, allow_pickle=False) as data:
            keys = list(data.files)
            if not keys:
                raise NpzAdapterError(f"npz artifact does not contain any arrays: {source}")

            warnings: list[str] = []
            if all(name in data for name in expected_names):
                outputs = {name: np.asarray(data[name]) for name in expected_names}
                return outputs, warnings

            if len(keys) == len(expected_names):
                warnings.append(
                    f"npz keys {keys} do not match expected output names {expected_names}; mapped outputs by file order"
                )
                outputs = {expected_names[index]: np.asarray(data[key]) for index, key in enumerate(keys)}
                return outputs, warnings

            raise NpzAdapterError(
                f"npz keys {keys} do not match expected outputs {expected_names}; rename keys or fix output count"
            )
    except OSError as exc:
        raise NpzAdapterError(f"failed to read npz artifact: {source}") from exc
