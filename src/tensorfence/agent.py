"""Agent-facing bridge that consumes the same structured CLI protocol as Qt."""

from __future__ import annotations

import contextlib
import io
import json
from typing import Any, Sequence

from .cli import main


def invoke(argv: Sequence[str]) -> dict[str, Any]:
    args = list(argv)
    if "--format" in args:
        index = args.index("--format")
        if index + 1 < len(args):
            args[index + 1] = "json"
    else:
        args.extend(["--format", "json"])
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(args)
    raw = output.getvalue().strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"status": "blocked", "error": {"code": "invalid_cli_envelope", "message": raw}}
    if not isinstance(payload, dict):
        payload = {"status": "blocked", "error": {"code": "invalid_cli_envelope", "message": "CLI result must be an object"}}
    payload.setdefault("facts", [])
    payload.setdefault("artifacts", [])
    payload.setdefault("recommendations", [])
    payload.setdefault("provenance", {})
    payload.setdefault("exit_code", code)
    return payload


__all__ = ["invoke"]
