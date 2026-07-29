from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TMP_ROOT = ROOT / ".tmp" / "tests" / "tensor-artifact"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.adapters._npz import NpzAdapterError, load_npz_outputs
from tensorfence.artifacts.tensor_artifact import (
    TENSOR_ARTIFACT_MANIFEST_KEY,
    TENSOR_ARTIFACT_SCHEMA_VERSION,
    TensorArtifactError,
    load_tensor_artifact,
    write_tensor_artifact,
)
from tensorfence.cli import main


class TensorArtifactTests(unittest.TestCase):
    def _make_temp_root(self) -> Path:
        path = TMP_ROOT / str(uuid.uuid4())
        path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_canonical_artifact_round_trip_includes_manifest(self) -> None:
        temp_root = self._make_temp_root()
        target = temp_root / "rknn.npz"
        output0 = np.asarray([[-128, -3, 127]], dtype=np.int8)

        write_tensor_artifact(
            target,
            {"output0": output0},
            stage="rknn",
            source="rknn-runtime 2.3.2",
            provenance={"model_path": "best.rknn", "device": "RK3588"},
            quantization={
                "output0": {
                    "scale": 0.02265625,
                    "zero_point": -128,
                    "qmin": -128,
                    "qmax": 127,
                    "scheme": "asymmetric",
                }
            },
        )

        with np.load(target, allow_pickle=False) as raw:
            self.assertIn(TENSOR_ARTIFACT_MANIFEST_KEY, raw.files)
            self.assertIn("output0", raw.files)
        artifact = load_tensor_artifact(target, allow_legacy=False)
        self.assertTrue(artifact.is_canonical)
        np.testing.assert_array_equal(artifact.tensors["output0"], output0)
        assert artifact.manifest is not None
        self.assertEqual(artifact.manifest.schema_version, TENSOR_ARTIFACT_SCHEMA_VERSION)
        self.assertEqual(artifact.manifest.stage, "rknn")
        self.assertEqual(artifact.manifest.source, "rknn-runtime 2.3.2")
        self.assertEqual(artifact.manifest.provenance["model_path"], "best.rknn")
        self.assertIn("created_at_utc", artifact.manifest.provenance)
        tensor = artifact.manifest.tensors[0]
        self.assertEqual(tensor.name, "output0")
        self.assertEqual(tensor.dtype, "int8")
        self.assertEqual(tensor.shape, [1, 3])
        assert tensor.quantization is not None
        self.assertEqual(tensor.quantization.scale, 0.02265625)
        self.assertEqual(tensor.quantization.zero_point, -128)

    def test_adapter_ignores_manifest_key(self) -> None:
        temp_root = self._make_temp_root()
        target = temp_root / "framework.npz"
        output = np.ones((1, 2), dtype=np.float32)
        write_tensor_artifact(
            target,
            {"scores": output},
            stage="framework",
            source="pytorch",
        )

        outputs, warnings = load_npz_outputs(target, ["scores"])

        self.assertEqual(warnings, [])
        self.assertEqual(list(outputs), ["scores"])
        np.testing.assert_array_equal(outputs["scores"], output)

    def test_adapter_rejects_canonical_stage_mismatch(self) -> None:
        temp_root = self._make_temp_root()
        target = temp_root / "rknn.npz"
        write_tensor_artifact(
            target,
            {"output0": np.ones((1, 2), dtype=np.float32)},
            stage="rknn",
            source="rknn-runtime",
        )

        with self.assertRaisesRegex(NpzAdapterError, "does not match expected stage"):
            load_npz_outputs(target, ["output0"], expected_stage="framework")

    def test_legacy_npz_remains_readable(self) -> None:
        temp_root = self._make_temp_root()
        target = temp_root / "legacy.npz"
        output = np.arange(4, dtype=np.float32)
        np.savez(target, output0=output)

        artifact = load_tensor_artifact(target)

        self.assertFalse(artifact.is_canonical)
        self.assertIsNone(artifact.manifest)
        np.testing.assert_array_equal(artifact.tensors["output0"], output)
        with self.assertRaisesRegex(TensorArtifactError, "legacy npz artifact"):
            load_tensor_artifact(target, allow_legacy=False)

    def test_manifest_must_match_array_dtype_and_shape(self) -> None:
        temp_root = self._make_temp_root()
        target = temp_root / "invalid.npz"
        manifest = {
            "schema_version": TENSOR_ARTIFACT_SCHEMA_VERSION,
            "stage": "onnx",
            "source": "onnxruntime",
            "tensors": [{"name": "output0", "dtype": "float16", "shape": [1, 4]}],
            "provenance": {},
        }
        np.savez(
            target,
            **{
                TENSOR_ARTIFACT_MANIFEST_KEY: np.asarray(json.dumps(manifest)),
                "output0": np.zeros((1, 4), dtype=np.float32),
            },
        )

        with self.assertRaisesRegex(TensorArtifactError, "does not match array"):
            load_tensor_artifact(target)

    def test_per_channel_quantization_requires_axis(self) -> None:
        temp_root = self._make_temp_root()
        with self.assertRaisesRegex(TensorArtifactError, "requires axis"):
            write_tensor_artifact(
                temp_root / "invalid.npz",
                {"output0": np.zeros((1, 2), dtype=np.int8)},
                stage="rknn",
                source="rknn-runtime",
                quantization={"output0": {"scale": [0.1, 0.2], "zero_point": [0, 0]}},
            )

    def test_per_channel_zero_points_also_require_axis(self) -> None:
        temp_root = self._make_temp_root()
        with self.assertRaisesRegex(TensorArtifactError, "requires axis"):
            write_tensor_artifact(
                temp_root / "invalid.npz",
                {"output0": np.zeros((1, 2), dtype=np.int8)},
                stage="rknn",
                source="rknn-runtime",
                quantization={"output0": {"scale": 0.1, "zero_point": [0, 1]}},
            )

    def test_artifact_rejects_non_real_tensor_dtype(self) -> None:
        temp_root = self._make_temp_root()
        with self.assertRaisesRegex(TensorArtifactError, "unsupported non-real dtype"):
            write_tensor_artifact(
                temp_root / "invalid.npz",
                {"output0": np.asarray(["not-a-tensor"])},
                stage="framework",
                source="test",
            )

    def test_quantization_metadata_requires_integer_tensor(self) -> None:
        temp_root = self._make_temp_root()
        with self.assertRaisesRegex(TensorArtifactError, "requires an integer tensor dtype"):
            write_tensor_artifact(
                temp_root / "invalid.npz",
                {"output0": np.zeros((1, 2), dtype=np.float32)},
                stage="rknn",
                source="test",
                quantization={"output0": {"scale": 0.1, "zero_point": 0}},
            )

    def test_quantization_effective_range_must_not_be_empty(self) -> None:
        temp_root = self._make_temp_root()
        with self.assertRaisesRegex(TensorArtifactError, "qmin must be less than qmax"):
            write_tensor_artifact(
                temp_root / "invalid.npz",
                {"output0": np.zeros((1, 2), dtype=np.int8)},
                stage="rknn",
                source="test",
                quantization={"output0": {"scale": 0.1, "zero_point": 127, "qmin": 127}},
            )

    def test_dump_tensors_cli_packs_npy_arrays_and_metadata(self) -> None:
        temp_root = self._make_temp_root()
        boxes_path = temp_root / "boxes.npy"
        scores_path = temp_root / "scores.npy"
        target = temp_root / "framework.npz"
        provenance_path = temp_root / "provenance.json"
        np.save(boxes_path, np.zeros((1, 10, 4), dtype=np.float32))
        np.save(scores_path, np.ones((1, 3, 10), dtype=np.float32))
        provenance_path.write_text(
            json.dumps({"model_path": "best.pt", "input_path": "frame.jpg"}),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "dump-tensors",
                "--stage",
                "framework",
                "--source",
                "pytorch 2.7",
                "--tensor",
                f"boxes={boxes_path}",
                "--tensor",
                f"scores={scores_path}",
                "--provenance-json",
                str(provenance_path),
                "--out",
                str(target),
            ]
        )

        self.assertEqual(exit_code, 0)
        artifact = load_tensor_artifact(target, allow_legacy=False)
        self.assertEqual(list(artifact.tensors), ["boxes", "scores"])
        assert artifact.manifest is not None
        self.assertEqual(artifact.manifest.provenance["input_path"], "frame.jpg")

    def test_dump_tensors_cli_rejects_ambiguous_tensor_specification(self) -> None:
        temp_root = self._make_temp_root()
        exit_code = main(
            [
                "dump-tensors",
                "--stage",
                "rknn",
                "--source",
                "rknn-runtime",
                "--tensor",
                "output.npy",
                "--out",
                str(temp_root / "out.npz"),
            ]
        )
        self.assertEqual(exit_code, 2)

    def test_dump_tensors_cli_rejects_invalid_quantization_object(self) -> None:
        temp_root = self._make_temp_root()
        tensor_path = temp_root / "output.npy"
        quantization_path = temp_root / "quantization.json"
        np.save(tensor_path, np.zeros((1, 2), dtype=np.int8))
        quantization_path.write_text(json.dumps({"output0": 0.1}), encoding="utf-8")

        exit_code = main(
            [
                "dump-tensors",
                "--stage",
                "rknn",
                "--source",
                "rknn-runtime",
                "--tensor",
                f"output0={tensor_path}",
                "--quantization-json",
                str(quantization_path),
                "--out",
                str(temp_root / "out.npz"),
            ]
        )

        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
