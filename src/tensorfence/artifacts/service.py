from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .tensor_artifact import LoadedTensorArtifact, load_tensor_artifact, write_tensor_artifact


class ArtifactPathError(ValueError):
    pass


class ArtifactStore:
    """Artifact boundary exposed to plugins; paths stay inside the configured root."""

    def __init__(self, root: str | Path = ".tensorfence/artifacts") -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str | Path) -> Path:
        candidate = (self.root / Path(name)).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ArtifactPathError(f"artifact path escapes store: {name}")
        return candidate

    def read(self, name: str | Path, *, allow_legacy: bool = True) -> LoadedTensorArtifact:
        return load_tensor_artifact(self.path(name), allow_legacy=allow_legacy)

    def write(self, name: str | Path, tensors: Mapping[str, Any], *, stage: str, source: str,
              provenance: Mapping[str, Any] | None = None, quantization: Mapping[str, Any] | None = None) -> Path:
        target = self.path(name)
        return write_tensor_artifact(target, tensors, stage=stage, source=source,
                                     provenance=dict(provenance or {}), quantization=quantization)

    def validate(self, name: str | Path) -> LoadedTensorArtifact:
        return self.read(name, allow_legacy=False)


class ArtifactReader:
    def __init__(self, store: ArtifactStore): self.store = store
    def read(self, name: str | Path) -> LoadedTensorArtifact: return self.store.read(name)


class ArtifactWriter:
    def __init__(self, store: ArtifactStore): self.store = store
    def write(self, name: str | Path, tensors: Mapping[str, Any], **kwargs: Any) -> Path: return self.store.write(name, tensors, **kwargs)


class ArtifactValidator:
    def __init__(self, store: ArtifactStore): self.store = store
    def validate(self, name: str | Path) -> LoadedTensorArtifact: return self.store.validate(name)


__all__ = ["ArtifactPathError", "ArtifactStore", "ArtifactReader", "ArtifactWriter", "ArtifactValidator"]
