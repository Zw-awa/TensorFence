from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from tensorfence.environment.host import ExecutionContext, PluginHost
from tensorfence.environment.models import PluginAction, PluginManifest, TargetProfile


class PluginHostTests(unittest.TestCase):
    def test_builtin_python_handler_returns_standard_envelope(self) -> None:
        plugin = PluginManifest(
            id="example.builtin",
            name="Example",
            version="1.0.0",
            runtime="builtin-python",
            actions=[PluginAction(id="inspect", description="inspect", command=["unused"], output_kind="facts")],
        )
        host = PluginHost({plugin.id: plugin})
        host.register(plugin.id, "inspect", lambda context: {"facts": [{"key": "ok", "status": "ready"}]})
        result = host.execute(TargetProfile(name="local"), plugin.id, "inspect")
        envelope = result.envelope()
        self.assertEqual(envelope["status"], "ready")
        self.assertEqual(envelope["facts"][0]["key"], "ok")
        self.assertEqual(envelope["provenance"]["plugin_version"], "1.0.0")

    def test_external_json_plugin_receives_protocol_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "plugin.py"
            script.write_text(
                "import json, sys\n"
                "request = json.loads(sys.stdin.readline())\n"
                "print(json.dumps({'facts': [{'key': 'input', 'status': 'ready', 'value': request['inputs']['name']}] }))\n",
                encoding="utf-8",
            )
            plugin = PluginManifest(
                id="example.external",
                name="Example",
                version="1.0.0",
                actions=[
                    PluginAction(
                        id="inspect",
                        description="inspect",
                        command=[sys.executable, str(script)],
                        input_schema={"name": {"type": "string", "required": True}},
                        output_kind="facts",
                    )
                ],
            )
            result = PluginHost({plugin.id: plugin}).execute(TargetProfile(name="local"), plugin.id, "inspect", input_args=["name=demo"])
            envelope = result.envelope()
            self.assertEqual(result.returncode, 0)
            self.assertEqual(envelope["result"]["facts"][0]["value"], "demo")
            self.assertEqual(envelope["result"]["facts"][0]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
