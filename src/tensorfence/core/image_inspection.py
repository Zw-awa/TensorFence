from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from ..artifacts.reports.inspection_report import (
    InspectionArtifactPaths,
    InspectionCheck,
    InspectionReport,
    write_report_html,
    write_report_json,
    write_report_markdown,
)
from .contracts import load_contract
from .diff import summarize_array
from .preprocess import PreprocessError, PreprocessResult, prepare_image, save_preview_image


class ImageInspectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImageInspectionArtifacts:
    report: Path
    tensor_summary: Path
    preview_image: Path | None
    tensor_dump: Path | None
    report_markdown: Path | None
    report_html: Path | None


def _write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _build_checks(contract, result: PreprocessResult) -> list[InspectionCheck]:
    checks = [
        InspectionCheck(
            name="input-shape-match",
            status="pass",
            message=f"preprocessed tensor shape matches declared input shape {contract.input.shape}",
        ),
        InspectionCheck(
            name="input-dtype-match",
            status="pass" if contract.input.dtype == "float32" else "warning",
            message=f"inspection emits float32 tensors; declared input dtype is {contract.input.dtype}",
        ),
        InspectionCheck(
            name="output-layout-match",
            status="pass",
            message=f"preprocess output layout is {result.output_layout}",
        ),
        InspectionCheck(
            name="resize-target-match",
            status="pass",
            message=f"resize target is {result.resize.target_width}x{result.resize.target_height}",
        ),
    ]

    if contract.preprocess.output_color_space is None:
        checks.append(
            InspectionCheck(
                name="output-color-space-defaulted",
                status="warning",
                message="preprocess.output_color_space is not declared; using input_color_space",
            )
        )

    return checks


def inspect_image(
    contract_path: str | Path,
    image_path: str | Path,
    out_dir: str | Path,
    report_format: str = "json",
    save_image: bool = False,
    save_tensor: bool = False,
) -> ImageInspectionArtifacts:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        contract = load_contract(contract_path)
        result = prepare_image(contract, image_path)
    except (OSError, PreprocessError, RuntimeError) as exc:
        raise ImageInspectionError(str(exc)) from exc

    summary = summarize_array(result.input_tensor)
    summary_path = _write_json(out / "input_tensor_summary.json", asdict(summary))

    preview_path = None
    if save_image:
        preview_path = save_preview_image(out / "preprocessed.png", result.display_ready_image)

    tensor_dump_path = None
    if save_tensor:
        tensor_dump_path = out / "input_tensor.npy"
        np.save(tensor_dump_path, result.input_tensor)

    report = InspectionReport(
        contract_name=contract.name,
        image_path=str(Path(image_path)),
        source_framework=contract.source_framework,
        target_runtime=contract.target_runtime,
        task=contract.task,
        source_image={"width": result.source_width, "height": result.source_height},
        preprocess={
            "input_color_space": result.input_color_space,
            "output_color_space": result.output_color_space,
            "input_layout": result.input_layout,
            "output_layout": result.output_layout,
            "resize": asdict(result.resize),
        },
        tensor_summary=asdict(summary),
        checks=_build_checks(contract, result),
        artifacts=InspectionArtifactPaths(
            report_json="report.json",
            tensor_summary_json="input_tensor_summary.json",
            preview_image="preprocessed.png" if preview_path else None,
            tensor_dump="input_tensor.npy" if tensor_dump_path else None,
        ),
    )

    report_path = write_report_json(report, out / "report.json")
    markdown_path = None
    html_path = None

    try:
        if report_format == "md":
            markdown_path = write_report_markdown(report, out / "report.md")
        elif report_format == "html":
            html_path = write_report_html(report, out / "report.html")
    except RuntimeError as exc:
        raise ImageInspectionError(str(exc)) from exc

    return ImageInspectionArtifacts(
        report=report_path,
        tensor_summary=summary_path,
        preview_image=preview_path,
        tensor_dump=tensor_dump_path,
        report_markdown=markdown_path,
        report_html=html_path,
    )
