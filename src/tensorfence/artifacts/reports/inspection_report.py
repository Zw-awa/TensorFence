from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class InspectionCheck:
    name: str
    status: Literal["pass", "warning", "fail"]
    message: str


@dataclass(frozen=True)
class InspectionArtifactPaths:
    report_json: str
    tensor_summary_json: str
    preview_image: str | None = None
    tensor_dump: str | None = None


@dataclass(frozen=True)
class InspectionReport:
    contract_name: str
    image_path: str
    source_framework: str
    target_runtime: str
    task: str
    source_image: dict
    preprocess: dict
    tensor_summary: dict
    checks: list[InspectionCheck]
    artifacts: InspectionArtifactPaths


def _to_dict(report: InspectionReport) -> dict:
    data = asdict(report)
    data["checks"] = [asdict(check) for check in report.checks]
    data["artifacts"] = asdict(report.artifacts)
    return data


def write_report_json(report: InspectionReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_to_dict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_report_markdown(report: InspectionReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Inspection Report: {report.contract_name}",
        "",
        f"- Image: `{report.image_path}`",
        f"- Source: `{report.source_framework}` -> `{report.target_runtime}`",
        f"- Task: `{report.task}`",
        f"- Source image: `{report.source_image['width']}x{report.source_image['height']}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- [{check.status}] `{check.name}`: {check.message}")

    lines.extend(
        [
            "",
            "## Tensor Summary",
            "",
            f"- Shape: `{report.tensor_summary['shape']}`",
            f"- Dtype: `{report.tensor_summary['dtype']}`",
            f"- Min: `{report.tensor_summary['minimum']}`",
            f"- Max: `{report.tensor_summary['maximum']}`",
            f"- Mean: `{report.tensor_summary['mean']}`",
            f"- Std: `{report.tensor_summary['std']}`",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def write_report_html(report: InspectionReport, path: str | Path) -> Path:
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
    template = environment.get_template("inspection_report.html.j2")
    content = template.render(report=_to_dict(report))
    target.write_text(content, encoding="utf-8")
    return target
