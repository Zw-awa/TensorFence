from __future__ import annotations

import tempfile
import shlex
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from tensorfence.environment.config import load_targets, save_target
from tensorfence.environment.discovery import discover_target, evaluate_compatibility
from tensorfence.environment.models import EnvironmentFacts, Fact, TargetProfile
from tensorfence.environment.plugins import discover_plugins
from tensorfence.environment.transports import CommandResult, SshTransport, TargetTransport


class FakeTransport(TargetTransport):
    def run(self, command: list[str], timeout: int = 15) -> CommandResult:
        joined = " ".join(command)
        values = {
            "uname -s": "Linux",
            "uname -m": "x86_64",
            "--version": "Python 3.10.12" if "python" in joined else "conda 24.11.0",
            "rknn-toolkit2": "2.3.2",
        }
        for needle, output in values.items():
            if needle in joined:
                return CommandResult(command, 0, output, "")
        return CommandResult(command, 1, "", "not found")


class EnvironmentTests(unittest.TestCase):
    def test_ssh_preserves_remote_command_arguments(self) -> None:
        target = TargetProfile(
            name="board", transport="ssh", connection={"host": "board", "user": "tester"}
        )
        commands = [
            ["python", "--version"],
            ["/opt/my env/bin/python", "-c", "print('hello world')", "$(echo unsafe)", "a;b", ""],
        ]
        for command in commands:
            with self.subTest(command=command):
                with patch("tensorfence.environment.transports.subprocess.run") as run:
                    run.return_value = subprocess.CompletedProcess([], 0, "ok\n", "")
                    result = SshTransport(target).run(command, input_text="payload", timeout=7)
                invocation = run.call_args.args[0]
                self.assertEqual(invocation[:4], ["ssh", "-p", "22", "tester@board"])
                remote_shell = shlex.split(" ".join(invocation[4:]))
                self.assertEqual(remote_shell[:2], ["sh", "-lc"])
                self.assertEqual(len(remote_shell), 3)
                self.assertEqual(shlex.split(remote_shell[2]), ["exec", *command])
                self.assertEqual(run.call_args.kwargs["input"], "payload")
                self.assertEqual(run.call_args.kwargs["timeout"], 7)
                self.assertEqual(result.stdout, "ok")

    def test_project_targets_override_global_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            global_path = root / "global" / "targets.yaml"
            with patch("tensorfence.environment.config.user_config_path", return_value=global_path):
                save_target(TargetProfile(name="shared", transport="local"))
                save_target(TargetProfile(name="shared", transport="wsl", connection={"wsl_distro": "Ubuntu"}), root)
                save_target(TargetProfile(name="board", transport="local"), root)
                targets = load_targets(root)
        self.assertEqual(targets["shared"].transport, "wsl")
        self.assertIn("board", targets)

    def test_builtin_plugin_is_discoverable(self) -> None:
        plugins, errors = discover_plugins()
        self.assertEqual(errors, [])
        self.assertIn("tensorfence.core", plugins)
        self.assertEqual(plugins["tensorfence.core"].actions[0].id, "doctor")

    def test_rknn_host_facts_evaluate_version_policy(self) -> None:
        target = TargetProfile(
            name="host",
            profile="rknn-host",
            transport="wsl",
            connection={"wsl_distro": "Ubuntu", "python": "python", "conda_path": "conda", "conda_env": "rknn"},
            version_policy={"python": ">=3.10", "rknn_toolkit": ">=2.3.2,<2.4"},
        )
        facts = evaluate_compatibility(discover_target(target, FakeTransport(target)))
        self.assertEqual(facts.overall_status(), "ready")
        self.assertEqual(next(item for item in facts.facts if item.key == "rknn_toolkit").value, "2.3.2")

    def test_incompatible_policy_is_blocked(self) -> None:
        target = TargetProfile(name="host", transport="local", version_policy={"python": ">=3.12"})
        facts = EnvironmentFacts(target=target, facts=[Fact(key="python", status="ready", value="Python 3.10.12")])
        checked = evaluate_compatibility(facts)
        self.assertEqual(checked.overall_status(), "blocked")


if __name__ == "__main__":
    unittest.main()
