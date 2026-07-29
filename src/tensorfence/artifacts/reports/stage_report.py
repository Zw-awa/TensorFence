from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


STAGE_REPORT_SCHEMA_VERSION = "tensorfence.stage-report/v1"
STAGE_DIFF_SCHEMA_VERSION = "tensorfence.tensor-diff/v1"
STAGE_SUMMARY_SCHEMA_VERSION = "tensorfence.stage-summary/v1"


@dataclass(frozen=True)
class StageTensorSummaryEntry:
    name: str
    shape: list[int]
    dtype: str
    minimum: float | None
    maximum: float | None
    mean: float | None
    std: float | None
    zero_fraction: float | None
    finite_fraction: float | None
    nan_count: int
    positive_inf_count: int
    negative_inf_count: int
    saturation_fraction: float | None
    clipping_fraction: float | None
    quantization: dict[str, object] | None
    summary_domain: Literal["raw"]
    dequantized_minimum: float | None
    dequantized_maximum: float | None
    dequantized_zero_fraction: float | None


@dataclass(frozen=True)
class StageRecord:
    stage: Literal["framework", "onnx", "rknn"]
    source_kind: str
    source_path: str | None
    artifact_source: str | None
    provenance: dict[str, object]
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
    comparison_domain: Literal["raw", "dequantized"] = "raw"
    left_raw_dtype: str | None = None
    right_raw_dtype: str | None = None
    max_relative_error: float | None = None
    mean_relative_error: float | None = None
    left_zero_fraction: float | None = None
    right_zero_fraction: float | None = None
    left_nan_count: int = 0
    right_nan_count: int = 0
    left_inf_count: int = 0
    right_inf_count: int = 0
    finite_pair_fraction: float | None = None
    left_saturation_fraction: float | None = None
    right_saturation_fraction: float | None = None
    left_clipping_fraction: float | None = None
    right_clipping_fraction: float | None = None
    small_value_threshold: float | None = None
    small_value_count: int | None = None
    small_value_fraction: float | None = None
    small_value_zero_fraction: float | None = None
    quantization_step_min: float | None = None
    quantization_step_max: float | None = None
    under_resolution_count: int | None = None
    under_resolution_fraction: float | None = None
    under_resolution_zero_fraction: float | None = None
    schema_version: str = STAGE_DIFF_SCHEMA_VERSION


@dataclass(frozen=True)
class StageFinalSummary:
    available_stages: list[str]
    compared_pairs: list[str]
    drift_detected: bool
    first_drift_stage: str | None
    first_drift_pair: str | None
    warning_count: int
    schema_version: str = STAGE_SUMMARY_SCHEMA_VERSION


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
    comparison_thresholds: dict[str, float | int | None]
    schema_version: str = STAGE_REPORT_SCHEMA_VERSION


def _to_dict(report: StageCompareReport) -> dict:
    return asdict(report)


def write_stage_report_json(report: StageCompareReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_to_dict(report), indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
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
            f"- `{stage.stage}` [{('available' if stage.available else 'skipped')}] via `{stage.source_kind}` "
            f"path=`{stage.source_path}` artifact_source=`{stage.artifact_source}`"
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
            f"max_abs=`{diff.max_abs_error}` mean_abs=`{diff.mean_abs_error}` rms=`{diff.rms_error}` "
            f"cosine=`{diff.cosine_similarity}` mean_relative=`{diff.mean_relative_error}` "
            f"domain=`{diff.comparison_domain}` raw_dtypes=`{diff.left_raw_dtype}/{diff.right_raw_dtype}` "
            f"left_zero=`{diff.left_zero_fraction}` right_zero=`{diff.right_zero_fraction}` "
            f"small_zero=`{diff.small_value_zero_fraction}` "
            f"quant_step=`{diff.quantization_step_min}/{diff.quantization_step_max}` "
            f"under_resolution_zero=`{diff.under_resolution_zero_fraction}`"
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
    target.write_text(
        json.dumps([asdict(item) for item in pair_diffs], indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return target


def write_final_summary_json(summary: StageFinalSummary, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(summary), indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return target
