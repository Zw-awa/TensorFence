from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from unittest.mock import patch
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TMP_ROOT = ROOT / ".tmp" / "tests" / "compare-stages"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.cli import main


CONTRACT_TEXT = """
name: test-compare
task: detection
source_framework: pytorch
target_runtime: rknn
input:
  name: images
  shape: [1, 3, 4, 4]
  dtype: float32
  layout: NCHW
  semantic: model_input
outputs:
  - name: output0
    shape: [1, 1, 6]
    dtype: float32
    layout: N/A
    semantic: raw_predictions
preprocess:
  input_color_space: RGB
  input_layout: HWC
  output_color_space: RGB
  output_layout: NCHW
  resize:
    mode: stretch
    target_size: [4, 4]
    interpolation: bilinear
    keep_aspect_ratio: false
  normalize:
    scale: 1.0
    mean: [0.0, 0.0, 0.0]
    std: [1.0, 1.0, 1.0]
  pad_value: 0
decode:
  family: yolo
  mode: anchor_free
  num_classes: 1
  strides: [8]
  head_names: [output0]
  score_activation: sigmoid
  box_activation: sigmoid
"""


class CompareStagesTests(unittest.TestCase):
    def _make_temp_root(self) -> Path:
        path = TMP_ROOT / str(uuid.uuid4())
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _write_sample_image(self, path: Path) -> None:
        Image.fromarray(np.full((4, 4, 3), 100, dtype=np.uint8), mode="RGB").save(path)

    def _write_stage_npz(self, path: Path, output0: np.ndarray, key: str = "output0") -> None:
        np.savez(path, **{key: output0})

    def test_compare_stages_with_npz_inputs_generates_reports(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        onnx_path = temp_root / "onnx.npz"
        rknn_path = temp_root / "rknn.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]]], dtype=np.float32)
        self._write_stage_npz(framework_path, base)
        self._write_stage_npz(onnx_path, base.copy())
        self._write_stage_npz(rknn_path, base + 0.01)

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--onnx-out",
                str(onnx_path),
                "--rknn-out",
                str(rknn_path),
                "--out",
                str(out_dir),
                "--report-format",
                "md",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((out_dir / "report.json").exists())
        self.assertTrue((out_dir / "report.md").exists())
        self.assertTrue((out_dir / "tensor_diffs.json").exists())
        self.assertTrue((out_dir / "final_summary.json").exists())

        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["contract_name"], "test-compare")
        self.assertEqual(len(report["stages"]), 3)
        self.assertTrue(report["final_summary"]["drift_detected"])
        self.assertEqual(report["final_summary"]["first_drift_pair"], "onnx->rknn")

    def test_compare_stages_maps_npz_by_order_with_warning(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        onnx_path = temp_root / "onnx.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[1, 2, 3, 4, 5, 6]]], dtype=np.float32)
        self._write_stage_npz(framework_path, base, key="tensor_a")
        self._write_stage_npz(onnx_path, base, key="tensor_b")

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--onnx-out",
                str(onnx_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 0)
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        warnings = report["warnings"]
        self.assertTrue(any("mapped outputs by file order" in warning for warning in warnings))

    def test_compare_stages_requires_two_available_stages(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[1, 2, 3, 4, 5, 6]]], dtype=np.float32)
        self._write_stage_npz(framework_path, base)

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_compare_stages_rejects_bad_npz_mapping(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        onnx_path = temp_root / "onnx.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        np.savez(framework_path, a=np.ones((1, 1, 6), dtype=np.float32), b=np.ones((1, 1, 6), dtype=np.float32))
        self._write_stage_npz(onnx_path, np.ones((1, 1, 6), dtype=np.float32))

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--onnx-out",
                str(onnx_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_compare_stages_rejects_framework_runner_without_outputs(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-runner",
                "pytorch",
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_compare_stages_writes_html_report(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        onnx_path = temp_root / "onnx.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]]], dtype=np.float32)
        self._write_stage_npz(framework_path, base)
        self._write_stage_npz(onnx_path, base.copy())

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--onnx-out",
                str(onnx_path),
                "--out",
                str(out_dir),
                "--report-format",
                "html",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((out_dir / "report.html").exists())
        html = (out_dir / "report.html").read_text(encoding="utf-8")
        self.assertIn("Stage Compare Report", html)
        self.assertIn("framework", html)
        self.assertIn("onnx", html)
        self.assertIn("right_zero", html)
        self.assertIn("small_zero", html)

    def test_compare_stages_reports_shape_mismatch(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        onnx_path = temp_root / "onnx.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        self._write_stage_npz(framework_path, np.ones((1, 1, 6), dtype=np.float32))
        self._write_stage_npz(onnx_path, np.ones((1, 2, 6), dtype=np.float32))

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--onnx-out",
                str(onnx_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 0)
        diffs = json.loads((out_dir / "tensor_diffs.json").read_text(encoding="utf-8"))
        self.assertEqual(diffs[0]["status"], "shape_mismatch")
        self.assertIn("shape mismatch", diffs[0]["reasons"])

    def test_compare_stages_flags_small_values_collapsing_to_zero(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        rknn_path = temp_root / "rknn.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        reference = np.full((1, 1, 6), 1e-7, dtype=np.float32)
        quantized = np.zeros_like(reference)
        self._write_stage_npz(framework_path, reference)
        self._write_stage_npz(rknn_path, quantized)

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--rknn-out",
                str(rknn_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 0)
        diffs = json.loads((out_dir / "tensor_diffs.json").read_text(encoding="utf-8"))
        self.assertEqual(diffs[0]["status"], "drift")
        self.assertEqual(diffs[0]["small_value_count"], 6)
        self.assertEqual(diffs[0]["small_value_fraction"], 1.0)
        self.assertEqual(diffs[0]["small_value_zero_fraction"], 1.0)
        self.assertTrue(any("quantization under-resolution" in reason for reason in diffs[0]["reasons"]))

    def test_compare_stages_does_not_flag_small_values_that_are_preserved(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        rknn_path = temp_root / "rknn.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        reference = np.full((1, 1, 6), 1e-7, dtype=np.float32)
        self._write_stage_npz(framework_path, reference)
        self._write_stage_npz(rknn_path, reference.copy())

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--rknn-out",
                str(rknn_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 0)
        diffs = json.loads((out_dir / "tensor_diffs.json").read_text(encoding="utf-8"))
        self.assertEqual(diffs[0]["status"], "aligned")
        self.assertEqual(diffs[0]["small_value_zero_fraction"], 0.0)
        self.assertFalse(any("under-resolution" in reason for reason in diffs[0]["reasons"]))

    def test_compare_stages_onnx_model_requires_onnxruntime(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        self._write_stage_npz(framework_path, np.ones((1, 1, 6), dtype=np.float32))
        dummy_model = temp_root / "model.onnx"
        dummy_model.write_bytes(b"not a real model")

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--onnx",
                str(dummy_model),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_compare_stages_report_contains_skipped_stage_record(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        onnx_path = temp_root / "onnx.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[1, 2, 3, 4, 5, 6]]], dtype=np.float32)
        self._write_stage_npz(framework_path, base)
        self._write_stage_npz(onnx_path, base.copy())

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--framework-out",
                str(framework_path),
                "--onnx-out",
                str(onnx_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 0)
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        rknn_stage = next(stage for stage in report["stages"] if stage["stage"] == "rknn")
        self.assertFalse(rknn_stage["available"])
        self.assertEqual(rknn_stage["source_kind"], "not-provided")

    def test_compare_stages_framework_runner_path_can_be_mocked(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        onnx_path = temp_root / "onnx.npz"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[0.5, 0.4, 0.3, 0.2, 0.1, 0.0]]], dtype=np.float32)
        self._write_stage_npz(onnx_path, base.copy())

        with patch("tensorfence.core.stage_compare.run_framework_outputs") as mocked:
            mocked.return_value = ({"output0": base.copy()}, ["mock framework runner"])
            exit_code = main(
                [
                    "compare-stages",
                    "--contract",
                    str(contract_path),
                    "--image",
                    str(image_path),
                    "--framework-runner",
                    "pytorch",
                    "--onnx-out",
                    str(onnx_path),
                    "--out",
                    str(out_dir),
                ]
            )

        self.assertEqual(exit_code, 0)
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        framework_stage = next(stage for stage in report["stages"] if stage["stage"] == "framework")
        self.assertTrue(framework_stage["available"])
        self.assertEqual(framework_stage["source_kind"], "runner:pytorch")
        self.assertIn("mock framework runner", framework_stage["warnings"])
        self.assertEqual(report["final_summary"]["available_stages"], ["framework", "onnx"])
        self.assertEqual(report["final_summary"]["warning_count"], 1)

    def test_compare_stages_onnx_model_path_can_be_mocked(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        dummy_onnx = temp_root / "model.onnx"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[0.6, 0.5, 0.4, 0.3, 0.2, 0.1]]], dtype=np.float32)
        self._write_stage_npz(framework_path, base.copy())
        dummy_onnx.write_bytes(b"placeholder")

        with patch("tensorfence.core.stage_compare.run_onnx_model") as mocked:
            mocked.return_value = ({"output0": base.copy()}, ["mock onnx runtime"])
            exit_code = main(
                [
                    "compare-stages",
                    "--contract",
                    str(contract_path),
                    "--image",
                    str(image_path),
                    "--framework-out",
                    str(framework_path),
                    "--onnx",
                    str(dummy_onnx),
                    "--out",
                    str(out_dir),
                ]
            )

        self.assertEqual(exit_code, 0)
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        onnx_stage = next(stage for stage in report["stages"] if stage["stage"] == "onnx")
        self.assertTrue(onnx_stage["available"])
        self.assertEqual(onnx_stage["source_kind"], "onnxruntime")
        self.assertIn("mock onnx runtime", onnx_stage["warnings"])
        self.assertEqual(report["final_summary"]["available_stages"], ["framework", "onnx"])
        self.assertEqual(report["final_summary"]["drift_detected"], False)

    def test_compare_stages_rknn_model_path_can_be_mocked(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        framework_path = temp_root / "framework.npz"
        dummy_rknn = temp_root / "model.rknn"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        self._write_sample_image(image_path)
        base = np.asarray([[[0.0, 0.1, 0.2, 0.3, 0.4, 0.5]]], dtype=np.float32)
        self._write_stage_npz(framework_path, base.copy())
        dummy_rknn.write_bytes(b"placeholder")

        with patch("tensorfence.core.stage_compare.run_rknn_model") as mocked:
            mocked.return_value = ({"output0": base + 0.02}, ["mock rknn runtime"])
            exit_code = main(
                [
                    "compare-stages",
                    "--contract",
                    str(contract_path),
                    "--image",
                    str(image_path),
                    "--framework-out",
                    str(framework_path),
                    "--rknn",
                    str(dummy_rknn),
                    "--out",
                    str(out_dir),
                ]
            )

        self.assertEqual(exit_code, 0)
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        rknn_stage = next(stage for stage in report["stages"] if stage["stage"] == "rknn")
        self.assertTrue(rknn_stage["available"])
        self.assertEqual(rknn_stage["source_kind"], "rknn-runtime")
        self.assertIn("mock rknn runtime", rknn_stage["warnings"])
        self.assertEqual(report["final_summary"]["available_stages"], ["framework", "rknn"])
        self.assertEqual(report["final_summary"]["first_drift_pair"], "framework->rknn")


if __name__ == "__main__":
    unittest.main()
