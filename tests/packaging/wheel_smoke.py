from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tensorfence", *args],
        cwd=cwd,
        check=True,
        text=True,
    )


def main() -> None:
    if int(np.__version__.split(".", maxsplit=1)[0]) >= 2:
        raise AssertionError(f"wheel resolved unsupported NumPy {np.__version__}")

    with tempfile.TemporaryDirectory(prefix="tensorfence-wheel-smoke-") as temp_dir:
        root = Path(temp_dir)
        contract = root / "contract.yaml"
        image = root / "sample.png"
        inspection_output = root / "inspection-report"
        comparison_output = root / "comparison-report"
        framework_output = root / "framework.npz"
        onnx_output = root / "onnx.npz"

        run("init", str(contract), cwd=root)
        Image.new("RGB", (32, 24), color=(64, 96, 128)).save(image)
        run(
            "inspect-image",
            "--contract",
            str(contract),
            "--image",
            str(image),
            "--out",
            str(inspection_output),
            "--report-format",
            "html",
            cwd=root,
        )

        inspection_report = inspection_output / "report.html"
        if not inspection_report.is_file():
            raise AssertionError("installed wheel did not generate the inspection HTML report")
        if "Inspection Report" not in inspection_report.read_text(encoding="utf-8"):
            raise AssertionError("generated HTML does not contain the inspection report")

        values = np.zeros((1, 8400, 85), dtype=np.float32)
        np.savez(framework_output, output0=values)
        np.savez(onnx_output, output0=values)
        run(
            "compare-stages",
            "--contract",
            str(contract),
            "--image",
            str(image),
            "--framework-out",
            str(framework_output),
            "--onnx-out",
            str(onnx_output),
            "--out",
            str(comparison_output),
            "--report-format",
            "html",
            cwd=root,
        )
        comparison_report = comparison_output / "report.html"
        if not comparison_report.is_file():
            raise AssertionError("installed wheel did not generate the stage comparison HTML report")
        if "Stage Compare Report" not in comparison_report.read_text(encoding="utf-8"):
            raise AssertionError("generated HTML does not contain the stage comparison report")


if __name__ == "__main__":
    main()
