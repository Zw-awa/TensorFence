from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import yaml
from pydantic import ValidationError

from .config import user_config_path
from .models import PluginManifest


class PluginError(RuntimeError):
    pass


def _load_manifest(path: Path) -> PluginManifest:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return PluginManifest.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise PluginError(f"invalid plugin manifest: {path}: {exc}") from exc


def _manifest_paths(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")])


def load_builtin_plugins() -> dict[str, PluginManifest]:
    root = files("tensorfence.environment").joinpath("builtin_plugins")
    return {
        path.name.rsplit(".", 1)[0]: _load_manifest(Path(str(path)))
        for path in root.iterdir()
        if path.name.endswith((".yaml", ".yml"))
    }


def discover_plugins(project_root: str | Path | None = None) -> tuple[dict[str, PluginManifest], list[str]]:
    plugins = {item.id: item for item in load_builtin_plugins().values()}
    errors: list[str] = []
    directories = [user_config_path().parent / "plugins"]
    if project_root is not None:
        directories.append(Path(project_root) / ".tensorfence" / "plugins")
    for directory in directories:
        for path in _manifest_paths(directory):
            try:
                manifest = _load_manifest(path)
                plugins[manifest.id] = manifest
            except PluginError as exc:
                errors.append(str(exc))
    return plugins, errors
