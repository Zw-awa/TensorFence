from __future__ import annotations

import json
import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .models import PluginAction, PluginManifest, TargetProfile
from .plugins import manifest_hash, plugin_enabled
from .transports import CommandResult, TargetTransport, TransportError, make_transport


class PluginHostError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExecutionContext:
    target: TargetProfile
    plugin: PluginManifest
    action: PluginAction
    inputs: dict[str, Any]
    transport: TargetTransport


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

    def __init__(self, plugins: dict[str, PluginManifest], *, handlers: dict[tuple[str, str], BuiltinHandler] | None = None) -> None:
        self.plugins = plugins
        self.handlers = handlers or {}
        self._started = False

    def start(self) -> "PluginHost":
        self._started = True
        return self

    def stop(self) -> None:
        self._started = False

    def dispose(self) -> None:
        self.stop()
        self.handlers.clear()

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
        missing = [name for name, spec in action.input_schema.items() if isinstance(spec, dict) and spec.get("required") and name not in inputs]
        if missing:
            raise PluginHostError("missing_input", "missing action inputs: " + ", ".join(missing))
        invalid = []
        for name, spec in action.input_schema.items():
            if name not in inputs or not isinstance(spec, dict):
                continue
            if spec.get("type") == "string" and not isinstance(inputs[name], str):
                invalid.append(f"{name}: expected string")
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
        context = ExecutionContext(target, plugin, action, inputs, make_transport(target))
        base = {"target": target.name, "plugin": plugin.id, "action": action.id, "read_only": action.read_only, "plugin_errors": [], "facts": [], "artifacts": [], "recommendations": [], "provenance": {"plugin_version": plugin.version, "manifest_hash": manifest_hash(plugin)}}
        handler = self.handlers.get((plugin.id, action.id))
        if plugin.runtime == "builtin-python":
            if handler is None:
                raise PluginHostError("entrypoint_unavailable", f"no Python handler registered for {plugin.id}/{action.id}")
            payload = handler(context)
            return PluginResult("ready", base | payload)
        python = target.connection.python or "python3"
        command = self._command(action, inputs, python)
        if target.connection.conda_path and target.connection.conda_env:
            command = [target.connection.conda_path, "run", "-n", target.connection.conda_env, *command]
        request = {"protocol": "tensorfence.plugin/v1", "target": target.model_dump(mode="json"), "plugin": plugin.id, "action": action.id, "inputs": inputs}
        try:
            result: CommandResult = context.transport.run(command, timeout=timeout, input_text=json.dumps(request) + "\n")
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
                    base[key] = parsed[key]
        base["result"] = parsed
        return PluginResult("ready" if result.returncode == 0 else "error", base, result.command, result.returncode, result.stdout, result.stderr)


def make_plugin_host(plugins: dict[str, PluginManifest]) -> PluginHost:
    from .builtin import register_builtin_handlers

    host = register_builtin_handlers(PluginHost(plugins))
    for plugin in plugins.values():
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
