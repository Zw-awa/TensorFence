"""Portable target environments, discovery, and plugin manifests."""

from .config import TargetConfigError, load_targets, save_target, user_config_path
from .discovery import discover_target, evaluate_compatibility
from .models import EnvironmentFacts, TargetProfile
from .plugins import discover_plugins, load_builtin_plugins

__all__ = [
    "EnvironmentFacts",
    "TargetConfigError",
    "TargetProfile",
    "discover_plugins",
    "discover_target",
    "evaluate_compatibility",
    "load_builtin_plugins",
    "load_targets",
    "save_target",
    "user_config_path",
]
