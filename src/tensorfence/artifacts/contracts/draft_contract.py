from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


DRAFT_REPORT_SCHEMA_VERSION = "tensorfence.draft-report/v1"


@dataclass(frozen=True)
class DraftFieldDecision:
    path: str
    value: object
    source: Literal["facts", "rules", "default", "override"]
    confidence: Literal["high", "medium", "low"]
    note: str | None = None


@dataclass(frozen=True)
class DraftIssue:
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    path: str | None = None


@dataclass(frozen=True)
class DraftConfirmation:
    path: str
    reason: str
    suggested_action: str | None = None


@dataclass(frozen=True)
class DraftContractReport:
    model_path: str | None
    facts_path: str | None
    rules_path: str
    task: str
    family: str
    generated_contract_path: str
    decisions: list[DraftFieldDecision]
    issues: list[DraftIssue]
    needs_confirmation: list[DraftConfirmation]
    schema_version: str = DRAFT_REPORT_SCHEMA_VERSION


def draft_report_to_dict(report: DraftContractReport) -> dict:
    return asdict(report)


def write_draft_report_json(report: DraftContractReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(draft_report_to_dict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_draft_report_markdown(report: DraftContractReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Draft Contract Report",
        "",
        f"- Model: `{report.model_path or '<from facts only>'}`",
        f"- Facts: `{report.facts_path or '<in-memory>'}`",
        f"- Rules: `{report.rules_path}`",
        f"- Task: `{report.task}`",
        f"- Family: `{report.family}`",
        f"- Contract: `{report.generated_contract_path}`",
        "",
        "## Decisions",
        "",
    ]
    for decision in report.decisions:
        note = f" ({decision.note})" if decision.note else ""
        lines.append(
            f"- `{decision.path}` = `{decision.value}` from `{decision.source}` [{decision.confidence}]{note}"
        )

    lines.extend(["", "## Needs Confirmation", ""])
    for item in report.needs_confirmation:
        action = f" Suggested action: {item.suggested_action}" if item.suggested_action else ""
        lines.append(f"- `{item.path}`: {item.reason}{action}")

    if report.issues:
        lines.extend(["", "## Issues", ""])
        for issue in report.issues:
            suffix = f" ({issue.path})" if issue.path else ""
            lines.append(f"- [{issue.severity}] `{issue.code}`: {issue.message}{suffix}")

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
