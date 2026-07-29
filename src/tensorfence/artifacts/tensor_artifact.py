from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from ..version import __version__


TENSOR_ARTIFACT_SCHEMA_VERSION = "tensorfence.tensor-artifact/v1"
TENSOR_ARTIFACT_MANIFEST_KEY = "__tensorfence_manifest__"


class TensorArtifactError(ValueError):
    """Raised when a tensor artifact cannot be written or validated."""


@dataclass(frozen=True)
class QuantizationMetadata:
    scale: float | list[float]
    zero_point: int | list[int]
    axis: int | None = None
    qmin: int | None = None
    qmax: int | None = None
    scheme: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "scale": self.scale,
            "zero_point": self.zero_point,
        }
        for name in ("axis", "qmin", "qmax", "scheme"):
            value = getattr(self, name)
            if value is not None:
                data[name] = value
        return data


@dataclass(frozen=True)
class TensorArtifactTensor:
    name: str
    dtype: str
    shape: list[int]
    quantization: QuantizationMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "dtype": self.dtype,
            "shape": self.shape,
        }
        if self.quantization is not None:
            data["quantization"] = self.quantization.to_dict()
        return data


@dataclass(frozen=True)
class TensorArtifactManifest:
    schema_version: str
    stage: str
    source: str
    tensors: list[TensorArtifactTensor]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage": self.stage,
            "source": self.source,
            "tensors": [tensor.to_dict() for tensor in self.tensors],
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class LoadedTensorArtifact:
    tensors: dict[str, np.ndarray]
    manifest: TensorArtifactManifest | None

    @property
    def is_canonical(self) -> bool:
        return self.manifest is not None


def _number_list(value: Any, *, field: str) -> float | list[float]:
    values = value if isinstance(value, list) else [value]
    if not values:
        raise TensorArtifactError(f"quantization {field} must not be empty")
    parsed: list[float] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise TensorArtifactError(f"quantization {field} must contain numbers")
        number = float(item)
        if not math.isfinite(number):
            raise TensorArtifactError(f"quantization {field} must contain finite numbers")
        parsed.append(number)
    return parsed if isinstance(value, list) else parsed[0]


def _integer_list(value: Any, *, field: str) -> int | list[int]:
    values = value if isinstance(value, list) else [value]
    if not values:
        raise TensorArtifactError(f"quantization {field} must not be empty")
    parsed: list[int] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, int):
            raise TensorArtifactError(f"quantization {field} must contain integers")
        parsed.append(int(item))
    return parsed if isinstance(value, list) else parsed[0]


def _parse_quantization(value: Any, *, rank: int) -> QuantizationMetadata:
    if not isinstance(value, dict):
        raise TensorArtifactError("tensor quantization metadata must be an object")
    unknown = set(value) - {"scale", "zero_point", "axis", "qmin", "qmax", "scheme"}
    if unknown:
        raise TensorArtifactError(f"unknown quantization metadata fields: {sorted(unknown)}")
    if "scale" not in value or "zero_point" not in value:
        raise TensorArtifactError("quantization metadata requires scale and zero_point")

    scale = _number_list(value["scale"], field="scale")
    scale_values = scale if isinstance(scale, list) else [scale]
    if any(item <= 0 for item in scale_values):
        raise TensorArtifactError("quantization scale values must be greater than zero")
    zero_point = _integer_list(value["zero_point"], field="zero_point")
    zero_point_values = zero_point if isinstance(zero_point, list) else [zero_point]
    channel_count = max(len(scale_values), len(zero_point_values))
    if any(len(values) not in {1, channel_count} for values in (scale_values, zero_point_values)):
        raise TensorArtifactError("per-channel scale and zero_point lengths do not match")

    axis = value.get("axis")
    if axis is not None and (isinstance(axis, bool) or not isinstance(axis, int)):
        raise TensorArtifactError("quantization axis must be an integer")
    if channel_count > 1 and axis is None:
        raise TensorArtifactError("per-channel quantization requires axis")
    if axis is not None and not (-rank <= axis < rank):
        raise TensorArtifactError(f"quantization axis {axis} is invalid for tensor rank {rank}")

    qmin = value.get("qmin")
    qmax = value.get("qmax")
    for name, item in (("qmin", qmin), ("qmax", qmax)):
        if item is not None and (isinstance(item, bool) or not isinstance(item, int)):
            raise TensorArtifactError(f"quantization {name} must be an integer")
    if qmin is not None and qmax is not None and qmin >= qmax:
        raise TensorArtifactError("quantization qmin must be less than qmax")

    scheme = value.get("scheme")
    if scheme is not None and (not isinstance(scheme, str) or not scheme.strip()):
        raise TensorArtifactError("quantization scheme must be a non-empty string")
    return QuantizationMetadata(
        scale=scale,
        zero_point=zero_point,
        axis=axis,
        qmin=qmin,
        qmax=qmax,
        scheme=scheme,
    )


def _json_object(value: Mapping[str, Any] | None, *, field: str) -> dict[str, Any]:
    data = dict(value or {})
    try:
        encoded = json.dumps(data, allow_nan=False, ensure_ascii=False)
        decoded = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise TensorArtifactError(f"{field} must contain JSON-compatible finite values") from exc
    if not isinstance(decoded, dict):  # defensive: Mapping should always encode as an object
        raise TensorArtifactError(f"{field} must be an object")
    return decoded


def _validate_quantization_for_array(
    metadata: QuantizationMetadata,
    array: np.ndarray,
    *,
    name: str,
) -> None:
    if not np.issubdtype(array.dtype, np.integer):
        raise TensorArtifactError(
            f"quantization metadata for tensor {name!r} requires an integer tensor dtype"
        )

    scale_values = metadata.scale if isinstance(metadata.scale, list) else [metadata.scale]
    zero_point_values = (
        metadata.zero_point if isinstance(metadata.zero_point, list) else [metadata.zero_point]
    )
    channel_count = max(len(scale_values), len(zero_point_values))
    if channel_count > 1:
        if metadata.axis is None:  # defensive; _parse_quantization normally catches this
            raise TensorArtifactError(f"per-channel quantization for tensor {name!r} requires axis")
        axis = metadata.axis % array.ndim
        if array.shape[axis] != channel_count:
            raise TensorArtifactError(
                f"quantization channel count {channel_count} for tensor {name!r} "
                f"does not match shape {array.shape} at axis {metadata.axis}"
            )

    limits = np.iinfo(array.dtype)
    qmin = metadata.qmin if metadata.qmin is not None else limits.min
    qmax = metadata.qmax if metadata.qmax is not None else limits.max
    if qmin >= qmax:
        raise TensorArtifactError(
            f"quantization qmin must be less than qmax for tensor {name!r}"
        )
    if qmin < limits.min or qmax > limits.max:
        raise TensorArtifactError(
            f"quantization range [{qmin}, {qmax}] for tensor {name!r} exceeds dtype {array.dtype}"
        )
    if any(value < qmin or value > qmax for value in zero_point_values):
        raise TensorArtifactError(
            f"quantization zero_point for tensor {name!r} is outside [{qmin}, {qmax}]"
        )


def _normalize_quantization_map(
    quantization: Mapping[str, QuantizationMetadata | Mapping[str, Any]] | None,
    arrays: Mapping[str, np.ndarray],
) -> dict[str, QuantizationMetadata]:
    if not quantization:
        return {}
    unknown = set(quantization) - set(arrays)
    if unknown:
        raise TensorArtifactError(f"quantization metadata names unknown tensors: {sorted(unknown)}")
    parsed: dict[str, QuantizationMetadata] = {}
    for name, value in quantization.items():
        if isinstance(value, QuantizationMetadata):
            value = value.to_dict()
        if not isinstance(value, Mapping):
            raise TensorArtifactError(f"quantization metadata for tensor {name!r} must be an object")
        metadata = _parse_quantization(dict(value), rank=arrays[name].ndim)
        _validate_quantization_for_array(metadata, arrays[name], name=name)
        parsed[name] = metadata
    return parsed


def _validate_arrays(tensors: Mapping[str, np.ndarray | Sequence[Any]]) -> dict[str, np.ndarray]:
    if not tensors:
        raise TensorArtifactError("tensor artifact requires at least one tensor")
    arrays: dict[str, np.ndarray] = {}
    for name, value in tensors.items():
        if not isinstance(name, str) or not name.strip():
            raise TensorArtifactError("tensor names must be non-empty strings")
        if name == TENSOR_ARTIFACT_MANIFEST_KEY:
            raise TensorArtifactError(f"tensor name {name!r} is reserved")
        array = np.asarray(value)
        if array.dtype.kind not in {"b", "i", "u", "f"}:
            raise TensorArtifactError(f"tensor {name!r} uses unsupported non-real dtype {array.dtype}")
        arrays[name] = array
    return arrays


def create_tensor_artifact_manifest(
    tensors: Mapping[str, np.ndarray | Sequence[Any]],
    *,
    stage: str,
    source: str,
    provenance: Mapping[str, Any] | None = None,
    quantization: Mapping[str, QuantizationMetadata | Mapping[str, Any]] | None = None,
) -> TensorArtifactManifest:
    if not isinstance(stage, str) or not stage.strip():
        raise TensorArtifactError("artifact stage must be a non-empty string")
    if not isinstance(source, str) or not source.strip():
        raise TensorArtifactError("artifact source must be a non-empty string")
    arrays = _validate_arrays(tensors)
    parsed_quantization = _normalize_quantization_map(quantization, arrays)
    provenance_data = {
        **_json_object(provenance, field="provenance"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "producer": f"tensorfence {__version__}",
    }
    records = [
        TensorArtifactTensor(
            name=name,
            dtype=str(array.dtype),
            shape=[int(dim) for dim in array.shape],
            quantization=parsed_quantization.get(name),
        )
        for name, array in arrays.items()
    ]
    return TensorArtifactManifest(
        schema_version=TENSOR_ARTIFACT_SCHEMA_VERSION,
        stage=stage.strip(),
        source=source.strip(),
        tensors=records,
        provenance=provenance_data,
    )


def write_tensor_artifact(
    path: str | Path,
    tensors: Mapping[str, np.ndarray | Sequence[Any]],
    *,
    stage: str,
    source: str,
    provenance: Mapping[str, Any] | None = None,
    quantization: Mapping[str, QuantizationMetadata | Mapping[str, Any]] | None = None,
    compressed: bool = True,
) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".npz":
        raise TensorArtifactError("tensor artifact output path must use the .npz extension")
    arrays = _validate_arrays(tensors)
    manifest = create_tensor_artifact_manifest(
        arrays,
        stage=stage,
        source=source,
        provenance=provenance,
        quantization=quantization,
    )
    manifest_json = json.dumps(manifest.to_dict(), allow_nan=False, ensure_ascii=False, separators=(",", ":"))
    payload: dict[str, np.ndarray] = {
        TENSOR_ARTIFACT_MANIFEST_KEY: np.asarray(manifest_json),
        **arrays,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    writer = np.savez_compressed if compressed else np.savez
    try:
        writer(target, **payload)
    except OSError as exc:
        raise TensorArtifactError(f"failed to write tensor artifact: {target}") from exc
    return target


def _manifest_from_dict(value: Any, arrays: Mapping[str, np.ndarray]) -> TensorArtifactManifest:
    if not isinstance(value, dict):
        raise TensorArtifactError("tensor artifact manifest root must be an object")
    required = {"schema_version", "stage", "source", "tensors", "provenance"}
    missing = required - set(value)
    if missing:
        raise TensorArtifactError(f"tensor artifact manifest is missing fields: {sorted(missing)}")
    unknown = set(value) - required
    if unknown:
        raise TensorArtifactError(f"tensor artifact manifest has unknown fields: {sorted(unknown)}")
    if value["schema_version"] != TENSOR_ARTIFACT_SCHEMA_VERSION:
        raise TensorArtifactError(f"unsupported tensor artifact schema_version: {value['schema_version']!r}")
    stage = value["stage"]
    source = value["source"]
    if not isinstance(stage, str) or not stage.strip():
        raise TensorArtifactError("tensor artifact stage must be a non-empty string")
    if not isinstance(source, str) or not source.strip():
        raise TensorArtifactError("tensor artifact source must be a non-empty string")
    provenance = value["provenance"]
    if not isinstance(provenance, dict):
        raise TensorArtifactError("tensor artifact provenance must be an object")
    provenance = _json_object(provenance, field="provenance")

    raw_tensors = value["tensors"]
    if not isinstance(raw_tensors, list) or not raw_tensors:
        raise TensorArtifactError("tensor artifact manifest requires a non-empty tensors list")
    records: list[TensorArtifactTensor] = []
    seen: set[str] = set()
    for item in raw_tensors:
        if not isinstance(item, dict):
            raise TensorArtifactError("tensor artifact tensor entries must be objects")
        item_required = {"name", "dtype", "shape"}
        item_unknown = set(item) - (item_required | {"quantization"})
        if item_required - set(item) or item_unknown:
            raise TensorArtifactError("tensor artifact tensor entry has invalid fields")
        name = item["name"]
        dtype = item["dtype"]
        shape = item["shape"]
        if not isinstance(name, str) or not name or name in seen:
            raise TensorArtifactError(f"invalid or duplicate tensor name in manifest: {name!r}")
        if name not in arrays:
            raise TensorArtifactError(f"manifest describes missing tensor array: {name}")
        if not isinstance(dtype, str) or not dtype:
            raise TensorArtifactError(f"manifest tensor {name!r} has an invalid dtype")
        invalid_shape = not isinstance(shape, list) or any(
            isinstance(dim, bool) or not isinstance(dim, int) or dim < 0 for dim in shape
        )
        if invalid_shape:
            raise TensorArtifactError(f"manifest tensor {name!r} has an invalid shape")
        array = arrays[name]
        actual_shape = [int(dim) for dim in array.shape]
        if dtype != str(array.dtype) or shape != actual_shape:
            raise TensorArtifactError(
                f"manifest metadata for tensor {name!r} does not match array: "
                f"declared {dtype} {shape}, actual {array.dtype} {actual_shape}"
            )
        quantization = None
        if "quantization" in item:
            quantization = _parse_quantization(item["quantization"], rank=array.ndim)
            _validate_quantization_for_array(quantization, array, name=name)
        records.append(TensorArtifactTensor(name, dtype, list(shape), quantization))
        seen.add(name)
    extra_arrays = set(arrays) - seen
    if extra_arrays:
        raise TensorArtifactError(f"tensor artifact contains arrays absent from manifest: {sorted(extra_arrays)}")
    return TensorArtifactManifest(
        schema_version=TENSOR_ARTIFACT_SCHEMA_VERSION,
        stage=stage,
        source=source,
        tensors=records,
        provenance=provenance,
    )


def _decode_manifest(value: np.ndarray) -> Any:
    if value.ndim != 0 or value.dtype.kind not in {"U", "S"}:
        raise TensorArtifactError("tensor artifact manifest must be a scalar UTF-8 JSON string")
    raw = value.item()
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TensorArtifactError("tensor artifact manifest is not valid UTF-8") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise TensorArtifactError("tensor artifact manifest is not valid JSON") from exc


def load_tensor_artifact(path: str | Path, *, allow_legacy: bool = True) -> LoadedTensorArtifact:
    source = Path(path)
    if not source.exists():
        raise TensorArtifactError(f"tensor artifact does not exist: {source}")
    if source.suffix.lower() != ".npz":
        raise TensorArtifactError(f"tensor artifact path must use the .npz extension: {source}")
    try:
        with np.load(source, allow_pickle=False) as data:
            keys = [name for name in data.files if name != TENSOR_ARTIFACT_MANIFEST_KEY]
            arrays = _validate_arrays({name: np.asarray(data[name]) for name in keys})
            if not arrays:
                raise TensorArtifactError(f"tensor artifact does not contain any tensor arrays: {source}")
            if TENSOR_ARTIFACT_MANIFEST_KEY not in data.files:
                if not allow_legacy:
                    raise TensorArtifactError(f"legacy npz artifact has no v1 manifest: {source}")
                return LoadedTensorArtifact(tensors=arrays, manifest=None)
            manifest_value = np.asarray(data[TENSOR_ARTIFACT_MANIFEST_KEY])
    except TensorArtifactError:
        raise
    except (OSError, ValueError) as exc:
        raise TensorArtifactError(f"failed to read tensor artifact: {source}") from exc

    manifest = _manifest_from_dict(_decode_manifest(manifest_value), arrays)
    return LoadedTensorArtifact(tensors=arrays, manifest=manifest)


__all__ = [
    "LoadedTensorArtifact",
    "QuantizationMetadata",
    "TENSOR_ARTIFACT_MANIFEST_KEY",
    "TENSOR_ARTIFACT_SCHEMA_VERSION",
    "TensorArtifactError",
    "TensorArtifactManifest",
    "TensorArtifactTensor",
    "create_tensor_artifact_manifest",
    "load_tensor_artifact",
    "write_tensor_artifact",
]
