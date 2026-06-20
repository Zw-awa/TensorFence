from __future__ import annotations

from pathlib import Path

import numpy as np

from .._npz import NpzAdapterError, load_npz_outputs


class OnnxRuntimeAdapterError(RuntimeError):
    pass


def _import_onnxruntime():
    try:
        import onnxruntime as ort
    except ModuleNotFoundError as exc:
        raise OnnxRuntimeAdapterError(
            "onnxruntime is not installed. Install the tensorfence environment update or provide --onnx-out."
        ) from exc
    return ort


def load_onnx_outputs(path: str | Path, expected_names: list[str]) -> tuple[dict[str, np.ndarray], list[str]]:
    try:
        return load_npz_outputs(path, expected_names)
    except NpzAdapterError as exc:
        raise OnnxRuntimeAdapterError(str(exc)) from exc


def run_onnx_model(model_path: str | Path, input_tensor: np.ndarray) -> tuple[dict[str, np.ndarray], list[str]]:
    ort = _import_onnxruntime()
    model_file = Path(model_path)
    if not model_file.exists():
        raise OnnxRuntimeAdapterError(f"onnx model does not exist: {model_file}")

    try:
        session = ort.InferenceSession(str(model_file), providers=["CPUExecutionProvider"])
    except Exception as exc:  # pragma: no cover - onnxruntime exception types vary across versions
        raise OnnxRuntimeAdapterError(f"failed to create onnxruntime session: {model_file}") from exc

    inputs = session.get_inputs()
    if len(inputs) != 1:
        raise OnnxRuntimeAdapterError(
            f"compare-stages v1 only supports single-input ONNX models, got {len(inputs)} inputs"
        )

    input_name = inputs[0].name
    output_names = [item.name for item in session.get_outputs()]
    try:
        output_values = session.run(None, {input_name: np.asarray(input_tensor)})
    except Exception as exc:  # pragma: no cover - onnxruntime exception types vary across versions
        raise OnnxRuntimeAdapterError(f"failed to run ONNX model: {model_file}") from exc

    outputs = {name: np.asarray(value) for name, value in zip(output_names, output_values, strict=True)}
    return outputs, []
