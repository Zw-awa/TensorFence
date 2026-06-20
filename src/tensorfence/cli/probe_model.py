from __future__ import annotations

import argparse
import sys

from ..probe.base import ProbeError
from ..probe.onnx_probe import probe_onnx_model


def build_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "probe-model",
        help="extract graph facts, inputs, outputs, and operator summaries from a model file",
    )
    parser.add_argument("--model", required=True, help="path to the model file")
    parser.add_argument(
        "--model-type",
        choices=["auto", "onnx", "pt", "pdmodel", "rknn"],
        default="auto",
        help="force the model type instead of auto-detecting",
    )
    parser.add_argument("--out", required=True, help="output directory for probe artifacts")
    parser.add_argument(
        "--format",
        choices=["json", "md", "both"],
        default="both",
        help="artifact format preference",
    )
    parser.set_defaults(func=cmd_probe_model)


def cmd_probe_model(args: argparse.Namespace) -> int:
    try:
        model_path = args.model
        model_type = args.model_type
        if model_type == "auto":
            model_type = "onnx" if str(model_path).lower().endswith(".onnx") else "unsupported"
        if model_type != "onnx":
            raise ProbeError(f"probe-model currently only supports ONNX files, got model_type={model_type}")

        artifacts = probe_onnx_model(model_path=model_path, out_dir=args.out, output_format=args.format)
    except ProbeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"wrote model facts to {artifacts.model_facts_json}")
    print(f"wrote ops summary to {artifacts.ops_summary_json}")
    if artifacts.graph_summary_md is not None:
        print(f"wrote graph summary to {artifacts.graph_summary_md}")
    return 0
