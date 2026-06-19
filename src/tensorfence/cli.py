from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path
from importlib.util import find_spec

from . import __version__
from .core.contracts import ContractError, load_contract
from .core.report import render_validation_report
from .core.templates import SAMPLE_CONTRACT_YAML
from .core.validation import has_errors, validate_contract


def _module_status(module_name: str) -> str:
    return "ok" if find_spec(module_name) is not None else "missing"


def cmd_doctor(_args: argparse.Namespace) -> int:
    lines = [
        f"TensorFence {__version__}",
        f"Python: {platform.python_version()}",
        f"Executable: {sys.executable}",
        f"Conda prefix: {os.environ.get('CONDA_PREFIX', '<not set>')}",
        f"numpy: {_module_status('numpy')}",
        f"pydantic: {_module_status('pydantic')}",
        f"yaml: {_module_status('yaml')}",
        "",
        "Foundation status: adapters and stage runners are not wired yet.",
    ]
    print("\n".join(lines))
    return 0


def cmd_check_contract(args: argparse.Namespace) -> int:
    try:
        contract = load_contract(args.path)
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    issues = validate_contract(contract)
    print(render_validation_report(contract, issues))
    return 1 if has_errors(issues) else 0

def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if target.exists() and not args.force:
        print(f"ERROR: file already exists: {target}", file=sys.stderr)
        return 2

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(SAMPLE_CONTRACT_YAML, encoding="utf-8")
    print(f"wrote sample contract to {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tensorfence", description="Foundation CLI for TensorFence")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="print environment and package status")
    doctor.set_defaults(func=cmd_doctor)

    check_contract = subparsers.add_parser("check-contract", help="validate a model contract YAML file")
    check_contract.add_argument("path", type=Path)
    check_contract.set_defaults(func=cmd_check_contract)

    init = subparsers.add_parser("init", help="write a sample contract YAML file")
    init.add_argument("path", type=Path)
    init.add_argument("--force", action="store_true", help="overwrite existing file")
    init.set_defaults(func=cmd_init)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
