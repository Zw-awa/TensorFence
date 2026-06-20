from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..adapters.framework import FrameworkAdapterError, load_framework_outputs, run_framework_outputs
from ..adapters.onnxruntime import OnnxRuntimeAdapterError, load_onnx_outputs, run_onnx_model
from ..adapters.rknn import RknnAdapterError, load_rknn_outputs, run_rknn_model
from ..artifacts.reports.stage_report import (
    StageCompareReport,
    StageFinalSummary,
    StagePairDiffEntry,
    StageRecord,
    StageTensorSummaryEntry,
    write_final_summary_json,
    write_stage_report_html,
    write_stage_report_json,
    write_stage_report_markdown,
    write_tensor_diffs_json,
)
from .contracts import load_contract
from .diff import compare_arrays, summarize_array
from .preprocess import PreprocessError, prepare_image


class StageCompareError(RuntimeError):
    pass


@dataclass(frozen=True)
class StageCompareArtifacts:
    report_json: Path
    tensor_diffs_json: Path
    final_summary_json: Path
    report_markdown: Path | None
    report_html: Path | None


@dataclass(frozen=True)
class _ResolvedStage:
    stage: Literal["framework", "onnx", "rknn"]
    source_kind: str
    source_path: str | None
    outputs: dict[str, object]
    warnings: list[str]
    available: bool


def _coerce_outputs(
    outputs: dict[str, object],
    expected_names: list[str],
    stage_name: str,
) -> tuple[dict[str, object], list[str]]:
    warnings: list[str] = []
    if all(name in outputs for name in expected_names):
        return {name: outputs[name] for name in expected_names}, warnings

    keys = list(outputs.keys())
    if len(keys) == len(expected_names):
        warnings.append(
            f"{stage_name} output names {keys} do not match contract outputs {expected_names}; mapped outputs by order"
        )
        return {expected_names[index]: outputs[key] for index, key in enumerate(keys)}, warnings

    raise StageCompareError(
        f"{stage_name} outputs {keys} do not match expected outputs {expected_names}; provide aligned stage artifacts"
    )


def _make_stage_record(stage: _ResolvedStage) -> StageRecord:
    outputs = []
    for name, value in stage.outputs.items():
        summary = summarize_array(value)
        outputs.append(
            StageTensorSummaryEntry(
                name=name,
                shape=list(summary.shape),
                dtype=summary.dtype,
                minimum=summary.minimum,
                maximum=summary.maximum,
                mean=summary.mean,
                std=summary.std,
            )
        )
    return StageRecord(
        stage=stage.stage,
        source_kind=stage.source_kind,
        source_path=stage.source_path,
        available=stage.available,
        warnings=stage.warnings,
        outputs=outputs,
    )


def _diff_status(shape_match: bool, dtype_match: bool, max_abs: float | None, cosine: float | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not shape_match:
        reasons.append("shape mismatch")
        return "shape_mismatch", reasons
    if not dtype_match:
        reasons.append("dtype mismatch")
    if max_abs is not None and max_abs > 1e-3:
        reasons.append(f"max_abs_error>{1e-3}")
    if cosine is not None and cosine < 0.999:
        reasons.append(f"cosine_similarity<{0.999}")
    if reasons:
        return "drift", reasons
    return "aligned", reasons


def _resolve_framework_stage(
    framework_out: str | Path | None,
    framework_runner: str | None,
    contract_path: str | Path,
    image_path: str | Path,
    input_tensor,
    expected_names: list[str],
) -> _ResolvedStage:
    if framework_out:
        outputs, warnings = load_framework_outputs(framework_out, expected_names)
        return _ResolvedStage(
            stage="framework",
            source_kind="npz",
            source_path=str(framework_out),
            outputs=outputs,
            warnings=warnings,
            available=True,
        )
    if framework_runner:
        try:
            outputs, warnings = run_framework_outputs(
                framework_runner,
                contract_path=contract_path,
                image_path=image_path,
                input_tensor=input_tensor,
                expected_names=expected_names,
            )
            mapped, name_warnings = _coerce_outputs(outputs, expected_names, "framework")
            return _ResolvedStage(
                stage="framework",
                source_kind=f"runner:{framework_runner}",
                source_path=None,
                outputs=mapped,
                warnings=warnings + name_warnings,
                available=True,
            )
        except FrameworkAdapterError as exc:
            return _ResolvedStage(
                stage="framework",
                source_kind=f"runner:{framework_runner}",
                source_path=None,
                outputs={},
                warnings=[str(exc)],
                available=False,
            )
    return _ResolvedStage(
        stage="framework",
        source_kind="not-provided",
        source_path=None,
        outputs={},
        warnings=[],
        available=False,
    )


def _resolve_onnx_stage(
    onnx_model: str | Path | None,
    onnx_out: str | Path | None,
    input_tensor,
    expected_names: list[str],
) -> _ResolvedStage:
    if onnx_out:
        outputs, warnings = load_onnx_outputs(onnx_out, expected_names)
        return _ResolvedStage(
            stage="onnx",
            source_kind="npz",
            source_path=str(onnx_out),
            outputs=outputs,
            warnings=warnings,
            available=True,
        )
    if onnx_model:
        outputs, warnings = run_onnx_model(onnx_model, input_tensor)
        mapped, name_warnings = _coerce_outputs(outputs, expected_names, "onnx")
        return _ResolvedStage(
            stage="onnx",
            source_kind="onnxruntime",
            source_path=str(onnx_model),
            outputs=mapped,
            warnings=warnings + name_warnings,
            available=True,
        )
    return _ResolvedStage(
        stage="onnx",
        source_kind="not-provided",
        source_path=None,
        outputs={},
        warnings=[],
        available=False,
    )


def _resolve_rknn_stage(
    rknn_model: str | Path | None,
    rknn_out: str | Path | None,
    input_tensor,
    expected_names: list[str],
) -> _ResolvedStage:
    if rknn_out:
        outputs, warnings = load_rknn_outputs(rknn_out, expected_names)
        return _ResolvedStage(
            stage="rknn",
            source_kind="npz",
            source_path=str(rknn_out),
            outputs=outputs,
            warnings=warnings,
            available=True,
        )
    if rknn_model:
        try:
            outputs, warnings = run_rknn_model(
                rknn_model,
                input_tensor=input_tensor,
                expected_names=expected_names,
            )
            mapped, name_warnings = _coerce_outputs(outputs, expected_names, "rknn")
            return _ResolvedStage(
                stage="rknn",
                source_kind="rknn-runtime",
                source_path=str(rknn_model),
                outputs=mapped,
                warnings=warnings + name_warnings,
                available=True,
            )
        except RknnAdapterError as exc:
            return _ResolvedStage(
                stage="rknn",
                source_kind="rknn-runtime",
                source_path=str(rknn_model),
                outputs={},
                warnings=[str(exc)],
                available=False,
            )
    return _ResolvedStage(
        stage="rknn",
        source_kind="not-provided",
        source_path=None,
        outputs={},
        warnings=[],
        available=False,
    )


def compare_stages(
    contract_path: str | Path,
    image_path: str | Path,
    out_dir: str | Path,
    framework_out: str | Path | None = None,
    framework_runner: str | None = None,
    onnx_model: str | Path | None = None,
    onnx_out: str | Path | None = None,
    rknn_model: str | Path | None = None,
    rknn_out: str | Path | None = None,
    report_format: str = "json",
) -> StageCompareArtifacts:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        contract = load_contract(contract_path)
        preprocess = prepare_image(contract, image_path)
    except (OSError, RuntimeError, PreprocessError) as exc:
        raise StageCompareError(str(exc)) from exc

    expected_names = [output.name for output in contract.outputs]
    try:
        stages = [
            _resolve_framework_stage(
                framework_out,
                framework_runner,
                contract_path,
                image_path,
                preprocess.input_tensor,
                expected_names,
            ),
            _resolve_onnx_stage(onnx_model, onnx_out, preprocess.input_tensor, expected_names),
            _resolve_rknn_stage(rknn_model, rknn_out, preprocess.input_tensor, expected_names),
        ]
    except (FrameworkAdapterError, OnnxRuntimeAdapterError, RknnAdapterError) as exc:
        raise StageCompareError(str(exc)) from exc

    available = [stage for stage in stages if stage.available]
    if len(available) < 2:
        raise StageCompareError(
            "compare-stages needs at least two available stages; provide framework/onnx/rknn outputs or install required runtimes"
        )

    pair_diffs: list[StagePairDiffEntry] = []
    for left, right in zip(available, available[1:], strict=False):
        for output_name in expected_names:
            diff = compare_arrays(left.outputs[output_name], right.outputs[output_name])
            status, reasons = _diff_status(
                diff.shape_match,
                diff.dtype_match,
                diff.max_abs_error,
                diff.cosine_similarity,
            )
            pair_diffs.append(
                StagePairDiffEntry(
                    left_stage=left.stage,
                    right_stage=right.stage,
                    tensor_name=output_name,
                    status=status,  # type: ignore[arg-type]
                    shape_match=diff.shape_match,
                    dtype_match=diff.dtype_match,
                    max_abs_error=diff.max_abs_error,
                    mean_abs_error=diff.mean_abs_error,
                    rms_error=diff.rms_error,
                    cosine_similarity=diff.cosine_similarity,
                    reasons=reasons,
                )
            )

    first_drift = next((item for item in pair_diffs if item.status != "aligned"), None)
    warnings: list[str] = []
    for stage in stages:
        warnings.extend(stage.warnings)

    final_summary = StageFinalSummary(
        available_stages=[stage.stage for stage in available],
        compared_pairs=[f"{item.left_stage}->{item.right_stage}" for item in pair_diffs],
        drift_detected=first_drift is not None,
        first_drift_stage=first_drift.right_stage if first_drift is not None else None,
        first_drift_pair=f"{first_drift.left_stage}->{first_drift.right_stage}" if first_drift is not None else None,
        warning_count=len(warnings),
    )
    report = StageCompareReport(
        contract_name=contract.name,
        image_path=str(Path(image_path)),
        input_tensor_shape=list(preprocess.input_tensor.shape),
        input_tensor_dtype=str(preprocess.input_tensor.dtype),
        stages=[_make_stage_record(stage) for stage in stages],
        pair_diffs=pair_diffs,
        final_summary=final_summary,
        warnings=warnings,
    )

    report_json = write_stage_report_json(report, out / "report.json")
    tensor_diffs_json = write_tensor_diffs_json(pair_diffs, out / "tensor_diffs.json")
    final_summary_json = write_final_summary_json(final_summary, out / "final_summary.json")
    report_markdown = None
    report_html = None
    try:
        if report_format == "md":
            report_markdown = write_stage_report_markdown(report, out / "report.md")
        elif report_format == "html":
            report_html = write_stage_report_html(report, out / "report.html")
    except RuntimeError as exc:
        raise StageCompareError(str(exc)) from exc

    return StageCompareArtifacts(
        report_json=report_json,
        tensor_diffs_json=tensor_diffs_json,
        final_summary_json=final_summary_json,
        report_markdown=report_markdown,
        report_html=report_html,
    )
