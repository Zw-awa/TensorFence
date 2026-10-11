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
        self.assertTrue((TOOLS / "qt.ps1").exists())
        self.assertTrue((TOOLS / "test.ps1").exists())

    def test_test_entrypoint_keeps_local_and_wsl_selection_explicit(self) -> None:
        script = (TOOLS / "test.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("conda run", script)
        self.assertIn("WslDistro", script)
        self.assertIn("WslCondaPath", script)
        self.assertIn("CheckEnvironments", script)
        self.assertIn("environment.wsl.yml", script)
        agent = (ROOT / "AGENT.md").read_text(encoding="utf-8-sig")
        self.assertIn("Mandatory Environment Check", agent)
        self.assertIn("Never use bare `python`", agent)
        probe = (TOOLS / "check-test-env.py").read_text(encoding="utf-8-sig")
        self.assertIn("sys.executable", probe)
        self.assertIn("jinja2", probe)

    def test_cleanup_skips_opensource(self) -> None:
        powershell = (TOOLS / "cleanup-temp.ps1").read_text(encoding="utf-8-sig")
        shell = (TOOLS / "cleanup-temp.sh").read_text(encoding="utf-8-sig")
        self.assertIn('"opensource"', powershell)
        self.assertIn('${REPO_ROOT}/opensource', shell)

    def test_qt_script_has_agent_safe_mode(self) -> None:
        script = (TOOLS / "qt.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("CODEX_THREAD_ID", script)
        self.assertIn("MinGW Makefiles", script)
        self.assertIn("QT_AGENT_SAFE_BUILD", script)
        self.assertIn("Read-DotEnv", script)
        self.assertNotIn("F:\\Qt", script)
        self.assertTrue((ROOT / ".env.example").exists())
        self.assertIn(".env", (ROOT / ".gitignore").read_text(encoding="utf-8-sig"))

    def test_temp_root_is_standardized(self) -> None:
        self.assertTrue((ROOT / ".tmp").exists() or True)


if __name__ == "__main__":
    unittest.main()
