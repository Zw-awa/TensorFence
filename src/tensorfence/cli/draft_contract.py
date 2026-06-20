from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..artifacts.contracts.draft_contract import write_draft_report_json, write_draft_report_markdown
from ..artifacts.facts.model_facts import load_model_facts_json
from ..core.contracts import write_contract
from ..probe.base import ProbeError
from ..probe.onnx_probe import collect_onnx_model_facts
from ..rules.engine import DraftContractError, build_draft_contract_bundle
from ..rules.schema import RuleError, load_rules

def build_parser(subparsers) -> None:
    parser = subparsers.add_parser(
        "draft-contract",
        help="generate a draft contract from model facts and user-defined rules",
    )
    parser.add_argument("--facts", help="path to a model facts JSON file")
    parser.add_argument("--model", help="path to the model file to probe directly")
    parser.add_argument("--rules", required=True, help="path to the rule YAML file")
    parser.add_argument("--out", required=True, help="path to the draft contract output")
    parser.add_argument(
        "--report-format",
        choices=["json", "md", "both"],
        default="both",
        help="artifact format preference for the draft report",
    )
    parser.add_argument("--report-out", help="output directory for report artifacts; defaults to the contract output directory")
    parser.add_argument(
        "--task",
        choices=["auto", "detection", "classification", "segmentation", "pose", "ocr"],
        default="auto",
        help="override or constrain task inference",
    )
    parser.add_argument(
        "--family",
        choices=["auto", "yolo", "ppyoloe"],
        default="auto",
        help="override or constrain model family inference",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing output files")
    parser.set_defaults(func=cmd_draft_contract)


def cmd_draft_contract(args: argparse.Namespace) -> int:
    if not args.facts and not args.model:
        print("ERROR: provide --facts or --model", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    report_dir = Path(args.report_out) if args.report_out else out_path.parent
    report_json = report_dir / "draft_report.json"
    report_md = report_dir / "draft_report.md"

    if not args.force:
        for path in [out_path, report_json if args.report_format in {"json", "both"} else None, report_md if args.report_format in {"md", "both"} else None]:
            if path is not None and path.exists():
                print(f"ERROR: file already exists: {path}", file=sys.stderr)
                return 2

    try:
        rules = load_rules(args.rules)
        facts_path = args.facts
        if args.facts and args.model:
            print("WARNING: both --facts and --model were provided; using --facts", file=sys.stderr)

        if args.facts:
            model_facts = load_model_facts_json(args.facts)
        else:
            model_path = args.model
            model_type = "onnx" if str(model_path).lower().endswith(".onnx") else "unsupported"
            if model_type != "onnx":
                raise DraftContractError(f"draft-contract currently only supports ONNX model probing, got model={model_path}")
            model_facts = collect_onnx_model_facts(model_path)
            facts_path = None

        bundle = build_draft_contract_bundle(
            model_facts=model_facts,
            rules=rules,
            rules_path=args.rules,
            generated_contract_path=out_path,
            task_override=args.task,
            family_override=args.family,
            facts_path=facts_path,
        )
    except (RuleError, DraftContractError, ProbeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    contract_path = write_contract(out_path, bundle.contract)
    print(f"wrote draft contract to {contract_path}")

    if args.report_format in {"json", "both"}:
        json_path = write_draft_report_json(bundle.report, report_json)
        print(f"wrote draft report to {json_path}")
    if args.report_format in {"md", "both"}:
        md_path = write_draft_report_markdown(bundle.report, report_md)
        print(f"wrote draft report to {md_path}")
    return 0
