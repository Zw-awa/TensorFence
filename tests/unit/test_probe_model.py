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
        self.assertTrue(any("duplicate postprocessing" in warning for warning in facts["warnings"]))
        self.assertEqual(summary["warnings"], facts["warnings"])
        self.assertIn("embedded postprocess detected", markdown)

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
