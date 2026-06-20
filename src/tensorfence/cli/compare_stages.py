from __future__ import annotations

import argparse
import sys

from ..core.stage_compare import StageCompareError, compare_stages

def build_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "compare-stages",
        help="compare framework, ONNX, and RKNN stage outputs and reports",
    )
    parser.add_argument("--contract", required=True, help="path to the model contract YAML file")
    parser.add_argument("--image", required=True, help="path to the source image")
    parser.add_argument("--framework-out", help="path to precomputed framework outputs")
    parser.add_argument("--framework-runner", help="framework runner identifier for direct execution")
    parser.add_argument("--onnx", help="path to the ONNX model")
    parser.add_argument("--onnx-out", help="path to precomputed ONNX outputs (.npz)")
    parser.add_argument("--rknn", help="path to the RKNN model")
    parser.add_argument("--rknn-out", help="path to precomputed RKNN outputs (.npz)")
    parser.add_argument("--out", required=True, help="output directory for comparison artifacts")
    parser.add_argument(
        "--report-format",
        choices=["json", "md", "html"],
        default="json",
        help="report format to generate",
    )
    parser.set_defaults(func=cmd_compare_stages)


def cmd_compare_stages(args: argparse.Namespace) -> int:
    try:
        artifacts = compare_stages(
            contract_path=args.contract,
            image_path=args.image,
            out_dir=args.out,
            framework_out=args.framework_out,
            framework_runner=args.framework_runner,
            onnx_model=args.onnx,
            onnx_out=args.onnx_out,
            rknn_model=args.rknn,
            rknn_out=args.rknn_out,
            report_format=args.report_format,
        )
    except StageCompareError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"wrote stage compare report to {artifacts.report_json}")
    print(f"wrote tensor diffs to {artifacts.tensor_diffs_json}")
    print(f"wrote final summary to {artifacts.final_summary_json}")
    if artifacts.report_markdown is not None:
        print(f"wrote markdown report to {artifacts.report_markdown}")
    if artifacts.report_html is not None:
        print(f"wrote html report to {artifacts.report_html}")
    return 0
