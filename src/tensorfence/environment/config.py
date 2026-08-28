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


def _read_plugin_states(path: Path) -> dict[str, bool]:
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
    invalid = [str(key) for key, value in states.items() if not isinstance(value, bool)]
    if invalid:
        raise TargetConfigError(f"invalid plugin configuration: {path}: enabled values must be booleans ({', '.join(invalid)})")
    return {str(key): value for key, value in states.items()}


def load_plugin_states(project_root: str | Path | None = None) -> dict[str, bool]:
    states = _read_plugin_states(user_plugins_config_path())
    if project_root is not None:
        states.update(_read_plugin_states(project_plugins_config_path(project_root)))
    return states


def save_plugin_state(plugin_id: str, enabled: bool, project_root: str | Path | None = None) -> Path:
    path = project_plugins_config_path(project_root) if project_root is not None else user_plugins_config_path()
    states = _read_plugin_states(path)
    states[plugin_id] = enabled
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"plugins": states}, sort_keys=False), encoding="utf-8")
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
