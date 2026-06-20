from __future__ import annotations

import argparse
import sys

from ..core.image_inspection import ImageInspectionError, inspect_image


def build_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "inspect-image",
        help="inspect one image through the declared preprocessing path",
    )
    parser.add_argument("--contract", required=True, help="path to the model contract YAML file")
    parser.add_argument("--image", required=True, help="path to the source image")
    parser.add_argument("--out", required=True, help="output directory for inspection artifacts")
    parser.add_argument(
        "--report-format",
        choices=["json", "md", "html"],
        default="json",
        help="report format to generate",
    )
    parser.add_argument("--save-image", action="store_true", help="save the preprocessed image artifact")
    parser.add_argument("--save-tensor", action="store_true", help="save tensor summaries or dumps")
    parser.set_defaults(func=cmd_inspect_image)


def cmd_inspect_image(args: argparse.Namespace) -> int:
    try:
        artifacts = inspect_image(
            contract_path=args.contract,
            image_path=args.image,
            out_dir=args.out,
            report_format=args.report_format,
            save_image=args.save_image,
            save_tensor=args.save_tensor,
        )
    except ImageInspectionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"wrote inspection report to {artifacts.report}")
    print(f"wrote tensor summary to {artifacts.tensor_summary}")
    if artifacts.preview_image is not None:
        print(f"wrote preview image to {artifacts.preview_image}")
    if artifacts.tensor_dump is not None:
        print(f"wrote tensor dump to {artifacts.tensor_dump}")
    if artifacts.report_markdown is not None:
        print(f"wrote markdown report to {artifacts.report_markdown}")
    if artifacts.report_html is not None:
        print(f"wrote html report to {artifacts.report_html}")
    return 0
