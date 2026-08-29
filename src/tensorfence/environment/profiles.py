from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .models import PluginManifest
from .config import project_plugins_config_path, user_plugins_config_path


class ProfileError(ValueError):
    pass


BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "default": {"plugins": {
        "tensorfence.core": {"enabled": True},
        "tensorfence.environment": {"enabled": True},
        "tensorfence.artifact": {"enabled": True},
        "tensorfence.onnx": {"enabled": True},
        "tensorfence.rknn": {"enabled": False},
        "tensorfence.compare": {"enabled": True},
        "tensorfence.diagnose": {"enabled": True},
    }},
    "offline-analysis": {
        "plugins": {
            "tensorfence.core": {"enabled": True},
            "tensorfence.onnx": {"enabled": True},
            "tensorfence.diagnostics": {"enabled": True},
            "tensorfence.rknn": {"enabled": False},
        }
    },
    "onnx-host": {"plugins": {"tensorfence.onnx": {"enabled": True}}},
    "rknn-host": {"plugins": {"tensorfence.rknn": {"enabled": True}}},
    "rk3588-board": {"plugins": {"tensorfence.rknn": {"enabled": True}}},
}


@dataclass(frozen=True)
class Profile:
    name: str
    plugins: dict[str, dict[str, Any]]
    config: dict[str, Any]

    def enabled(self, plugin: PluginManifest) -> bool:
        value = self.plugins.get(plugin.id, {}).get("enabled")
        return plugin.default_enabled if value is None else bool(value)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ProfileError(f"{label} must be a mapping")
    return dict(value)


def _merge(base: dict[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_profile(name: str, *, global_config: Mapping[str, Any] | None = None,
                 project_config: Mapping[str, Any] | None = None,
                 cli_overrides: Mapping[str, Any] | None = None) -> Profile:
    if name not in BUILTIN_PROFILES:
        raise ProfileError(f"profile not found: {name}")
    merged: dict[str, Any] = _merge(BUILTIN_PROFILES[name], _mapping(global_config, "global config"))
    merged = _merge(merged, _mapping(project_config, "project config"))
    merged = _merge(merged, _mapping(cli_overrides, "CLI overrides"))
    plugins = _mapping(merged.get("plugins"), "plugins")
    normalized: dict[str, dict[str, Any]] = {}
    for plugin_id, value in plugins.items():
        item = _mapping(value, f"plugins.{plugin_id}")
        unknown = set(item) - {"enabled", "config"}
        if unknown:
            raise ProfileError(f"unknown profile fields for {plugin_id}: {sorted(unknown)}")
        if "enabled" in item and not isinstance(item["enabled"], bool):
            raise ProfileError(f"plugins.{plugin_id}.enabled must be boolean")
        normalized[str(plugin_id)] = item
    config = _mapping(merged.get("config"), "config")
    unknown_root = set(merged) - {"plugins", "config"}
    if unknown_root:
        raise ProfileError(f"unknown profile fields: {sorted(unknown_root)}")
    return Profile(name=name, plugins=normalized, config=config)


def load_profile_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        return {}
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ProfileError(f"invalid profile configuration: {source}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError(f"invalid profile configuration: {source}: expected mapping")
    return raw


def profile_config_path(project_root: str | Path | None = None) -> Path:
    if project_root is None:
        return user_plugins_config_path().with_name("profile.yaml")
    return Path(project_root) / ".tensorfence" / "profile.yaml"


def project_config_file(project_root: str | Path) -> Path:
    return Path(project_root) / ".tensorfence" / "config.yaml"


def global_config_file() -> Path:
    return user_plugins_config_path().with_name("config.yaml")


def resolve_profile(name: str | None = None, project_root: str | Path | None = None,
                    cli_overrides: Mapping[str, Any] | None = None) -> Profile:
    """Resolve built-in, global, project and ephemeral CLI profile patches."""
    root = Path(project_root) if project_root is not None else None
    global_data = _merge(load_profile_file(global_config_file()), load_profile_file(profile_config_path()))
    project_data = load_profile_file(profile_config_path(root)) if root is not None else {}
    if root is not None:
        project_data = _merge(load_profile_file(project_config_file(root)), project_data)
    selected = name or project_data.get("profile") or global_data.get("profile") or "default"
    # Legacy plugins.yaml remains an input during migration, but never stores secrets.
    legacy: dict[str, Any] = {}
    try:
        from .config import load_plugin_states
        legacy = {"plugins": {key: {"enabled": value} for key, value in load_plugin_states(root).items()}}
    except Exception:
        legacy = {}
    if legacy:
        global_data = _merge(global_data, legacy)
    global_patch = {key: value for key, value in global_data.items() if key != "profile"}
    project_patch = {key: value for key, value in project_data.items() if key != "profile"}
    return load_profile(selected, global_config=global_patch, project_config=project_patch, cli_overrides=cli_overrides)


def save_profile_use(name: str, project_root: str | Path | None = None) -> Path:
    if name not in BUILTIN_PROFILES:
        raise ProfileError(f"profile not found: {name}")
    path = profile_config_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"profile": name}, sort_keys=False), encoding="utf-8")
    return path


__all__ = ["BUILTIN_PROFILES", "Profile", "ProfileError", "load_profile", "load_profile_file", "resolve_profile", "save_profile_use", "profile_config_path"]
