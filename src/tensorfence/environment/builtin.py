from __future__ import annotations

import os
import platform
import sys
from importlib.util import find_spec
from typing import Any

from .host import ExecutionContext, PluginHost
from .models import Fact


def _module_status(module_name: str) -> str:
    return "ready" if find_spec(module_name) is not None else "unknown"


def core_doctor(context: ExecutionContext) -> dict[str, Any]:
    facts = [
        Fact(key="python", status="ready", value=platform.python_version(), evidence=sys.executable),
        Fact(key="platform", status="ready", value=platform.platform()),
        Fact(key="conda", status="ready" if os.environ.get("CONDA_PREFIX") else "unknown", value=os.environ.get("CONDA_PREFIX")),
    ]
    for module in ("numpy", "pydantic", "yaml", "onnx", "onnxruntime", "jinja2"):
        facts.append(Fact(key=f"module.{module}", status=_module_status(module), value=module))
    status = "warning" if any(item.status == "unknown" for item in facts) else "ready"
    return {"status": status, "facts": [item.model_dump(mode="json") for item in facts]}


def register_builtin_handlers(host: PluginHost) -> PluginHost:
    host.register("tensorfence.core", "doctor", core_doctor)
    return host
