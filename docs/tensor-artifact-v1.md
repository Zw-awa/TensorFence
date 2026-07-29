# Tensor Artifact v1

TensorFence stage comparison uses one canonical, artifact-first interchange format. Framework and RKNN execution may
happen in another process, machine, WSL distribution, or board environment; TensorFence only needs the captured arrays
and their explicit metadata.

## Container

The file is a NumPy `.npz` archive. Every tensor is stored under its contract output name. A reserved scalar string named
`__tensorfence_manifest__` contains the UTF-8 JSON manifest.

The v1 manifest has this shape:

```json
{
  "schema_version": "tensorfence.tensor-artifact/v1",
  "stage": "rknn",
  "source": "rknn-runtime 2.3.2",
  "tensors": [
    {
      "name": "output0",
      "dtype": "int8",
      "shape": [1, 5, 8400],
      "quantization": {
        "scale": 0.02265625,
        "zero_point": -128,
        "qmin": -128,
        "qmax": 127,
        "scheme": "asymmetric"
      }
    }
  ],
  "provenance": {
    "created_at_utc": "2026-07-29T08:00:00+00:00",
    "producer": "tensorfence 0.1.0",
    "model_path": "best.rknn",
    "runtime_version": "2.3.2",
    "device": "RK3588",
    "input_path": "frame.jpg"
  }
}
```

`schema_version`, `stage`, `source`, `tensors`, and `provenance` are required. Tensor `name`, `dtype`, and `shape` must
match the array stored in the archive. Quantization metadata is optional for floating tensors, but required when a raw
integer tensor will be compared. It supports scalar or per-channel `scale` and `zero_point`; per-channel values require
`axis`.

Provenance is open JSON data so a producer can record the model hash/path, runtime and toolkit versions, device, input
identity, command, and relevant environment facts. TensorFence adds `created_at_utc` and `producer` when it writes the
file. Do not place secrets or large binary data in provenance.

## Capture Workflow

If framework or board code can import TensorFence, write the outputs directly:

```python
from tensorfence.artifacts import write_tensor_artifact

write_tensor_artifact(
    "framework_outputs.npz",
    {
        "boxes": boxes.detach().cpu().numpy(),
        "scores": scores.detach().cpu().numpy(),
    },
    stage="framework",
    source="pytorch 2.7",
    provenance={"model_path": "best.pt", "input_path": "frame.jpg"},
)
```

RKNN output follows the same API. Raw integer output should carry the exact tensor attributes reported by RKNN Runtime:

```python
write_tensor_artifact(
    "rknn_outputs.npz",
    {"output0": output_int8},
    stage="rknn",
    source="rknn-runtime 2.3.2",
    provenance={"model_path": "best.rknn", "device": "RK3588"},
    quantization={
        "output0": {"scale": 0.02265625, "zero_point": -128, "qmin": -128, "qmax": 127}
    },
)
```

The stored array always remains raw and is never rewritten. During `compare-stages`, TensorFence explicitly records a
`dequantized` comparison domain and applies `(q - zero_point) * scale` when an integer artifact carries quantization
metadata. Raw integer summaries and endpoint statistics remain available in the same report. Any comparison involving
a raw integer output is rejected when scale/zero-point metadata is missing, because even two integer code streams may
use different quantization domains.

When the producer environment cannot install TensorFence, save each already obtained output as `.npy`, transfer those
files, and package them on the analysis machine:

```powershell
tensorfence dump-tensors `
  --stage rknn `
  --source "rknn-runtime 2.3.2" `
  --tensor output0=output0.npy `
  --quantization-json quantization.json `
  --provenance-json provenance.json `
  --out rknn_outputs.npz
```

The tensor names must equal the contract output names. This keeps mapping explicit and prevents different output branches from being compared by accident.

For that example, `quantization.json` is an object keyed by tensor name:

```json
{
  "output0": {
    "scale": 0.02265625,
    "zero_point": -128,
    "qmin": -128,
    "qmax": 127,
    "scheme": "asymmetric"
  }
}
```

`provenance.json` is also an object:

```json
{
  "model_path": "best.rknn",
  "runtime_version": "2.3.2",
  "device": "RK3588",
  "input_path": "frame.jpg"
}
```

## Legacy Compatibility

Plain `.npz` archives without `__tensorfence_manifest__` remain readable. Their keys are treated as tensor names, but
they do not provide stage, source, provenance, or quantization evidence. New capture workflows should use v1.

When two canonical artifacts share identity fields such as `input_id`, `input_path`, `input_sha256`, `sample_id`, or
`model_id`, `compare-stages` reports conflicting values as provenance warnings. Record stable IDs or hashes when the
artifacts are produced on different machines.
