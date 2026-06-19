from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.core.contracts import load_contract
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


if __name__ == "__main__":
    unittest.main()

