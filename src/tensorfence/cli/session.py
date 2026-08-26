from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = ("contract", "model", "image", "fp16_artifact", "int8_artifact", "framework_artifact", "report")


def _load(path: Path) -> dict:
    if not path.exists():
        return {field: "" for field in FIELDS}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid session file: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("session file must contain a JSON object")
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise ValueError(f"unknown session fields: {', '.join(unknown)}")
    return {field: str(data.get(field, "")) for field in FIELDS}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser(subparsers) -> None:
    parser = subparsers.add_parser("session", help="manage an explicit diagnostic session JSON file")
    commands = parser.add_subparsers(dest="session_command", required=True)
    for name in ("init", "show", "clear"):
        p = commands.add_parser(name)
        p.add_argument("--file", required=True, type=Path)
        p.set_defaults(func=cmd_session)
    p = commands.add_parser("set")
    p.add_argument("--file", required=True, type=Path)
    for field in FIELDS:
        p.add_argument(f"--{field.replace('_', '-')}", type=Path)
    p.set_defaults(func=cmd_session)


def cmd_session(args: argparse.Namespace) -> int:
    try:
        data = _load(args.file)
        if args.session_command == "init":
            if args.file.exists():
                print(f"ERROR: file already exists: {args.file}")
                return 2
            _save(args.file, data)
            print(f"created session: {args.file}")
        elif args.session_command == "clear":
            _save(args.file, {field: "" for field in FIELDS})
            print(f"cleared session: {args.file}")
        elif args.session_command == "set":
            for field in FIELDS:
                value = getattr(args, field)
                if value is not None:
                    data[field] = str(value.expanduser().resolve())
            _save(args.file, data)
            print(f"updated session: {args.file}")
        else:
            print(json.dumps({"file": str(args.file.resolve()), **data}, ensure_ascii=False, indent=2))
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0
