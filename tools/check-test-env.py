from __future__ import annotations

import importlib.util
import sys


required = ("jinja2", "onnxruntime", "pytest")
missing = [name for name in required if importlib.util.find_spec(name) is None]
print(f"Python: {sys.executable}")
print(f"Missing dependencies: {', '.join(missing) if missing else 'none'}")
raise SystemExit(bool(missing))
