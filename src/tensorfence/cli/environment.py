from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from ..environment import TargetProfile, discover_plugins, discover_target, evaluate_compatibility, load_targets, save_target
from ..environment.models import TargetConnection, VersionPolicy
from ..environment.plugins import PluginError
from ..environment.transports import TransportError, make_transport


def _emit(payload: object, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                print(f"{key}: {value}")
    else:
        print(payload)


def _project_root(value: str | None) -> Path:
    return Path(value).resolve() if value else Path.cwd()


def _target_or_error(name: str, project_root: Path) -> TargetProfile | None:
    target = load_targets(project_root).get(name)
    if target is None:
        print(f"ERROR: target not found: {name}", file=sys.stderr)
    return target


def _facts_payload(facts) -> dict[str, object]:
    return facts.model_dump(mode="json") | {"overall_status": facts.overall_status()}


def cmd_plugins_list(args: argparse.Namespace) -> int:
    plugins, errors = discover_plugins(_project_root(args.project_root))
    payload = {
        "plugins": [plugin.model_dump(mode="json") for plugin in sorted(plugins.values(), key=lambda item: item.id)],
        "errors": errors,
    }
    _emit(payload, args.format)
    return 0 if not errors else 1


def cmd_environment_discover(args: argparse.Namespace) -> int:
    project_root = _project_root(args.project_root)
    target = _target_or_error(args.target, project_root)
    if target is None:
        return 2
    facts = discover_target(target)
    _emit(_facts_payload(facts), args.format)
    return 0


def cmd_environment_check(args: argparse.Namespace) -> int:
    project_root = _project_root(args.project_root)
    target = _target_or_error(args.target, project_root)
    if target is None:
        return 2
    facts = evaluate_compatibility(discover_target(target))
    _emit(_facts_payload(facts), args.format)
    return 2 if facts.overall_status() == "blocked" else 0


def cmd_target_list(args: argparse.Namespace) -> int:
    targets = load_targets(_project_root(args.project_root))
    payload = {"targets": [target.model_dump(mode="json") for target in sorted(targets.values(), key=lambda item: item.name)]}
    _emit(payload, args.format)
    return 0


def cmd_target_show(args: argparse.Namespace) -> int:
    target = _target_or_error(args.name, _project_root(args.project_root))
    if target is None:
        return 2
    _emit(target.model_dump(mode="json"), args.format)
    return 0


def _updated_target(args: argparse.Namespace, current: TargetProfile | None) -> TargetProfile:
    requested_profile = args.profile or (current.profile if current else "generic-linux")
    if current is None:
        default_policy = {
            "generic-linux": VersionPolicy(python=">=3.10"),
            "rknn-host": VersionPolicy(python=">=3.10", rknn_toolkit=">=2.3.2,<2.4"),
            "rk3588-board": VersionPolicy(python=">=3.10"),
        }[requested_profile]
        current = TargetProfile(name=args.name, profile=requested_profile, version_policy=default_policy)
    connection = current.connection.model_copy(
        update={
            key: value
            for key, value in {
                "wsl_distro": args.wsl_distro,
                "host": args.host,
                "user": args.user,
                "port": args.port,
                "identity_file": args.identity_file,
                "python": args.python,
                "conda_path": args.conda_path,
                "conda_env": args.conda_env,
            }.items()
            if value is not None
        }
    )
    policy = current.version_policy.model_copy(
        update={
            key: value
            for key, value in {
                "python": args.require_python,
                "rknn_toolkit": args.require_rknn_toolkit,
                "rknn_runtime": args.require_rknn_runtime,
            }.items()
            if value is not None
        }
    )
    return TargetProfile(
        name=args.name,
        profile=requested_profile,
        transport=args.transport or current.transport,
        connection=connection,
        plugin_ids=args.plugin if args.plugin is not None else current.plugin_ids,
        version_policy=policy,
        notes=args.note if args.note is not None else current.notes,
    )


def cmd_target_upsert(args: argparse.Namespace) -> int:
    root = None if args.global_config else _project_root(args.project_root)
    current = load_targets(root).get(args.name)
    try:
        target = _updated_target(args, current)
    except ValidationError as exc:
        print(f"ERROR: invalid target: {exc}", file=sys.stderr)
        return 2
    path = save_target(target, root)
    _emit({"saved": str(path), "target": target.model_dump(mode="json")}, args.format)
    return 0


def _target_python(target: TargetProfile) -> str:
    return target.connection.python or "python3"


def _wrap_target_python(target: TargetProfile, command: list[str]) -> list[str]:
    if target.connection.conda_path and target.connection.conda_env:
        return [target.connection.conda_path, "run", "-n", target.connection.conda_env, *command]
    return command


def cmd_target_run(args: argparse.Namespace) -> int:
    root = _project_root(args.project_root)
    target = _target_or_error(args.name, root)
    if target is None:
        return 2
    try:
        plugins, errors = discover_plugins(root)
    except PluginError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    plugin = plugins.get(args.plugin)
    if plugin is None:
        print(f"ERROR: plugin not found: {args.plugin}", file=sys.stderr)
        return 2
    action = next((item for item in plugin.actions if item.id == args.action), None)
    if action is None:
        print(f"ERROR: action not found: {args.plugin}/{args.action}", file=sys.stderr)
        return 2
    if not action.read_only and not args.allow_side_effects:
        print("ERROR: refusing side-effectful action without --allow-side-effects", file=sys.stderr)
        return 2
    variables = {"python": _target_python(target)}
    try:
        command = _wrap_target_python(target, [item.format(**variables) for item in action.command])
        result = make_transport(target).run(command, timeout=args.timeout)
    except (KeyError, TransportError) as exc:
        print(f"ERROR: failed to execute target action: {exc}", file=sys.stderr)
        return 2
    payload = {
        "target": target.name,
        "plugin": plugin.id,
        "action": action.id,
        "read_only": action.read_only,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "plugin_errors": errors,
    }
    _emit(payload, args.format)
    return result.returncode


def build_parser(subparsers) -> None:
    plugins = subparsers.add_parser("plugins", help="discover portable environment plugins")
    plugin_subparsers = plugins.add_subparsers(dest="plugins_command", required=True)
    plugin_list = plugin_subparsers.add_parser("list", help="list built-in, user, and project plugin manifests")
    plugin_list.add_argument("--project-root")
    plugin_list.add_argument("--format", choices=("text", "json"), default="text")
    plugin_list.set_defaults(func=cmd_plugins_list)

    environment = subparsers.add_parser("environment", help="discover and check a configured target")
    environment_subparsers = environment.add_subparsers(dest="environment_command", required=True)
    for name, handler, help_text in (
        ("discover", cmd_environment_discover, "collect read-only target facts"),
        ("check", cmd_environment_check, "collect facts and evaluate profile policy"),
    ):
        command = environment_subparsers.add_parser(name, help=help_text)
        command.add_argument("--target", required=True)
        command.add_argument("--project-root")
        command.add_argument("--format", choices=("text", "json"), default="text")
        command.set_defaults(func=handler)

    target = subparsers.add_parser("target", help="manage portable target profiles")
    target_subparsers = target.add_subparsers(dest="target_command", required=True)
    target_list = target_subparsers.add_parser("list", help="list global and project targets")
    target_list.add_argument("--project-root")
    target_list.add_argument("--format", choices=("text", "json"), default="text")
    target_list.set_defaults(func=cmd_target_list)
    target_show = target_subparsers.add_parser("show", help="show a target profile")
    target_show.add_argument("name")
    target_show.add_argument("--project-root")
    target_show.add_argument("--format", choices=("text", "json"), default="text")
    target_show.set_defaults(func=cmd_target_show)
    upsert = target_subparsers.add_parser("upsert", help="create or update a target profile")
    upsert.add_argument("--name", required=True)
    upsert.add_argument("--profile", choices=("generic-linux", "rknn-host", "rk3588-board"))
    upsert.add_argument("--transport", choices=("local", "wsl", "ssh"))
    upsert.add_argument("--wsl-distro")
    upsert.add_argument("--host")
    upsert.add_argument("--user")
    upsert.add_argument("--port", type=int)
    upsert.add_argument("--identity-file")
    upsert.add_argument("--python")
    upsert.add_argument("--conda-path")
    upsert.add_argument("--conda-env")
    upsert.add_argument("--require-python")
    upsert.add_argument("--require-rknn-toolkit")
    upsert.add_argument("--require-rknn-runtime")
    upsert.add_argument("--plugin", action="append", default=None)
    upsert.add_argument("--note", action="append", default=None)
    upsert.add_argument("--project-root")
    upsert.add_argument("--global", dest="global_config", action="store_true")
    upsert.add_argument("--format", choices=("text", "json"), default="text")
    upsert.set_defaults(func=cmd_target_upsert)
    run = target_subparsers.add_parser("run", help="run a declared plugin action on a target")
    run.add_argument("--name", required=True)
    run.add_argument("--plugin", default="tensorfence.core")
    run.add_argument("--action", default="doctor")
    run.add_argument("--timeout", type=int, default=30)
    run.add_argument("--allow-side-effects", action="store_true")
    run.add_argument("--project-root")
    run.add_argument("--format", choices=("text", "json"), default="text")
    run.set_defaults(func=cmd_target_run)
