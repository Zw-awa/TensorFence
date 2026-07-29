from __future__ import annotations

import json
import shutil
import sys
import textwrap
import unittest
import uuid
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TMP_ROOT = ROOT / ".tmp" / "tests" / "integration-mvp"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.artifacts import write_tensor_artifact
from tensorfence.cli import main

try:
    import onnx
    import onnxruntime
    from onnx import TensorProto, helper
except ModuleNotFoundError:
    onnx = None
    onnxruntime = None
    TensorProto = None
    helper = None


@unittest.skipIf(onnx is None or onnxruntime is None, "onnx and onnxruntime are required")
class CliMvpFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = TMP_ROOT / str(uuid.uuid4())
        self.root.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

        self.model_path = self.root / "identity.onnx"
        self.image_path = self.root / "frame.png"
        self.rules_path = self.root / "rules.yaml"
        self.contract_path = self.root / "contract.yaml"
        self._write_model()
        Image.fromarray(np.full((4, 4, 3), 64, dtype=np.uint8), mode="RGB").save(self.image_path)
        self._write_rules()

    def _write_model(self) -> None:
        input_info = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 4, 4])
        output_info = helper.make_tensor_value_info("output0", TensorProto.FLOAT, [1, 3, 4, 4])
        graph = helper.make_graph(
            [helper.make_node("Identity", ["images"], ["output0"], name="identity")],
            "tensorfence-integration",
            [input_info],
            [output_info],
        )
        model = helper.make_model(
            graph,
            producer_name="tensorfence-integration",
            opset_imports=[helper.make_opsetid("", 13)],
        )
        model.ir_version = 8
        onnx.save_model(model, str(self.model_path))

    def _write_rules(self) -> None:
        self.rules_path.write_text(
            textwrap.dedent(
                """
                version: 1
                defaults:
                  name: "{model_name}-integration"
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
                    input_color_space: RGB
                    output_color_space: RGB
                    input_layout: HWC
                    output_layout: NCHW
                    resize:
                      mode: stretch
                      interpolation: nearest
                      keep_aspect_ratio: false
                    normalize:
                      scale: 0.00392156862745098
                      mean: [0.0, 0.0, 0.0]
                      std: [1.0, 1.0, 1.0]
                    pad_value: 0
                  decode:
                    enabled: true
                    family: yolo
                    mode: anchor_free
                    num_classes: 1
                    strides: [8]
                    score_activation: sigmoid
                    box_activation: sigmoid
                  nms:
                    enabled: true
                    score_threshold: 0.25
                    iou_threshold: 0.45
                  quantization:
                    enabled: false
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    def _build_contract(self) -> None:
        probe_dir = self.root / "probe"
        self.assertEqual(
            main(["probe-model", "--model", str(self.model_path), "--out", str(probe_dir), "--format", "both"]),
            0,
        )
        self.assertEqual(
            main(
                [
                    "draft-contract",
                    "--facts",
                    str(probe_dir / "model_facts.json"),
                    "--rules",
                    str(self.rules_path),
                    "--out",
                    str(self.contract_path),
                    "--report-format",
                    "both",
                ]
            ),
            0,
        )
        self.assertEqual(main(["check-contract", str(self.contract_path)]), 0)
        self.assertTrue((probe_dir / "graph_summary.md").exists())
        self.assertTrue((self.root / "draft_report.json").exists())

    def test_probe_contract_and_real_onnx_compare_are_aligned(self) -> None:
        self._build_contract()
        framework_path = self.root / "framework.npz"
        expected = np.full((1, 3, 4, 4), 64 / 255, dtype=np.float32)
        write_tensor_artifact(
            framework_path,
            {"output0": expected},
            stage="framework",
            source="integration-reference",
            provenance={"model_path": str(self.model_path), "input_path": str(self.image_path)},
        )
        out_dir = self.root / "aligned"

        exit_code = main(
            [
                "compare-stages",
                "--contract",
                str(self.contract_path),
                "--image",
                str(self.image_path),
                "--framework-out",
                str(framework_path),
                "--onnx",
                str(self.model_path),
                "--out",
                str(out_dir),
                "--report-format",
                "html",
            ]
        )

        self.assertEqual(exit_code, 0)
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["schema_version"], "tensorfence.stage-report/v1")
        self.assertFalse(report["final_summary"]["drift_detected"])
        self.assertEqual(report["pair_diffs"][0]["status"], "aligned")
        self.assertTrue((out_dir / "report.html").exists())

    def test_drift_zero_collapse_and_mapping_policy(self) -> None:
        self._build_contract()
        reference_path = self.root / "reference.npz"
        drift_path = self.root / "drift.npz"
        tiny_path = self.root / "tiny.npz"
        zero_path = self.root / "zero.npz"
        reference = np.linspace(0.1, 1.0, 48, dtype=np.float32).reshape(1, 3, 4, 4)
        write_tensor_artifact(reference_path, {"output0": reference}, stage="framework", source="test")
        write_tensor_artifact(drift_path, {"output0": reference + 0.1}, stage="rknn", source="test")
        write_tensor_artifact(
            tiny_path,
            {"output0": np.full_like(reference, 1e-7)},
            stage="framework",
            source="test",
        )
        write_tensor_artifact(zero_path, {"output0": np.zeros_like(reference)}, stage="rknn", source="test")

        drift_out = self.root / "drift-report"
        self.assertEqual(
            main(
                [
                    "compare-stages",
                    "--contract",
                    str(self.contract_path),
                    "--image",
                    str(self.image_path),
                    "--framework-out",
                    str(reference_path),
                    "--rknn-out",
                    str(drift_path),
                    "--out",
                    str(drift_out),
                ]
            ),
            0,
        )
        drift = json.loads((drift_out / "tensor_diffs.json").read_text(encoding="utf-8"))[0]
        self.assertEqual(drift["status"], "drift")

        collapse_out = self.root / "collapse-report"
        self.assertEqual(
            main(
                [
                    "compare-stages",
                    "--contract",
                    str(self.contract_path),
                    "--image",
                    str(self.image_path),
                    "--framework-out",
                    str(tiny_path),
                    "--rknn-out",
                    str(zero_path),
                    "--out",
                    str(collapse_out),
                ]
            ),
            0,
        )
        collapse = json.loads((collapse_out / "tensor_diffs.json").read_text(encoding="utf-8"))[0]
        self.assertEqual(collapse["small_value_zero_fraction"], 1.0)
        self.assertTrue(any("quantization under-resolution" in reason for reason in collapse["reasons"]))

        wrong_framework = self.root / "wrong-framework.npz"
        wrong_rknn = self.root / "wrong-rknn.npz"
        np.savez(wrong_framework, tensor_a=reference)
        np.savez(wrong_rknn, tensor_b=reference)
        common = [
            "compare-stages",
            "--contract",
            str(self.contract_path),
            "--image",
            str(self.image_path),
            "--framework-out",
            str(wrong_framework),
            "--rknn-out",
            str(wrong_rknn),
            "--out",
            str(self.root / "mapping-report"),
        ]
        self.assertEqual(main(common), 2)
        self.assertEqual(main([*common, "--map-by-order"]), 0)


if __name__ == "__main__":
    unittest.main()
