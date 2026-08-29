from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import TargetDocument, TargetProfile


class TargetConfigError(RuntimeError):
    pass


def user_config_path() -> Path:
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return root / "TensorFence" / "targets.yaml"
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "tensorfence" / "targets.yaml"


def project_config_path(project_root: str | Path) -> Path:
    return Path(project_root) / ".tensorfence" / "targets.yaml"


def user_plugins_config_path() -> Path:
    return user_config_path().with_name("plugins.yaml")


def project_plugins_config_path(project_root: str | Path) -> Path:
    return Path(project_root) / ".tensorfence" / "plugins.yaml"


_SECRET_FIELDS = {"password", "private_key", "private_key_text", "token", "secret"}


def _secret_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        found = {str(key).lower() for key in value if str(key).lower() in _SECRET_FIELDS}
        for nested in value.values():
            found.update(_secret_keys(nested))
        return found
    if isinstance(value, list):
        result: set[str] = set()
        for nested in value:
            result.update(_secret_keys(nested))
        return result
    return set()


def _read_plugin_settings(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise TargetConfigError(f"invalid plugin configuration: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise TargetConfigError(f"invalid plugin configuration: {path}: expected mapping")
    states = raw.get("plugins", raw)
    if not isinstance(states, dict):
        raise TargetConfigError(f"invalid plugin configuration: {path}: plugins must be a mapping")
    result: dict[str, dict[str, object]] = {}
    for key, value in states.items():
        if isinstance(value, bool):
            result[str(key)] = {"enabled": value}
            continue
        if not isinstance(value, dict):
            raise TargetConfigError(f"invalid plugin configuration: {path}: {key} must be a boolean or mapping")
        unknown = set(value) - {"enabled", "config"}
        if unknown:
            raise TargetConfigError(f"invalid plugin configuration: {path}: unknown fields for {key}: {sorted(unknown)}")
        if "enabled" in value and not isinstance(value["enabled"], bool):
            raise TargetConfigError(f"invalid plugin configuration: {path}: {key}.enabled must be boolean")
        config = value.get("config", {})
        if not isinstance(config, dict):
            raise TargetConfigError(f"invalid plugin configuration: {path}: {key}.config must be a mapping")
        forbidden = _secret_keys(config)
        if forbidden:
            raise TargetConfigError(f"credentials must be environment, credential-store, or key-file references: {sorted(forbidden)}")
        result[str(key)] = {"enabled": value.get("enabled", True), "config": dict(config)}
    return result


def _read_plugin_states(path: Path) -> dict[str, bool]:
    return {key: bool(value.get("enabled", True)) for key, value in _read_plugin_settings(path).items()}


def load_plugin_states(project_root: str | Path | None = None) -> dict[str, bool]:
    states = _read_plugin_states(user_plugins_config_path())
    if project_root is not None:
        states.update(_read_plugin_states(project_plugins_config_path(project_root)))
    return states


def load_plugin_settings(project_root: str | Path | None = None) -> dict[str, dict[str, object]]:
    settings = _read_plugin_settings(user_plugins_config_path())
    if project_root is not None:
        for plugin_id, patch in _read_plugin_settings(project_plugins_config_path(project_root)).items():
            base = settings.get(plugin_id, {})
            config = dict(base.get("config", {}))
            config.update(dict(patch.get("config", {})))
            settings[plugin_id] = {**base, **patch, "config": config}
    return settings


def save_plugin_state(plugin_id: str, enabled: bool, project_root: str | Path | None = None) -> Path:
    path = project_plugins_config_path(project_root) if project_root is not None else user_plugins_config_path()
    settings = _read_plugin_settings(path)
    current = settings.get(plugin_id, {})
    settings[plugin_id] = {**current, "enabled": enabled}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"plugins": settings}, sort_keys=False), encoding="utf-8")
    return path


def _read_document(path: Path) -> TargetDocument:
    if not path.exists():
        return TargetDocument()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return TargetDocument.model_validate(raw or {})
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise TargetConfigError(f"invalid target configuration: {path}: {exc}") from exc


def load_targets(project_root: str | Path | None = None) -> dict[str, TargetProfile]:
    """Return global targets with project targets overriding identical names."""
    targets = {target.name: target for target in _read_document(user_config_path()).targets}
    if project_root is not None:
        targets.update({target.name: target for target in _read_document(project_config_path(project_root)).targets})
    return targets


def save_target(target: TargetProfile, project_root: str | Path | None = None) -> Path:
    path = project_config_path(project_root) if project_root is not None else user_config_path()
    document = _read_document(path)
    targets = [item for item in document.targets if item.name != target.name]
    targets.append(target)
    updated = TargetDocument(targets=targets)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(updated.model_dump(mode="python"), sort_keys=False), encoding="utf-8")
    return path


def load_profile(name: str, **kwargs):
    from .profiles import load_profile as _load_profile
    return _load_profile(name, **kwargs)


def resolve_profile(name: str | None = None, project_root: str | Path | None = None, **kwargs):
    from .profiles import resolve_profile as _resolve_profile
    return _resolve_profile(name, project_root, **kwargs)


def save_profile(name: str, project_root: str | Path | None = None) -> Path:
    from .profiles import save_profile_use
    return save_profile_use(name, project_root)
