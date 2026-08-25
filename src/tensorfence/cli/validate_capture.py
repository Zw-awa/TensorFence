from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

from ..artifacts.tensor_artifact import TensorArtifactError, load_tensor_artifact
from ..core.contracts import ContractError, load_contract


class CaptureValidationError(ValueError):
    pass


def _parse_artifact(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise CaptureValidationError(
            f"invalid --artifact value {value!r}; expected LABEL=PATH.npz"
        )
    label, raw_path = value.split("=", 1)
    label = label.strip()
    path = Path(raw_path)
    if not label or not raw_path.strip():
        raise CaptureValidationError(
            f"invalid --artifact value {value!r}; expected LABEL=PATH.npz"
        )
    return label, path


def _validate_artifacts(contract_path: str, specifications: list[str]) -> list[str]:
    try:
        contract = load_contract(contract_path)
    except ContractError as exc:
        raise CaptureValidationError(str(exc)) from exc

    if len(specifications) < 2:
        raise CaptureValidationError("at least two --artifact values are required")

    expected_names = {output.name for output in contract.outputs}
    labels: set[str] = set()
    input_hash: str | None = None
    preprocess_id: str | None = None
    lines: list[str] = []
    for specification in specifications:
        label, path = _parse_artifact(specification)
        if label in labels:
            raise CaptureValidationError(f"duplicate artifact label: {label}")
        labels.add(label)
        try:
            artifact = load_tensor_artifact(path, allow_legacy=False)
        except TensorArtifactError as exc:
            raise CaptureValidationError(f"{label}: {exc}") from exc
        assert artifact.manifest is not None

        names = set(artifact.tensors)
        if names != expected_names:
            raise CaptureValidationError(
                f"{label}: output names {sorted(names)} do not match contract outputs {sorted(expected_names)}"
            )
        provenance = artifact.manifest.provenance
        candidate_hash = provenance.get("input_sha256")
        if not isinstance(candidate_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", candidate_hash):
            raise CaptureValidationError(
                f"{label}: provenance.input_sha256 must be a SHA-256 string for capture comparison"
            )
        if input_hash is None:
            input_hash = candidate_hash
        elif candidate_hash != input_hash:
            raise CaptureValidationError(f"{label}: provenance.input_sha256 differs from the other artifacts")

        candidate_preprocess = provenance.get("preprocess_id")
        if not isinstance(candidate_preprocess, str) or not candidate_preprocess.strip():
            raise CaptureValidationError(
                f"{label}: provenance.preprocess_id is required to prove matching preprocessing"
            )
        if preprocess_id is None:
            preprocess_id = candidate_preprocess
        elif candidate_preprocess != preprocess_id:
            raise CaptureValidationError(f"{label}: provenance.preprocess_id differs from the other artifacts")

        quantized = []
        records = {record.name: record for record in artifact.manifest.tensors}
        for name, array in artifact.tensors.items():
            if np.issubdtype(array.dtype, np.integer):
                if records[name].quantization is None:
                    raise CaptureValidationError(
                        f"{label}: integer tensor {name!r} is missing scale/zero_point metadata"
                    )
                quantized.append(name)
        quantization_text = ", ".join(sorted(quantized)) if quantized else "none"
        lines.append(
            f"OK {label}: stage={artifact.manifest.stage}, source={artifact.manifest.source}, "
            f"quantized_outputs={quantization_text}"
        )
    lines.append(f"OK shared input_sha256={input_hash}")
    lines.append(f"OK shared preprocess_id={preprocess_id}")
    return lines


def build_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "validate-capture",
        help="validate a comparable set of canonical stage artifacts before diagnosis",
    )
    parser.add_argument("--contract", required=True, help="path to the model contract YAML file")
    parser.add_argument(
        "--artifact",
        action="append",
        required=True,
        metavar="LABEL=PATH.npz",
        help="named canonical artifact; repeat for framework, fp16, int8, or other captures",
    )
    parser.set_defaults(func=cmd_validate_capture)


def cmd_validate_capture(args: argparse.Namespace) -> int:
    try:
        lines = _validate_artifacts(args.contract, args.artifact)
    except CaptureValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


__all__ = ["build_parser", "cmd_validate_capture"]
