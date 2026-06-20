from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class StageTensorSummaryEntry:
    name: str
    shape: list[int]
    dtype: str
    minimum: float | None
    maximum: float | None
    mean: float | None
    std: float | None


@dataclass(frozen=True)
class StageRecord:
    stage: Literal["framework", "onnx", "rknn"]
    source_kind: str
    source_path: str | None
    available: bool
    warnings: list[str]
    outputs: list[StageTensorSummaryEntry]


@dataclass(frozen=True)
class StagePairDiffEntry:
    left_stage: str
    right_stage: str
    tensor_name: str
    status: Literal["aligned", "drift", "shape_mismatch"]
    shape_match: bool
    dtype_match: bool
    max_abs_error: float | None
    mean_abs_error: float | None
    rms_error: float | None
    cosine_similarity: float | None
    reasons: list[str]


@dataclass(frozen=True)
class StageFinalSummary:
    available_stages: list[str]
    compared_pairs: list[str]
    drift_detected: bool
    first_drift_stage: str | None
    first_drift_pair: str | None
    warning_count: int


@dataclass(frozen=True)
class StageCompareReport:
    contract_name: str
    image_path: str
    input_tensor_shape: list[int]
    input_tensor_dtype: str
    stages: list[StageRecord]
    pair_diffs: list[StagePairDiffEntry]
    final_summary: StageFinalSummary
    warnings: list[str]


def _to_dict(report: StageCompareReport) -> dict:
    return asdict(report)


def write_stage_report_json(report: StageCompareReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_to_dict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_stage_report_markdown(report: StageCompareReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Stage Compare Report: {report.contract_name}",
        "",
        f"- Image: `{report.image_path}`",
        f"- Input tensor: `{report.input_tensor_shape}` `{report.input_tensor_dtype}`",
        "",
        "## Stages",
        "",
    ]
    for stage in report.stages:
        lines.append(
            f"- `{stage.stage}` [{('available' if stage.available else 'skipped')}] via `{stage.source_kind}` path=`{stage.source_path}`"
        )
        for output in stage.outputs:
            lines.append(
                f"  - `{output.name}` shape=`{output.shape}` dtype=`{output.dtype}` min=`{output.minimum}` max=`{output.maximum}`"
            )
        for warning in stage.warnings:
            lines.append(f"  - warning: {warning}")

    lines.extend(["", "## Pair Diffs", ""])
    for diff in report.pair_diffs:
        lines.append(
            f"- `{diff.left_stage}->{diff.right_stage}` `{diff.tensor_name}` [{diff.status}] "
            f"max_abs=`{diff.max_abs_error}` mean_abs=`{diff.mean_abs_error}` rms=`{diff.rms_error}` cosine=`{diff.cosine_similarity}`"
        )
        for reason in diff.reasons:
            lines.append(f"  - {reason}")

    lines.extend(
        [
            "",
            "## Final Summary",
            "",
            f"- Available stages: `{report.final_summary.available_stages}`",
            f"- Compared pairs: `{report.final_summary.compared_pairs}`",
            f"- Drift detected: `{report.final_summary.drift_detected}`",
            f"- First drift stage: `{report.final_summary.first_drift_stage}`",
            f"- First drift pair: `{report.final_summary.first_drift_pair}`",
        ]
    )

    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in report.warnings:
            lines.append(f"- {warning}")

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def write_stage_report_html(report: StageCompareReport, path: str | Path) -> Path:
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ModuleNotFoundError as exc:
        raise RuntimeError("jinja2 is required for HTML report generation") from exc

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    template_dir = Path(__file__).with_name("templates")
    environment = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )
    template = environment.get_template("stage_report.html.j2")
    content = template.render(report=_to_dict(report))
    target.write_text(content, encoding="utf-8")
    return target


def write_tensor_diffs_json(pair_diffs: list[StagePairDiffEntry], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([asdict(item) for item in pair_diffs], indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_final_summary_json(summary: StageFinalSummary, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    return target
