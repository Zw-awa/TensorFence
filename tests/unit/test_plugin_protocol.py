from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tensorfence.environment.config import load_plugin_states, save_plugin_state
from tensorfence.environment.models import PluginAction, PluginManifest
from tensorfence.environment.plugins import manifest_hash


class PluginProtocolTests(unittest.TestCase):
    def test_manifest_supports_capabilities_and_action_contract(self) -> None:
        manifest = PluginManifest(
            id="example.plugin",
            name="Example",
            version="1.0.0",
            capabilities=["probe"],
            actions=[PluginAction(id="run", description="run", command=["tool"], input_schema={"model": {"type": "string", "required": True}}, output_kind="artifact")],
        )
        self.assertEqual(manifest.actions[0].output_kind, "artifact")
        self.assertTrue(manifest.default_enabled)
        self.assertEqual(len(manifest_hash(manifest)), 64)

    def test_project_plugin_state_overrides_global(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            global_path = root / "global" / "targets.yaml"
            with patch("tensorfence.environment.config.user_config_path", return_value=global_path):
                save_plugin_state("example.plugin", True)
                save_plugin_state("example.plugin", False, root)
                self.assertEqual(load_plugin_states(root)["example.plugin"], False)


if __name__ == "__main__":
    unittest.main()
