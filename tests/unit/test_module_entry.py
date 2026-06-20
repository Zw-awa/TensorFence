from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ModuleEntryTests(unittest.TestCase):
    def test_python_module_entry_runs_with_pythonpath(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tensorfence",
                "doctor",
            ],
            cwd=str(ROOT),
            env={
                **__import__("os").environ,
                "PYTHONPATH": str(ROOT / "src"),
            },
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("TensorFence", result.stdout)

    def test_python_module_entry_exposes_inspect_image_help(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "tensorfence",
                "inspect-image",
                "--help",
            ],
            cwd=str(ROOT),
            env={
                **__import__("os").environ,
                "PYTHONPATH": str(ROOT / "src"),
            },
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("usage: tensorfence inspect-image", result.stdout)
        self.assertIn("--contract", result.stdout)
        self.assertIn("--report-format", result.stdout)


if __name__ == "__main__":
    unittest.main()
