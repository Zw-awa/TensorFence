from __future__ import annotations

import json
import shutil
import sys
import uuid
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TMP_ROOT = ROOT / ".tmp" / "tests" / "inspect-image"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.cli import main
from tensorfence.core.contracts import load_contract_from_text
from tensorfence.core.preprocess import prepare_image


CONTRACT_TEXT = """
name: test-inspect
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
    mode: letterbox
    target_size: [4, 4]
    interpolation: bilinear
    keep_aspect_ratio: true
  normalize:
    scale: 1.0
    mean: [0.0, 0.0, 0.0]
    std: [1.0, 1.0, 1.0]
  pad_value: 114
decode:
  family: yolo
  mode: anchor_free
  num_classes: 1
  strides: [8]
  head_names: [output0]
  score_activation: sigmoid
  box_activation: sigmoid
"""


class InspectImageTests(unittest.TestCase):
    def _make_temp_root(self) -> Path:
        path = TMP_ROOT / str(uuid.uuid4())
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_prepare_image_returns_expected_tensor_shape(self) -> None:
        contract = load_contract_from_text(CONTRACT_TEXT)
        temp_root = self._make_temp_root()
        image_path = temp_root / "sample.png"
        Image.fromarray(np.full((2, 4, 3), 50, dtype=np.uint8), mode="RGB").save(image_path)

        result = prepare_image(contract, image_path)

        self.assertEqual(result.input_tensor.shape, (1, 3, 4, 4))
        self.assertEqual(result.resize.pad_top, 1)
        self.assertEqual(result.resize.pad_bottom, 1)

    def test_cli_inspect_image_writes_artifacts(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        Image.fromarray(np.full((3, 5, 3), 120, dtype=np.uint8), mode="RGB").save(image_path)

        exit_code = main(
            [
                "inspect-image",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--out",
                str(out_dir),
                "--report-format",
                "md",
                "--save-image",
                "--save-tensor",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((out_dir / "report.json").exists())
        self.assertTrue((out_dir / "report.md").exists())
        self.assertTrue((out_dir / "input_tensor_summary.json").exists())
        self.assertTrue((out_dir / "preprocessed.png").exists())
        self.assertTrue((out_dir / "input_tensor.npy").exists())

        report_data = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report_data["contract_name"], "test-inspect")
        self.assertEqual(report_data["tensor_summary"]["shape"], [1, 3, 4, 4])

    def test_cli_inspect_image_writes_json_report_only(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "sample.png"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        Image.fromarray(np.full((4, 4, 3), 80, dtype=np.uint8), mode="RGB").save(image_path)

        exit_code = main(
            [
                "inspect-image",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--out",
                str(out_dir),
                "--report-format",
                "json",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((out_dir / "report.json").exists())
        self.assertFalse((out_dir / "report.md").exists())
        self.assertFalse((out_dir / "report.html").exists())

    def test_cli_inspect_image_rejects_missing_contract(self) -> None:
        temp_root = self._make_temp_root()
        image_path = temp_root / "sample.png"
        out_dir = temp_root / "out"
        Image.fromarray(np.full((4, 4, 3), 80, dtype=np.uint8), mode="RGB").save(image_path)

        exit_code = main(
            [
                "inspect-image",
                "--contract",
                str(temp_root / "missing.yaml"),
                "--image",
                str(image_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_cli_inspect_image_rejects_bad_image(self) -> None:
        temp_root = self._make_temp_root()
        contract_path = temp_root / "contract.yaml"
        image_path = temp_root / "bad.png"
        out_dir = temp_root / "out"

        contract_path.write_text(CONTRACT_TEXT, encoding="utf-8")
        image_path.write_text("not an image", encoding="utf-8")

        exit_code = main(
            [
                "inspect-image",
                "--contract",
                str(contract_path),
                "--image",
                str(image_path),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
