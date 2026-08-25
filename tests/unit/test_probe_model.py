from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TMP_ROOT = ROOT / ".tmp" / "tests" / "probe-model"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.cli import main
from tensorfence.artifacts.facts.model_facts import load_model_facts_json

try:
    import onnx
    from onnx import TensorProto, helper
except ModuleNotFoundError:
    onnx = None
    TensorProto = None
    helper = None


@unittest.skipIf(onnx is None, "onnx is not installed")
class ProbeModelTests(unittest.TestCase):
    def _make_temp_root(self) -> Path:
        path = TMP_ROOT / str(uuid.uuid4())
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _write_sample_onnx(self, path: Path) -> None:
        input_tensor = helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 3, 4, 4])
        output_tensor = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 4, 4])
        relu_node = helper.make_node("Relu", ["input"], ["output"], name="relu0")
        graph = helper.make_graph([relu_node], "sample-graph", [input_tensor], [output_tensor])
        model = helper.make_model(graph, producer_name="tensorfence-test")
        onnx.save_model(model, str(path))

    def _write_nms_onnx(self, path: Path) -> None:
        boxes = helper.make_tensor_value_info("boxes", TensorProto.FLOAT, [1, 10, 4])
        scores = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [1, 1, 10])
        selected = helper.make_tensor_value_info("selected_indices", TensorProto.INT64, [None, 3])
        nms_node = helper.make_node(
            "NonMaxSuppression",
            ["boxes", "scores"],
            ["selected_indices"],
            name="nms0",
        )
        graph = helper.make_graph([nms_node], "nms-graph", [boxes, scores], [selected])
        model = helper.make_model(graph, producer_name="tensorfence-test")
        onnx.save_model(model, str(path))

    def _write_ppyoloe_onnx(self, path: Path) -> None:
        image = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 320, 320])
        boxes = helper.make_tensor_value_info("boxes", TensorProto.FLOAT, [1, 2100, 4])
        scores = helper.make_tensor_value_info("scores", TensorProto.FLOAT, [1, 10, 2100])
        box_value = helper.make_tensor("box_value", TensorProto.FLOAT, [1, 2100, 4], [0.0] * 8400)
        score_value = helper.make_tensor("score_value", TensorProto.FLOAT, [1, 10, 2100], [0.0] * 21000)
        graph = helper.make_graph(
            [
                helper.make_node("Constant", [], ["boxes"], value=box_value),
                helper.make_node("Constant", [], ["scores"], value=score_value),
            ],
            "ppyoloe-graph",
            [image],
            [boxes, scores],
        )
        onnx.save_model(helper.make_model(graph), str(path))

    def test_probe_model_writes_artifacts(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        out_dir = temp_root / "out"
        self._write_sample_onnx(model_path)

        exit_code = main(
            [
                "probe-model",
                "--model",
                str(model_path),
                "--out",
                str(out_dir),
                "--format",
                "both",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((out_dir / "model_facts.json").exists())
        self.assertTrue((out_dir / "ops_summary.json").exists())
        self.assertTrue((out_dir / "graph_summary.md").exists())

        facts = json.loads((out_dir / "model_facts.json").read_text(encoding="utf-8"))
        self.assertEqual(facts["format"], "onnx")
        self.assertEqual(facts["schema_version"], "tensorfence.model-facts/v1")
        self.assertEqual(facts["inputs"][0]["name"], "input")
        self.assertEqual(facts["outputs"][0]["name"], "output")
        self.assertEqual(facts["operator_histogram"]["Relu"], 1)
        self.assertEqual(facts["warnings"], [])

    def test_probe_model_flags_embedded_nms_as_duplicate_postprocess_risk(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "nms.onnx"
        out_dir = temp_root / "out"
        self._write_nms_onnx(model_path)

        exit_code = main(
            [
                "probe-model",
                "--model",
                str(model_path),
                "--out",
                str(out_dir),
                "--format",
                "both",
            ]
        )

        self.assertEqual(exit_code, 0)
        facts = json.loads((out_dir / "model_facts.json").read_text(encoding="utf-8"))
        summary = json.loads((out_dir / "ops_summary.json").read_text(encoding="utf-8"))
        markdown = (out_dir / "graph_summary.md").read_text(encoding="utf-8")
        self.assertEqual(facts["operator_histogram"]["NonMaxSuppression"], 1)
        self.assertEqual(summary["schema_version"], "tensorfence.ops-summary/v1")
        self.assertTrue(any("duplicate postprocessing" in warning for warning in facts["warnings"]))
        self.assertEqual(summary["warnings"], facts["warnings"])
        self.assertIn("embedded postprocess detected", markdown)
        self.assertEqual(facts["output_contract"]["kind"], "end_to_end_nms")

    def test_probe_model_identifies_ppyoloe_boxes_and_scores_contract(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "ppyoloe.onnx"
        out_dir = temp_root / "out"
        self._write_ppyoloe_onnx(model_path)

        self.assertEqual(0, main(["probe-model", "--model", str(model_path), "--out", str(out_dir)]))
        facts = json.loads((out_dir / "model_facts.json").read_text(encoding="utf-8"))
        self.assertEqual(facts["output_contract"]["kind"], "ppyoloe_boxes_scores")
        self.assertEqual(facts["output_contract"]["confidence"], "high")

    def test_probe_model_flags_contract_nms_against_embedded_nms(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "nms.onnx"
        contract_path = temp_root / "contract.yaml"
        out_dir = temp_root / "out"
        self._write_nms_onnx(model_path)
        contract_path.write_text(
            """
name: nms-conflict
task: detection
source_framework: onnx
target_runtime: rknn
input:
  name: images
  shape: [1, 3, 4, 4]
  dtype: float32
  layout: NCHW
  semantic: model_input
outputs:
  - name: selected_indices
    shape: [1, 3]
    dtype: int64
    layout: N/A
    semantic: final_detections
preprocess:
  input_color_space: RGB
  output_color_space: RGB
  input_layout: HWC
  output_layout: NCHW
  resize:
    mode: stretch
    target_size: [4, 4]
    keep_aspect_ratio: false
nms:
  score_threshold: 0.25
  iou_threshold: 0.45
""",
            encoding="utf-8",
        )
        self.assertEqual(
            0,
            main(["probe-model", "--model", str(model_path), "--contract", str(contract_path), "--out", str(out_dir)]),
        )
        facts = json.loads((out_dir / "model_facts.json").read_text(encoding="utf-8"))
        self.assertTrue(any("duplicate postprocessing detected" in item for item in facts["warnings"]))

    def test_probe_model_rejects_unsupported_model_type(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        out_dir = temp_root / "out"
        self._write_sample_onnx(model_path)

        exit_code = main(
            [
                "probe-model",
                "--model",
                str(model_path),
                "--model-type",
                "rknn",
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_probe_model_json_only_skips_markdown(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        out_dir = temp_root / "out"
        self._write_sample_onnx(model_path)

        exit_code = main(
            [
                "probe-model",
                "--model",
                str(model_path),
                "--out",
                str(out_dir),
                "--format",
                "json",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((out_dir / "model_facts.json").exists())
        self.assertTrue((out_dir / "ops_summary.json").exists())
        self.assertFalse((out_dir / "graph_summary.md").exists())

    def test_probe_model_rejects_missing_file(self) -> None:
        temp_root = self._make_temp_root()
        out_dir = temp_root / "out"

        exit_code = main(
            [
                "probe-model",
                "--model",
                str(temp_root / "missing.onnx"),
                "--out",
                str(out_dir),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_probe_model_facts_loader_round_trip(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        out_dir = temp_root / "out"
        self._write_sample_onnx(model_path)

        exit_code = main(
            [
                "probe-model",
                "--model",
                str(model_path),
                "--out",
                str(out_dir),
                "--format",
                "both",
            ]
        )

        self.assertEqual(exit_code, 0)
        facts = load_model_facts_json(out_dir / "model_facts.json")
        self.assertEqual(facts.format, "onnx")
        self.assertEqual(facts.inputs[0].dtype, "float32")
        self.assertEqual(facts.outputs[0].shape, [1, 3, 4, 4])


if __name__ == "__main__":
    unittest.main()
