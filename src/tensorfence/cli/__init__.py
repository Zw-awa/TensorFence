from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path
from importlib.util import find_spec

from .. import __version__
from ..core.contracts import ContractError, load_contract
from ..core.report import render_validation_report
from ..core.templates import SAMPLE_CONTRACT_YAML
from ..core.validation import has_errors, validate_contract
from .compare_stages import build_parser as build_compare_stages_parser
from .draft_contract import build_parser as build_draft_contract_parser
from .dump_tensors import build_parser as build_dump_tensors_parser
from .inspect_image import build_parser as build_inspect_image_parser
from .probe_model import build_parser as build_probe_model_parser
from .validate_capture import build_parser as build_validate_capture_parser
from .session import build_parser as build_session_parser
from .diagnose import build_parser as build_diagnose_parser
from .rknn_run import build_parser as build_rknn_run_parser
from .environment import build_parser as build_environment_parser


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
        f"onnx: {_module_status('onnx')}",
        f"onnxruntime: {_module_status('onnxruntime')}",
        f"jinja2: {_module_status('jinja2')}",
        "",
        "Available commands: doctor, check-contract, init, inspect-image, probe-model, draft-contract, "
        "dump-tensors, validate-capture, compare-stages, session, diagnose, rknn-run, plugins, environment, target.",
        "MVP status: ONNX direct execution, artifact comparison, and WSL RKNN simulator execution are ready; "
        "direct framework execution is not implemented yet; use --framework-out with a framework-stage .npz artifact.",
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
    parser = argparse.ArgumentParser(prog="tensorfence", description="CLI-first diagnostics for TensorFence")
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

    build_inspect_image_parser(subparsers)
    build_probe_model_parser(subparsers)
    build_draft_contract_parser(subparsers)
    build_dump_tensors_parser(subparsers)
    build_validate_capture_parser(subparsers)
    build_compare_stages_parser(subparsers)
    build_session_parser(subparsers)
    build_diagnose_parser(subparsers)
    build_rknn_run_parser(subparsers)
    build_environment_parser(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
