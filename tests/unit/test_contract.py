from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.core.contracts import ContractError, load_contract, load_contract_from_text
from tensorfence.core.diff import compare_arrays
from tensorfence.core.validation import has_errors, validate_contract


class ContractTests(unittest.TestCase):
    def test_sample_contract_validates(self) -> None:
        contract_path = ROOT / "examples" / "detection_contract.yaml"
        contract = load_contract(contract_path)
        issues = validate_contract(contract)

        self.assertFalse(has_errors(issues))
        self.assertEqual(contract.name, "tensorfence-demo-yolo")
        self.assertEqual(len(contract.outputs), 1)

    def test_tensor_diff_for_identical_arrays(self) -> None:
        left = np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        right = np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)

        diff = compare_arrays(left, right)

        self.assertTrue(diff.shape_match)
        self.assertTrue(diff.dtype_match)
        self.assertEqual(diff.max_abs_error, 0.0)
        self.assertEqual(diff.mean_abs_error, 0.0)
        self.assertEqual(diff.rms_error, 0.0)
        self.assertAlmostEqual(diff.cosine_similarity, 1.0)

    def test_contract_rejects_unknown_fields(self) -> None:
        source = (ROOT / "examples" / "detection_contract.yaml").read_text(encoding="utf-8")
        source = source.replace("score_threshold:", "score_thresold:")

        with self.assertRaises(ContractError) as raised:
            load_contract_from_text(source)

        self.assertIn("score_thresold", str(raised.exception))

    def test_contract_rejects_non_positive_resize_target(self) -> None:
        source = (ROOT / "examples" / "detection_contract.yaml").read_text(encoding="utf-8")
        source = source.replace("target_size: [640, 640]", "target_size: [0, 640]")

        with self.assertRaises(ContractError) as raised:
            load_contract_from_text(source)

        self.assertIn("resize.target_size values must be positive", str(raised.exception))

    def test_custom_nc_contract_is_not_forced_to_detection_shape_or_nms(self) -> None:
        source = """
name: custom-vector
task: custom
source_framework: custom
target_runtime: custom
input:
  name: features
  shape: [1, 8]
  dtype: float32
  layout: NC
  semantic: feature_vector
outputs:
  - name: output
    shape: [1, 2]
    dtype: float32
    layout: NC
    semantic: scores
preprocess:
  input_color_space: GRAY
  input_layout: N/A
  output_color_space: GRAY
  output_layout: NC
  resize:
    mode: stretch
    target_size: [1, 8]
    interpolation: nearest
    keep_aspect_ratio: false
  pad_value: 0
"""
        contract = load_contract_from_text(source)
        issues = validate_contract(contract)

        self.assertFalse(has_errors(issues))
        self.assertFalse(any(issue.code == "nms.missing" for issue in issues))

    def test_contract_rejects_tensor_and_preprocess_layout_mismatch(self) -> None:
        contract = load_contract(ROOT / "examples" / "detection_contract.yaml")
        contract.input.layout = "NHWC"

        issues = validate_contract(contract)

        self.assertTrue(has_errors(issues))
        self.assertTrue(any(issue.code == "input.layout.mismatch" for issue in issues))

    def test_contract_rejects_invalid_decode_and_nms_ranges(self) -> None:
        contract = load_contract(ROOT / "examples" / "detection_contract.yaml")
        assert contract.decode is not None
        assert contract.nms is not None
        contract.decode.strides = [8, 0, -16]
        contract.nms.score_threshold = 2.0
        contract.nms.iou_threshold = -0.1
        contract.nms.max_detections = 0

        issues = validate_contract(contract)
        codes = {issue.code for issue in issues}

        self.assertTrue(has_errors(issues))
        self.assertIn("decode.strides.invalid", codes)
        self.assertIn("nms.score_threshold.invalid", codes)
        self.assertIn("nms.iou_threshold.invalid", codes)
        self.assertIn("nms.max_detections.invalid", codes)

    def test_contract_warns_when_preprocess_cannot_emit_declared_dtype(self) -> None:
        contract = load_contract(ROOT / "examples" / "detection_contract.yaml")
        contract.input.dtype = "uint8"

        issues = validate_contract(contract)

        self.assertFalse(has_errors(issues))
        self.assertTrue(any(issue.code == "input.dtype.preprocess_unsupported" for issue in issues))

    def test_contract_rejects_invalid_preprocess_vectors_and_padding(self) -> None:
        contract = load_contract(ROOT / "examples" / "detection_contract.yaml")
        assert contract.preprocess.normalize is not None
        contract.preprocess.normalize.mean = [0.0, 0.0]
        contract.preprocess.normalize.std = [0.0, 1.0, 1.0]
        contract.preprocess.pad_value = -1

        issues = validate_contract(contract)
        codes = {issue.code for issue in issues}

        self.assertTrue(has_errors(issues))
        self.assertIn("preprocess.normalize.mean.length", codes)
        self.assertIn("preprocess.normalize.std.zero", codes)
        self.assertIn("preprocess.pad_value.range", codes)


if __name__ == "__main__":
    unittest.main()
