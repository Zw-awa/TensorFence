from __future__ import annotations

import builtins
import unittest
from unittest.mock import patch

from tensorfence.adapters.onnxruntime import OnnxRuntimeAdapterError, _import_onnxruntime


class OnnxRuntimeImportTests(unittest.TestCase):
    def test_import_error_is_wrapped_with_cause(self) -> None:
        original_import = builtins.__import__
        error = ImportError("numpy ABI mismatch")

        def import_module(name, *args, **kwargs):
            if name == "onnxruntime":
                raise error
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_module):
            with self.assertRaises(OnnxRuntimeAdapterError) as caught:
                _import_onnxruntime()

        self.assertIs(caught.exception.__cause__, error)
        self.assertIn(str(error), str(caught.exception))
        self.assertIn("--onnx-out", str(caught.exception))
