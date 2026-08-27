from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


def _windows_to_wsl(path: str) -> str:
    match = re.fullmatch(r"([A-Za-z]):[\\/](.*)", path)
    if not match:
        return path.replace("\\", "/")
    tail = match.group(2).replace("\\", "/")
    return f"/mnt/{match.group(1).lower()}/{tail}"


def build_parser(subparsers) -> None:
    bridge = subparsers.add_parser("rknn-run", help="run RKNN inference in a configured WSL Conda environment")
    bridge.add_argument("--contract", required=True)
    bridge.add_argument("--model", required=True, help=".rknn model")
    bridge.add_argument("--image", required=True)
    bridge.add_argument("--out", required=True, help="canonical .npz output artifact")
    bridge.add_argument("--wsl-distro")
    bridge.add_argument("--wsl-conda", help="optional Conda executable inside WSL")
    bridge.add_argument("--wsl-env", help="optional Conda environment name")
    bridge.add_argument("--wsl-python", help="optional Python executable inside WSL")
    bridge.add_argument("--target", help="optional RKNN target platform or device id")
    bridge.add_argument("--device-id", help="optional connected device id")
    bridge.add_argument("--environment-target", help="named project target profile; fills WSL settings not explicitly passed")
    bridge.add_argument("--project-root", help="project root containing .tensorfence/targets.yaml")
    bridge.set_defaults(func=cmd_rknn_run)

    execute = subparsers.add_parser("_rknn-exec", help=argparse.SUPPRESS)
    execute.add_argument("--contract", required=True)
    execute.add_argument("--model", required=True)
    execute.add_argument("--image", required=True)
    execute.add_argument("--out", required=True)
    execute.add_argument("--target")
    execute.add_argument("--device-id")
    execute.set_defaults(func=cmd_rknn_exec)


def cmd_rknn_run(args: argparse.Namespace) -> int:
    if args.environment_target:
        from ..environment import load_targets

        target = load_targets(Path(args.project_root).resolve() if args.project_root else Path.cwd()).get(args.environment_target)
        if target is None:
            print(f"ERROR: target not found: {args.environment_target}", file=sys.stderr)
            return 2
        if target.transport != "wsl":
            print(f"ERROR: rknn-run compatibility bridge requires a WSL target, got {target.transport}", file=sys.stderr)
            return 2
        connection = target.connection
        args.wsl_distro = args.wsl_distro or connection.wsl_distro
        args.wsl_conda = args.wsl_conda or connection.conda_path
        args.wsl_env = args.wsl_env or connection.conda_env
        args.wsl_python = args.wsl_python or connection.python
    args.wsl_distro = args.wsl_distro or "Ubuntu"
    repo_root = Path(__file__).resolve().parents[3]
    source_root = _windows_to_wsl(str(repo_root / "src"))
    if args.wsl_conda and args.wsl_env:
        runner = [args.wsl_conda, "run", "-n", args.wsl_env, "env", f"PYTHONPATH={source_root}", args.wsl_python or "python"]
    else:
        runner = ["env", f"PYTHONPATH={source_root}", args.wsl_python or "python3"]
    command = runner + ["-m", "tensorfence", "_rknn-exec"]
    for key in ("contract", "model", "image", "out"):
        command.extend((f"--{key}", _windows_to_wsl(getattr(args, key))))
    for key in ("target", "device_id"):
        value = getattr(args, key)
        if value:
            command.extend((f"--{key.replace('_', '-')}", value))
    # WSL does not reliably preserve positional parameters passed after `bash -lc`
    # from Windows. Quote the complete Linux command as one script instead.
    script = "exec " + shlex.join(command)
    result = subprocess.run(["wsl", "-d", args.wsl_distro, "bash", "-lc", script], text=True)
    return result.returncode


def cmd_rknn_exec(args: argparse.Namespace) -> int:
    from ..adapters.rknn import RknnAdapterError, run_rknn_model
    from ..artifacts import write_tensor_artifact
    from ..core.contracts import ContractError, load_contract
    from ..core.preprocess import PreprocessError, prepare_image

    try:
        contract = load_contract(args.contract)
        prepared = prepare_image(contract, args.image)
        outputs, warnings = run_rknn_model(args.model, input_tensor=prepared.input_tensor, expected_names=[item.name for item in contract.outputs], target=args.target, device_id=args.device_id)
        artifact = write_tensor_artifact(args.out, outputs, stage="rknn", source="rknn-toolkit2 simulator" if not args.device_id else "rknn runtime device", provenance={"model_path": str(Path(args.model).resolve()), "input_image": str(Path(args.image).resolve()), "contract": str(Path(args.contract).resolve()), "warnings": warnings})
        print(f"wrote RKNN artifact: {artifact}")
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        return 0
    except (ContractError, PreprocessError, RknnAdapterError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
