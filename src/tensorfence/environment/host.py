from __future__ import annotations

import json
import importlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from .models import PluginAction, PluginManifest, TargetProfile
from .plugins import manifest_hash, plugin_enabled
from .transports import CommandResult, TargetTransport, TransportError, TransportTimeoutError, make_transport


class PluginHostError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PluginLifecycle(str, Enum):
    DISCOVERED = "discover"
    VALIDATED = "validate"
    ENABLED = "enable"
    STARTED = "start"
    STOPPED = "stop"
    DISPOSED = "dispose"


class ServiceRegistry:
    """Small dependency-injection registry shared by built-in plugins."""

    def __init__(self) -> None:
        self._services: dict[str, object] = {}

    def register(self, name: str, service: object, *, replace: bool = False) -> object:
        if name in self._services and not replace:
            raise PluginHostError("service_already_registered", f"service already registered: {name}")
        self._services[name] = service
        return service

    def get(self, name: str, default: object | None = None) -> object | None:
        return self._services.get(name, default)

    def require(self, name: str) -> object:
        value = self.get(name)
        if value is None:
            raise PluginHostError("missing_service", f"required service is unavailable: {name}")
        return value

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._services))

    def dispose(self) -> None:
        for service in self._services.values():
            dispose = getattr(service, "dispose", None)
            if callable(dispose):
                dispose()
        self._services.clear()


@dataclass(frozen=True)
class ExecutionContext:
    target: TargetProfile
    plugin: PluginManifest
    action: PluginAction
    inputs: dict[str, Any]
    transport: TargetTransport
    services: ServiceRegistry | None = None
    plugin_config: dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def profile(self) -> str:
        return self.target.profile

    @property
    def artifact_store(self) -> object | None:
        return self.services.get("artifact.store") if self.services else None


@dataclass(frozen=True)
class PluginResult:
    status: str
    payload: dict[str, Any]
    command: list[str] = field(default_factory=list)
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""

    def envelope(self) -> dict[str, Any]:
        return {
            "status": self.status,
            **self.payload,
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


BuiltinHandler = Callable[[ExecutionContext], dict[str, Any]]


class PluginHost:
    """Compose and execute built-in Python or external JSON plugins."""

    def __init__(self, plugins: dict[str, PluginManifest], *, handlers: dict[tuple[str, str], BuiltinHandler] | None = None, services: ServiceRegistry | None = None, plugin_config: dict[str, dict[str, Any]] | None = None) -> None:
        self.plugins = plugins
        self.handlers = handlers or {}
        self._started = False
        self.services = services or ServiceRegistry()
        self.plugin_config = plugin_config or {}
        self.loader: PluginLoader | None = None

    def start(self) -> "PluginHost":
        self._started = True
        return self

    def stop(self) -> None:
        self._started = False
        if self.loader is not None:
            self.loader.stop()

    def dispose(self) -> None:
        self.stop()
        self.handlers.clear()
        self.services.dispose()
        if self.loader is not None:
            self.loader.dispose()

    def __enter__(self) -> "PluginHost":
        return self.start()

    def __exit__(self, _exc_type: object, _exc_value: object, _traceback: object) -> None:
        self.dispose()

    def register(self, plugin_id: str, action_id: str, handler: BuiltinHandler) -> None:
        self.handlers[(plugin_id, action_id)] = handler

    @staticmethod
    def _inputs(args: list[str] | None, input_json: str | None) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for item in args or []:
            if "=" not in item:
                raise PluginHostError("invalid_input", f"--input expects key=value: {item}")
            key, value = item.split("=", 1)
            if not key:
                raise PluginHostError("invalid_input", "input key must not be empty")
            values[key] = value
        if input_json:
            try:
                loaded = json.loads(Path(input_json).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PluginHostError("invalid_input_json", str(exc)) from exc
            if not isinstance(loaded, dict):
                raise PluginHostError("invalid_input_json", "input JSON root must be an object")
            values.update(loaded)
        return values

    def _lookup(self, target: TargetProfile, plugin_id: str, action_id: str, override: bool | None, allow_side_effects: bool) -> tuple[PluginManifest, PluginAction]:
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            raise PluginHostError("plugin_not_found", f"plugin not found: {plugin_id}")
        if target.plugin_ids and plugin.id not in target.plugin_ids:
            raise PluginHostError("plugin_not_allowed", f"plugin is not enabled for target: {plugin.id}")
        if not plugin_enabled(plugin, override):
            raise PluginHostError("plugin_disabled", f"plugin is disabled: {plugin.id}")
        if plugin.profiles and target.profile not in plugin.profiles:
            raise PluginHostError("unsupported_profile", f"plugin does not support target profile: {target.profile}")
        for requirement in plugin.requires:
            if requirement in self.plugins and not plugin_enabled(self.plugins[requirement]):
                raise PluginHostError("missing_dependency", f"required plugin is disabled: {requirement}")
            if self.services.get(requirement) is None and requirement not in self.plugins and not any(requirement in item.provides and plugin_enabled(item) for item in self.plugins.values()):
                raise PluginHostError("missing_service", f"required service is unavailable: {requirement}")
        action = next((item for item in plugin.actions if item.id == action_id), None)
        if action is None:
            raise PluginHostError("action_not_found", f"action not found: {plugin_id}/{action_id}")
        if action.profiles and target.profile not in action.profiles:
            raise PluginHostError("unsupported_profile", f"action does not support target profile: {target.profile}")
        if not action.read_only and not allow_side_effects:
            raise PluginHostError("side_effect_confirmation_required", "refusing side-effectful action without --allow-side-effects")
        return plugin, action

    @staticmethod
    def _validate(action: PluginAction, inputs: dict[str, Any]) -> None:
        unknown = sorted(set(inputs) - set(action.input_schema)) if action.input_schema else []
        if unknown:
            raise PluginHostError("invalid_input", "unknown action inputs: " + ", ".join(unknown))
        missing = [name for name, spec in action.input_schema.items() if isinstance(spec, dict) and spec.get("required") and name not in inputs]
        if missing:
            raise PluginHostError("missing_input", "missing action inputs: " + ", ".join(missing))
        invalid = []
        for name, spec in action.input_schema.items():
            if name not in inputs or not isinstance(spec, dict):
                continue
            expected = spec.get("type")
            valid = {"string": isinstance(inputs[name], str), "integer": isinstance(inputs[name], int) and not isinstance(inputs[name], bool), "number": isinstance(inputs[name], (int, float)) and not isinstance(inputs[name], bool), "boolean": isinstance(inputs[name], bool), "object": isinstance(inputs[name], dict)}.get(expected, True)
            if not valid:
                invalid.append(f"{name}: expected {expected}")
        if invalid:
            raise PluginHostError("invalid_input", "; ".join(invalid))

    @staticmethod
    def _command(action: PluginAction, inputs: dict[str, Any], python: str) -> list[str]:
        def expand(template: str) -> str:
            value = template
            for key, item in inputs.items():
                value = value.replace("{input:" + key + "}", str(item))
            return value.format(python=python)
        return [expand(item) for item in action.command]

    def execute(self, target: TargetProfile, plugin_id: str, action_id: str, *, input_args: list[str] | None = None, input_json: str | None = None, timeout: int = 30, enable_override: bool | None = None, allow_side_effects: bool = False) -> PluginResult:
        plugin, action = self._lookup(target, plugin_id, action_id, enable_override, allow_side_effects)
        inputs = self._inputs(input_args, input_json)
        self._validate(action, inputs)
        provenance = {"plugin_version": plugin.version, "manifest_hash": manifest_hash(plugin)}
        context = ExecutionContext(target, plugin, action, inputs, make_transport(target), self.services, self.plugin_config.get(plugin.id, plugin.config), timeout, provenance)
        base = {"target": target.name, "profile": target.profile, "plugin": plugin.id, "action": action.id, "read_only": action.read_only, "plugin_errors": [], "facts": [], "artifacts": [], "recommendations": [], "provenance": provenance}
        handler = self.handlers.get((plugin.id, action.id))
        if plugin.runtime == "builtin-python":
            if handler is None:
                raise PluginHostError("entrypoint_unavailable", f"no Python handler registered for {plugin.id}/{action.id}")
            try:
                payload = handler(context)
            except PluginHostError:
                raise
            except Exception as exc:
                raise PluginHostError("plugin_crashed", f"builtin plugin {plugin.id} failed: {exc}") from exc
            return PluginResult("ready", base | payload)
        if not action.command:
            raise PluginHostError("invalid_action", f"external action has no command: {plugin.id}/{action.id}")
        python = target.connection.python or "python3"
        command = self._command(action, inputs, python)
        if target.connection.conda_path and target.connection.conda_env:
            command = [target.connection.conda_path, "run", "-n", target.connection.conda_env, *command]
        request = {"protocol": "tensorfence.plugin/v1", "target": target.model_dump(mode="json"), "plugin": plugin.id, "action": action.id, "inputs": inputs, "config": context.plugin_config}
        try:
            result: CommandResult = context.transport.run(command, timeout=timeout, input_text=json.dumps(request) + "\n")
        except TransportTimeoutError as exc:
            raise PluginHostError("timeout", str(exc)) from exc
        except TransportError as exc:
            raise PluginHostError("transport_error", str(exc)) from exc
        parsed: Any = None
        if result.stdout:
            try:
                parsed = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        if isinstance(parsed, dict):
            for key in ("status", "facts", "artifacts", "recommendations", "provenance"):
                if key in parsed:
                    if key == "provenance" and isinstance(parsed[key], dict):
                        base[key] = {**base[key], **parsed[key]}
                    else:
                        base[key] = parsed[key]
        elif result.stdout:
            base["status"] = "error"
            base["error"] = {"code": "invalid_envelope", "message": "external plugin stdout is not a JSON object"}
        if result.returncode != 0:
            base["error"] = {"code": "crashed" if result.returncode < 0 else "nonzero_exit", "message": result.stderr or f"plugin exited with code {result.returncode}"}
        base["result"] = parsed
        status = "ready" if result.returncode == 0 else ("crashed" if result.returncode < 0 else "error")
        return PluginResult(status, base, result.command, result.returncode, result.stdout, result.stderr)


class PluginLoader:
    """Discover, validate and resolve plugin dependencies before creating a host."""

    def __init__(self, plugins: dict[str, PluginManifest] | list[PluginManifest] | None = None, *, enabled: dict[str, bool] | None = None) -> None:
        if plugins is None:
            plugins = {}
        self.plugins = {item.id: item for item in plugins} if isinstance(plugins, list) else dict(plugins)
        self.enabled = enabled or {}
        self.states: dict[str, PluginLifecycle] = {key: PluginLifecycle.DISCOVERED for key in self.plugins}

    @classmethod
    def discover(cls, project_root: str | Path | None = None) -> "PluginLoader":
        from .plugins import discover_plugins
        plugins, errors = discover_plugins(project_root)
        if errors:
            raise PluginHostError("plugin_discovery_failed", "; ".join(errors))
        return cls(plugins)

    def validate(self) -> None:
        providers: dict[str, str] = {}
        for plugin in self.plugins.values():
            if plugin.runtime == "builtin-python" and not plugin.entrypoint:
                raise PluginHostError("invalid_entrypoint", f"builtin-python plugin has no entrypoint: {plugin.id}")
            if plugin.runtime == "external-json" and any(not action.command for action in plugin.actions):
                raise PluginHostError("invalid_action", f"external action has no command: {plugin.id}")
            for service in plugin.provides:
                if service in providers and providers[service] != plugin.id:
                    raise PluginHostError("duplicate_service", f"service {service} provided by both {providers[service]} and {plugin.id}")
                providers[service] = plugin.id
            missing = [item for item in plugin.requires if item not in self.plugins and item not in providers and item not in {p for other in self.plugins.values() for p in other.provides}]
            if missing:
                raise PluginHostError("missing_dependency", f"plugin {plugin.id} requires missing service/plugin: {', '.join(missing)}")
            self.states[plugin.id] = PluginLifecycle.VALIDATED

    def resolve(self) -> list[PluginManifest]:
        self.validate()
        ordered: list[PluginManifest] = []
        visiting: set[str] = set()
        visited: set[str] = set()
        def visit(plugin_id: str) -> None:
            if plugin_id in visiting:
                raise PluginHostError("circular_dependency", f"circular plugin dependency involving {plugin_id}")
            if plugin_id in visited or plugin_id not in self.plugins:
                return
            visiting.add(plugin_id)
            for requirement in self.plugins[plugin_id].requires:
                if requirement in self.plugins:
                    visit(requirement)
                else:
                    provider = next((p.id for p in self.plugins.values() if requirement in p.provides), None)
                    if provider:
                        visit(provider)
            visiting.remove(plugin_id); visited.add(plugin_id); ordered.append(self.plugins[plugin_id])
        for plugin_id in self.plugins:
            visit(plugin_id)
        return ordered

    def enable(self, plugin_id: str) -> None:
        if plugin_id not in self.plugins:
            raise PluginHostError("plugin_not_found", f"plugin not found: {plugin_id}")
        self.enabled[plugin_id] = True; self.states[plugin_id] = PluginLifecycle.ENABLED

    def start(self) -> list[PluginManifest]:
        ordered = self.resolve()
        for plugin in ordered:
            if self.enabled.get(plugin.id, plugin.default_enabled):
                self.states[plugin.id] = PluginLifecycle.STARTED
        return ordered

    def stop(self) -> None:
        for plugin_id, state in list(self.states.items()):
            if state == PluginLifecycle.STARTED:
                self.states[plugin_id] = PluginLifecycle.STOPPED

    def dispose(self) -> None:
        self.stop()
        for plugin_id in self.states:
            self.states[plugin_id] = PluginLifecycle.DISPOSED


def make_plugin_host(plugins: dict[str, PluginManifest]) -> PluginHost:
    from .builtin import register_builtin_handlers

    loader = PluginLoader(plugins)
    ordered = loader.start()
    host = register_builtin_handlers(PluginHost(plugins, plugin_config={item.id: dict(item.config) for item in plugins.values()}))
    host.loader = loader
    for plugin in ordered:
        if not plugin_enabled(plugin):
            continue
        if plugin.runtime != "builtin-python" or not plugin.entrypoint:
            continue
        module_name, separator, function_name = plugin.entrypoint.partition(":")
        if not separator or not module_name or not function_name:
            raise PluginHostError("invalid_entrypoint", f"invalid plugin entrypoint: {plugin.entrypoint}")
        try:
            register = getattr(importlib.import_module(module_name), function_name)
            register(host)
        except (ImportError, AttributeError, TypeError) as exc:
            raise PluginHostError("entrypoint_unavailable", f"failed to load {plugin.id} entrypoint: {exc}") from exc
    return host
