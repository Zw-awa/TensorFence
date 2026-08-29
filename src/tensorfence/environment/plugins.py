from __future__ import annotations

from importlib.resources import files
from importlib import metadata
import hashlib
import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from .config import load_plugin_settings, user_config_path
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
    try:
        entry_points = metadata.entry_points()
        selected = entry_points.select(group="tensorfence.plugins") if hasattr(entry_points, "select") else entry_points.get("tensorfence.plugins", [])
        for entry_point in selected:
            try:
                value = entry_point.load()
                manifest = value() if callable(value) and not isinstance(value, PluginManifest) else value
                if isinstance(manifest, PluginManifest):
                    plugins[manifest.id] = manifest
            except Exception as exc:
                errors.append(f"failed to load plugin entry point {entry_point.name}: {exc}")
    except Exception:
        pass
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
    settings = load_plugin_settings(project_root)
    for plugin_id, plugin in list(plugins.items()):
        if plugin_id in settings:
            item = settings[plugin_id]
            config = dict(plugin.config)
            config.update(dict(item.get("config", {})))
            plugins[plugin_id] = plugin.model_copy(update={"enabled": item.get("enabled"), "config": config})
    try:
        from .profiles import resolve_profile
        from .profiles import global_config_file, profile_config_path, project_config_file
        root = Path(project_root) if project_root is not None else None
        has_selection = global_config_file().exists() or profile_config_path().exists() or (root is not None and (project_config_file(root).exists() or profile_config_path(root).exists()))
        if not has_selection:
            return plugins, errors
        profile = resolve_profile(project_root=project_root)
        for plugin_id, patch in profile.plugins.items():
            if plugin_id not in plugins:
                continue
            plugin = plugins[plugin_id]
            config = dict(plugin.config)
            config.update(dict(patch.get("config", {})))
            plugins[plugin_id] = plugin.model_copy(update={"enabled": patch.get("enabled", plugin.enabled), "config": config})
    except Exception as exc:
        errors.append(f"invalid profile configuration: {exc}")
    return plugins, errors


def plugin_enabled(plugin: PluginManifest, cli_override: bool | None = None) -> bool:
    if cli_override is not None:
        return cli_override
    return plugin.default_enabled if plugin.enabled is None else plugin.enabled


def manifest_hash(plugin: PluginManifest) -> str:
    encoded = json.dumps(plugin.model_dump(mode="json", exclude={"installed", "enabled"}), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
