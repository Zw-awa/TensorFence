from __future__ import annotations

import argparse
import sys

from ..core.stage_compare import ComparisonThresholds, StageCompareError, compare_stages


def build_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "compare-stages",
        help="compare framework, ONNX, and RKNN stage outputs and reports",
    )
    parser.add_argument("--contract", required=True, help="path to the model contract YAML file")
    parser.add_argument("--image", required=True, help="path to the source image")
    framework_source = parser.add_mutually_exclusive_group()
    framework_source.add_argument("--framework-out", help="path to precomputed framework outputs")
    framework_source.add_argument("--framework-runner", help="framework runner identifier for direct execution")
    onnx_source = parser.add_mutually_exclusive_group()
    onnx_source.add_argument("--onnx", help="path to the ONNX model")
    onnx_source.add_argument("--onnx-out", help="path to precomputed ONNX outputs (.npz)")
    rknn_source = parser.add_mutually_exclusive_group()
    rknn_source.add_argument("--rknn", help="path to the RKNN model")
    rknn_source.add_argument("--rknn-out", help="path to precomputed RKNN outputs (.npz)")
    parser.add_argument(
        "--map-by-order",
        action="store_true",
        help="explicitly map outputs by order when names differ (unsafe; recorded as a warning)",
    )
    parser.add_argument("--out", required=True, help="output directory for comparison artifacts")
    parser.add_argument(
        "--report-format",
        choices=["json", "md", "html"],
        default="json",
        help="report format to generate",
    )
    defaults = ComparisonThresholds()
    parser.add_argument(
        "--max-abs-error",
        type=float,
        default=defaults.max_abs_error,
        help="maximum aligned absolute error (default: %(default)s)",
    )
    parser.add_argument(
        "--min-cosine-similarity",
        type=float,
        default=defaults.min_cosine_similarity,
        help="minimum aligned cosine similarity (default: %(default)s)",
    )
    parser.add_argument(
        "--max-mean-relative-error",
        type=float,
        default=defaults.max_mean_relative_error,
        help="maximum aligned mean relative error (default: %(default)s)",
    )
    parser.add_argument(
        "--relative-error-epsilon",
        type=float,
        default=defaults.relative_error_epsilon,
        help="reference denominator floor for relative error (default: %(default)s)",
    )
    parser.add_argument(
        "--small-value-threshold",
        type=float,
        default=defaults.small_value_threshold,
        help="explicit small-value ceiling; default uses the adaptive thresholds below",
    )
    parser.add_argument(
        "--small-value-relative-threshold",
        type=float,
        default=defaults.small_value_relative_threshold,
        help="adaptive small-value ceiling relative to reference max (default: %(default)s)",
    )
    parser.add_argument(
        "--small-value-min-threshold",
        type=float,
        default=defaults.small_value_min_threshold,
        help="adaptive small-value ceiling floor (default: %(default)s)",
    )
    parser.add_argument(
        "--small-value-max-threshold",
        type=float,
        default=defaults.small_value_max_threshold,
        help="adaptive small-value ceiling cap (default: %(default)s)",
    )
    parser.add_argument(
        "--small-value-min-count",
        type=int,
        default=defaults.small_value_min_count,
        help="minimum affected element count for collapse diagnosis (default: %(default)s)",
    )
    parser.add_argument(
        "--small-value-min-fraction",
        type=float,
        default=defaults.small_value_min_fraction,
        help="minimum affected tensor fraction for collapse diagnosis (default: %(default)s)",
    )
    parser.add_argument(
        "--small-value-zero-fraction",
        type=float,
        default=defaults.small_value_zero_fraction,
        help="minimum affected values becoming zero (default: %(default)s)",
    )
    parser.add_argument(
        "--clipping-ratio-threshold",
        type=float,
        default=defaults.clipping_ratio_threshold,
        help="minimum candidate endpoint/extreme ratio (default: %(default)s)",
    )
    parser.add_argument(
        "--clipping-ratio-increase",
        type=float,
        default=defaults.clipping_ratio_increase,
        help="minimum endpoint/extreme increase over reference (default: %(default)s)",
    )
    parser.add_argument(
        "--clipping-min-count",
        type=int,
        default=defaults.clipping_min_count,
        help="minimum tensor size for clipping diagnosis (default: %(default)s)",
    )
    parser.set_defaults(func=cmd_compare_stages)


def cmd_compare_stages(args: argparse.Namespace) -> int:
    thresholds = ComparisonThresholds(
        max_abs_error=args.max_abs_error,
        min_cosine_similarity=args.min_cosine_similarity,
        max_mean_relative_error=args.max_mean_relative_error,
        relative_error_epsilon=args.relative_error_epsilon,
        small_value_threshold=args.small_value_threshold,
        small_value_relative_threshold=args.small_value_relative_threshold,
        small_value_min_threshold=args.small_value_min_threshold,
        small_value_max_threshold=args.small_value_max_threshold,
        small_value_min_count=args.small_value_min_count,
        small_value_min_fraction=args.small_value_min_fraction,
        small_value_zero_fraction=args.small_value_zero_fraction,
        clipping_ratio_threshold=args.clipping_ratio_threshold,
        clipping_ratio_increase=args.clipping_ratio_increase,
        clipping_min_count=args.clipping_min_count,
    )
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
            map_by_order=args.map_by_order,
            thresholds=thresholds,
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
