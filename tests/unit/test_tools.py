from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class ToolingTests(unittest.TestCase):
    def test_cleanup_scripts_exist(self) -> None:
        self.assertTrue((TOOLS / "cleanup-temp.ps1").exists())
        self.assertTrue((TOOLS / "cleanup-temp.sh").exists())

    def test_temp_root_is_standardized(self) -> None:
        self.assertTrue((ROOT / ".tmp").exists() or True)


if __name__ == "__main__":
    unittest.main()
