from __future__ import annotations

from collections.abc import Iterable

from .contracts import ModelContract
from .diff import TensorDiff, TensorSummary
from .validation import ContractIssue


def render_validation_report(contract: ModelContract, issues: Iterable[ContractIssue]) -> str:
    issue_list = list(issues)
    lines = [
        f"Contract: {contract.name}",
        f"Task: {contract.task}",
        f"Source: {contract.source_framework} -> {contract.target_runtime}",
        f"Input: {contract.input.name} {contract.input.shape} {contract.input.dtype}",
        f"Outputs: {len(contract.outputs)}",
        "",
    ]

    if not issue_list:
        lines.append("Validation: OK")
        return "\n".join(lines)

    lines.append("Validation issues:")
    for issue in issue_list:
        lines.append(f"- [{issue.severity}] {issue.code} ({issue.field}): {issue.message}")
    return "\n".join(lines)


def render_summary(name: str, summary: TensorSummary) -> str:
    return (
        f"{name}: shape={summary.shape} dtype={summary.dtype} "
        f"min={summary.minimum} max={summary.maximum} mean={summary.mean} std={summary.std}"
    )


def render_diff(name: str, diff: TensorDiff) -> str:
    return (
        f"{name}: shape_match={diff.shape_match} dtype_match={diff.dtype_match} "
        f"max_abs={diff.max_abs_error} mean_abs={diff.mean_abs_error} "
        f"rms={diff.rms_error} cosine={diff.cosine_similarity}"
    )

