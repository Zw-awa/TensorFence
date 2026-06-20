from __future__ import annotations

import json
import shutil
import sys
import textwrap
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TMP_ROOT = ROOT / ".tmp" / "tests" / "draft-contract"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.cli import main
from tensorfence.core.contracts import load_contract

try:
    import onnx
    from onnx import TensorProto, helper
except ModuleNotFoundError:
    onnx = None
    TensorProto = None
    helper = None


@unittest.skipIf(onnx is None, "onnx is not installed")
class DraftContractTests(unittest.TestCase):
    def _make_temp_root(self) -> Path:
        path = TMP_ROOT / str(uuid.uuid4())
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def _write_sample_onnx(self, path: Path, output_names: list[str] | None = None) -> None:
        names = output_names or ["output0"]
        input_tensor = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])
        outputs = [
            helper.make_tensor_value_info(name, TensorProto.FLOAT, [1, 8400, 85])
            for name in names
        ]
        nodes = []
        node_input = "images"
        for index, name in enumerate(names):
            node_name = f"identity{index}"
            nodes.append(helper.make_node("Identity", [node_input], [name], name=node_name))
        graph = helper.make_graph(nodes, "draft-sample-graph", [input_tensor], outputs)
        model = helper.make_model(graph, producer_name="tensorfence-test")
        onnx.save_model(model, str(path))

    def _write_rules(self, path: Path, extra: str = "") -> None:
        base = """
        version: 1
        defaults:
          name: "{model_name}-draft"
          source_framework: onnx
          target_runtime: rknn
          task: detection
          family: yolo
        selection:
          input:
            strategy: first
          outputs:
            strategy: all
        mapping:
          input:
            semantic: model_input
            layout_from_rank:
              rank4: NCHW
            dtype_fallback: float32
          outputs:
            semantic: raw_predictions
            layout: N/A
            dtype_fallback: float32
        templates:
          preprocess:
            input_color_space: BGR
            output_color_space: RGB
            input_layout: HWC
            output_layout: NCHW
            resize:
              mode: letterbox
              interpolation: bilinear
              keep_aspect_ratio: true
            normalize:
              scale: 0.00392156862745098
              mean: [0.0, 0.0, 0.0]
              std: [1.0, 1.0, 1.0]
            pad_value: 114
          decode:
            enabled: true
            family: yolo
            mode: anchor_free
            num_classes: 80
            strides: [8, 16, 32]
            score_activation: sigmoid
            box_activation: sigmoid
          nms:
            enabled: true
            score_threshold: 0.25
            iou_threshold: 0.45
          quantization:
            enabled: false
        """
        path.write_text(textwrap.dedent(base).strip() + "\n" + extra, encoding="utf-8")

    def test_draft_contract_from_model_generates_valid_contract(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        self._write_sample_onnx(model_path)
        self._write_rules(rules_path)

        exit_code = main(
            [
                "draft-contract",
                "--model",
                str(model_path),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
                "--report-format",
                "both",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(out_path.exists())
        self.assertTrue((temp_root / "draft_report.json").exists())
        self.assertTrue((temp_root / "draft_report.md").exists())

        contract = load_contract(out_path)
        self.assertEqual(contract.name, "sample-draft")
        self.assertEqual(contract.input.name, "images")
        self.assertEqual(contract.input.shape, [1, 3, 640, 640])
        self.assertEqual(contract.preprocess.resize.target_size, [640, 640])
        self.assertEqual(contract.decode.head_names, ["output0"])

        report = json.loads((temp_root / "draft_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["task"], "detection")
        self.assertTrue(any(item["path"] == "preprocess" for item in report["needs_confirmation"]))

    def test_draft_contract_from_facts_supports_overrides(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        probe_out = temp_root / "probe"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        self._write_sample_onnx(model_path)
        self._write_rules(rules_path)

        probe_exit = main(
            [
                "probe-model",
                "--model",
                str(model_path),
                "--out",
                str(probe_out),
                "--format",
                "json",
            ]
        )
        self.assertEqual(probe_exit, 0)

        exit_code = main(
            [
                "draft-contract",
                "--facts",
                str(probe_out / "model_facts.json"),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
                "--task",
                "detection",
                "--family",
                "yolo",
                "--report-format",
                "json",
            ]
        )

        self.assertEqual(exit_code, 0)
        contract = load_contract(out_path)
        self.assertEqual(contract.task, "detection")
        self.assertEqual(contract.decode.family, "yolo")

    def test_draft_contract_rejects_missing_named_output(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        self._write_sample_onnx(model_path, output_names=["head0"])
        self._write_rules(
            rules_path,
            extra=textwrap.dedent(
                """
                selection:
                  input:
                    strategy: first
                  outputs:
                    strategy: by_name
                    names: [head1]
                """
            ),
        )

        exit_code = main(
            [
                "draft-contract",
                "--model",
                str(model_path),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_draft_contract_rejects_existing_output_without_force(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        self._write_sample_onnx(model_path)
        self._write_rules(rules_path)
        out_path.write_text("occupied\n", encoding="utf-8")

        exit_code = main(
            [
                "draft-contract",
                "--model",
                str(model_path),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_draft_contract_can_write_reports_to_custom_directory(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        report_dir = temp_root / "reports"
        self._write_sample_onnx(model_path)
        self._write_rules(rules_path)

        exit_code = main(
            [
                "draft-contract",
                "--model",
                str(model_path),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
                "--report-out",
                str(report_dir),
                "--report-format",
                "both",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((report_dir / "draft_report.json").exists())
        self.assertTrue((report_dir / "draft_report.md").exists())

    def test_draft_contract_prefers_facts_when_both_inputs_are_given(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        probe_out = temp_root / "probe"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        self._write_sample_onnx(model_path)
        self._write_rules(rules_path)

        probe_exit = main(
            [
                "probe-model",
                "--model",
                str(model_path),
                "--out",
                str(probe_out),
                "--format",
                "json",
            ]
        )
        self.assertEqual(probe_exit, 0)

        exit_code = main(
            [
                "draft-contract",
                "--facts",
                str(probe_out / "model_facts.json"),
                "--model",
                str(temp_root / "missing.onnx"),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
                "--report-format",
                "json",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(out_path.exists())

    def test_draft_contract_rejects_invalid_facts_json(self) -> None:
        temp_root = self._make_temp_root()
        facts_path = temp_root / "bad_facts.json"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        facts_path.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
        self._write_rules(rules_path)

        exit_code = main(
            [
                "draft-contract",
                "--facts",
                str(facts_path),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
            ]
        )

        self.assertEqual(exit_code, 2)

    def test_draft_contract_force_overwrites_existing_output(self) -> None:
        temp_root = self._make_temp_root()
        model_path = temp_root / "sample.onnx"
        rules_path = temp_root / "rules.yaml"
        out_path = temp_root / "draft.contract.yaml"
        self._write_sample_onnx(model_path)
        self._write_rules(rules_path)
        out_path.write_text("occupied\n", encoding="utf-8")

        exit_code = main(
            [
                "draft-contract",
                "--model",
                str(model_path),
                "--rules",
                str(rules_path),
                "--out",
                str(out_path),
                "--force",
            ]
        )

        self.assertEqual(exit_code, 0)
        contract = load_contract(out_path)
        self.assertEqual(contract.name, "sample-draft")


if __name__ == "__main__":
    unittest.main()
