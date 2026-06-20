from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tensorfence.cli import main


class DoctorCommandTests(unittest.TestCase):
    def test_doctor_prints_dependency_and_command_summary(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["doctor"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("TensorFence", output)
        self.assertIn("onnx:", output)
        self.assertIn("jinja2:", output)
        self.assertIn("Available commands:", output)


if __name__ == "__main__":
    unittest.main()
