from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..core.stage_compare import StageCompareError, compare_stages
from .session import _load


def build_parser(subparsers) -> None:
    parser = subparsers.add_parser("diagnose", help="run the complete artifact-first diagnostic workflow")
    parser.add_argument("--session", type=Path)
    parser.add_argument("--contract")
    parser.add_argument("--image")
    parser.add_argument("--onnx")
    parser.add_argument("--fp16")
    parser.add_argument("--int8")
    parser.add_argument("--framework")
    parser.add_argument("--out", required=True)
    parser.add_argument("--report-format", choices=("json", "md", "html"), default="json")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.set_defaults(func=cmd_diagnose)


def cmd_diagnose(args: argparse.Namespace) -> int:
    values = {key: getattr(args, key) for key in ("contract", "image", "onnx", "fp16", "int8", "framework")}
    try:
        if args.session:
            saved = _load(args.session)
            values = {key: values[key] or saved.get({"fp16": "fp16_artifact", "int8": "int8_artifact", "framework": "framework_artifact"}.get(key, key), "") for key in values}
        missing = [key for key in ("contract", "image") if not values[key]]
        if not values["onnx"] and not values["fp16"] and not values["int8"]:
            missing.append("onnx or artifacts")
        if missing:
            raise ValueError("missing required inputs: " + ", ".join(missing))
        artifacts = compare_stages(contract_path=values["contract"], image_path=values["image"], out_dir=args.out, onnx_model=values["onnx"] or None, onnx_out=None, rknn_out=None, fp16_out=values["fp16"] or None, int8_out=values["int8"] or None, framework_out=values["framework"] or None, report_format=args.report_format)
        result = {"status": "ok", "report": str(artifacts.report_json), "out": str(Path(args.out).resolve())}
        print(json.dumps(result, ensure_ascii=False) if args.format == "json" else f"diagnosis complete: {artifacts.report_json}")
        return 0
    except (ValueError, StageCompareError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
