"""Portable target environments, discovery, and plugin manifests."""

from .config import TargetConfigError, load_targets, save_target, user_config_path
from .discovery import discover_target, evaluate_compatibility
from .models import EnvironmentFacts, TargetProfile
from .plugins import discover_plugins, load_builtin_plugins, manifest_hash, plugin_enabled
from .host import ExecutionContext, PluginHost, PluginHostError, PluginResult, PluginLoader, PluginLifecycle, ServiceRegistry, make_plugin_host
from .profiles import BUILTIN_PROFILES, Profile, ProfileError, load_profile, resolve_profile, save_profile_use

__all__ = [
    "EnvironmentFacts",
    "TargetConfigError",
    "TargetProfile",
    "discover_plugins",
    "discover_target",
    "evaluate_compatibility",
    "load_builtin_plugins",
    "manifest_hash",
    "plugin_enabled",
    "ExecutionContext",
    "PluginHost",
    "PluginHostError",
    "PluginResult",
    "make_plugin_host",
    "PluginLoader",
    "PluginLifecycle",
    "ServiceRegistry",
    "BUILTIN_PROFILES",
    "Profile",
    "ProfileError",
    "load_profile",
    "resolve_profile",
    "save_profile_use",
    "load_targets",
    "save_target",
    "user_config_path",
]
