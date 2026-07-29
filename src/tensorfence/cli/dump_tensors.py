from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from ..artifacts.tensor_artifact import TensorArtifactError, write_tensor_artifact


class DumpTensorsError(ValueError):
    pass


def _load_json_object(path: str | None, *, label: str) -> dict[str, Any]:
    if path is None:
        return {}
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DumpTensorsError(f"failed to read {label} JSON: {source}") from exc
    except json.JSONDecodeError as exc:
        raise DumpTensorsError(f"invalid {label} JSON: {source}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise DumpTensorsError(f"{label} JSON root must be an object: {source}")
    return value


def _load_named_tensors(specifications: list[str]) -> dict[str, np.ndarray]:
    tensors: dict[str, np.ndarray] = {}
    for specification in specifications:
        if "=" not in specification:
            raise DumpTensorsError(f"invalid --tensor value {specification!r}; expected NAME=PATH.npy")
        name, raw_path = specification.split("=", 1)
        name = name.strip()
        source = Path(raw_path)
        if not name or not raw_path:
            raise DumpTensorsError(f"invalid --tensor value {specification!r}; expected NAME=PATH.npy")
        if name in tensors:
            raise DumpTensorsError(f"duplicate tensor name: {name}")
        if source.suffix.lower() != ".npy":
            raise DumpTensorsError(f"tensor input must be a .npy file: {source}")
        try:
            tensors[name] = np.load(source, allow_pickle=False)
        except (OSError, ValueError) as exc:
            raise DumpTensorsError(f"failed to read tensor array: {source}") from exc
    return tensors


def build_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "dump-tensors",
        help="pack named .npy arrays into a canonical TensorFence tensor artifact",
    )
    parser.add_argument("--stage", required=True, help="pipeline stage, for example framework, onnx, or rknn")
    parser.add_argument("--source", required=True, help="runtime or producer that created the tensors")
    parser.add_argument(
        "--tensor",
        action="append",
        required=True,
        metavar="NAME=PATH.npy",
        help="named tensor array; repeat for every output",
    )
    parser.add_argument("--out", required=True, help="canonical output artifact (.npz)")
    parser.add_argument(
        "--provenance-json",
        help="optional JSON object with model, runtime, device, input, or command provenance",
    )
    parser.add_argument(
        "--quantization-json",
        help="optional JSON object mapping tensor names to scale/zero_point metadata",
    )
    parser.add_argument(
        "--uncompressed",
        action="store_true",
        help="store arrays without ZIP compression",
    )
    parser.set_defaults(func=cmd_dump_tensors)


def cmd_dump_tensors(args: argparse.Namespace) -> int:
    try:
        tensors = _load_named_tensors(args.tensor)
        provenance = _load_json_object(args.provenance_json, label="provenance")
        quantization = _load_json_object(args.quantization_json, label="quantization")
        target = write_tensor_artifact(
            args.out,
            tensors,
            stage=args.stage,
            source=args.source,
            provenance=provenance,
            quantization=quantization,
            compressed=not args.uncompressed,
        )
    except (DumpTensorsError, TensorArtifactError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"wrote canonical tensor artifact to {target}")
    return 0


__all__ = ["build_parser", "cmd_dump_tensors"]
