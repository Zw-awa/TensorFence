from __future__ import annotations

import builtins
import unittest
from unittest.mock import patch

import numpy as np

from tensorfence.adapters.rknn import RknnAdapterError, run_rknn_model


class RknnImportTests(unittest.TestCase):
    def test_import_failures_preserve_cause_and_offer_environment_guidance(self) -> None:
        original_import = builtins.__import__
        for error in (
            ModuleNotFoundError("No module named 'rknn'"),
            ImportError("cannot import name 'runtime_version' from 'google.protobuf'"),
        ):
            with self.subTest(error=str(error)):
                def import_module(name, *args, **kwargs):
                    if name == "rknn.api":
                        raise error
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=import_module):
                    with self.assertRaises(RknnAdapterError) as caught:
                        run_rknn_model(
                            "unused.rknn",
                            input_tensor=np.zeros((1, 3, 4, 4), dtype=np.float32),
                            expected_names=["output0"],
                        )
                self.assertIs(caught.exception.__cause__, error)
                self.assertIn(str(error), str(caught.exception))
                self.assertIn("tensorfence rknn-run", str(caught.exception))
