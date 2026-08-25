# TensorFence

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![Status](https://img.shields.io/badge/status-CLI%20MVP-green)](#current-status)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](./LICENSE)

TensorFence helps when a model:

- exports successfully, but RKNN behavior is wrong
- runs, but boxes shift, scores collapse, or classes drift
- looks correct in framework or ONNX, then breaks after RKNN conversion
- fails because preprocessing, decode, or NMS is not aligned

If that sounds like your problem, this project is built for that failure mode.

## Table of Contents

- [TensorFence](#tensorfence)
  - [Table of Contents](#table-of-contents)
  - [Why This Exists](#why-this-exists)
  - [When TensorFence Fits](#when-tensorfence-fits)
  - [Quick Start](#quick-start)
  - [Beginner Setup](#beginner-setup)
  - [Draft Contract](#draft-contract)
  - [Stage Compare](#stage-compare)
  - [Tensor Artifacts](#tensor-artifacts)
  - [Qt UI Build](#qt-ui-build)
  - [Agent Guide](#agent-guide)
  - [What a Contract File Looks Like](#what-a-contract-file-looks-like)
  - [What You Must Fill In](#what-you-must-fill-in)
  - [What TensorFence Checks](#what-tensorfence-checks)
  - [What TensorFence Can Do](#what-tensorfence-can-do)
  - [Current Status](#current-status)
  - [Supported Scope](#supported-scope)
  - [Repository Layout](#repository-layout)
  - [Contributing](#contributing)
  - [License](#license)

If you are an agent reading this repository for a user, start with [AGENT.md](./AGENT.md).

## Why This Exists

Most conversion tools answer one question:
`can the model be converted and executed?`

TensorFence answers the harder question:
`where did the exported pipeline stop matching the original model behavior?`

It is a contract-first drift diagnosis tool for `YOLO/PP -> ONNX -> RKNN`.

## When TensorFence Fits

Use TensorFence when you have one of these symptoms:

| What you see | What is often wrong |
| --- | --- |
| Export succeeds, runtime runs, results are still bad | preprocess, decode, NMS, quantization |
| ONNX looks fine, RKNN output differs | operator lowering, layout, precision, output ordering |
| Boxes shift after resize/letterbox | resize mode, padding, input shape, color order |
| Confidence collapses | normalization, quantization, activation placement |
| Only some classes are wrong | output mapping, decode rule, label alignment |

## Quick Start

```bash
conda env create -f environment.yml
conda activate tensorfence
pip install -e .
tensorfence doctor
tensorfence init tensorfence.contract.yaml
tensorfence check-contract tensorfence.contract.yaml
```

If you already have a model contract, you can run:

```bash
tensorfence doctor
tensorfence check-contract your.contract.yaml
```

`tensorfence init` writes a starter contract file to the path you choose.

For RKNN conversion and board-side workflows, keep a separate WSL/Linux environment.
This repository includes `environment.wsl.yml` for that split. Install the official RKNN-Toolkit2 Linux wheel separately from the Rockchip repository, and do not try to force RKNN-Toolkit2 into the Windows dev env.

## Beginner Setup

If you are not comfortable with Conda, WSL, or Python environments yet, start here:

- English: [docs/setup-beginner.md](./docs/setup-beginner.md)
- Chinese: [docs/setup-beginner.zh-CN.md](./docs/setup-beginner.zh-CN.md)

To clean test caches and temporary artifacts:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\cleanup-temp.ps1
```

To also remove local build outputs such as `build/`, `dist/`, `htmlcov/`, and `*.egg-info/`:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\cleanup-temp.ps1 -IncludeBuildArtifacts
```

Project-local runtime directories:

- `.tmp/` for temporary run artifacts and test scratch data
- `.cache/` for local tooling caches such as pytest

## Draft Contract

When you already have a model file or model facts, TensorFence can draft a contract instead of asking you to start from zero.

```bash
tensorfence probe-model --model model.onnx --out out/probe
tensorfence draft-contract --facts out/probe/model_facts.json --rules examples/rules/detection_yolo_v1.yaml --out out/draft.contract.yaml
tensorfence check-contract out/draft.contract.yaml
```

The draft is intentionally conservative:

- it reuses exported facts where the graph is reliable
- it fills the rest from explicit rules
- it keeps unresolved semantic choices visible in the report

## Stage Compare

`compare-stages` is the artifact-first end-to-end diagnosis command:

```bash
tensorfence compare-stages \
  --contract contract.yaml \
  --image demo.jpg \
  --framework-out framework.npz \
  --onnx-out onnx.npz \
  --rknn-out rknn.npz \
  --out out/compare \
  --report-format html
```

It writes:

- `out/compare/report.json`
- `out/compare/tensor_diffs.json`
- `out/compare/final_summary.json`
- `out/compare/report.html` when HTML is requested

If `onnxruntime` is installed, pass `--onnx model.onnx` to execute ONNX directly. Direct framework and RKNN execution is not implemented in this MVP; capture those outputs in their native environment and pass canonical `.npz` artifacts.

Output names must match the contract. TensorFence rejects name mismatches by default; `--map-by-order` is an explicit, warning-producing escape hatch for legacy data. Numerical thresholds such as `--max-abs-error`, `--min-cosine-similarity`, and the small-value collapse thresholds are configurable from the CLI.

The report includes absolute and relative errors, cosine similarity, finite/NaN/Inf counts, zero ratios, integer saturation and repeated-extreme clipping ratios. Conservative likely-cause rules currently identify small non-zero values collapsing to zero and likely clipping/saturation. ONNX probing also warns when graph-embedded postprocessing may be duplicated by application code. These are evidence-backed conclusions, not automatic fixes.

## Tensor Artifacts

Tensor artifact v1 stores named arrays and an embedded manifest containing the stage, source, dtype, shape, provenance, and optional quantization scale/zero-point metadata. Existing plain `.npz` files remain readable. Raw integer tensors with metadata are explicitly dequantized for numerical comparison while their raw endpoint statistics remain visible; any raw integer comparison without metadata is rejected.

When framework or board code has already saved output arrays as `.npy`, package them without installing a runtime adapter:

```bash
tensorfence dump-tensors \
  --stage rknn \
  --source "rknn-runtime 2.3.2 / RK3588" \
  --tensor output0=output0.npy \
  --quantization-json quantization.json \
  --provenance-json provenance.json \
  --out rknn.npz
```

The Python writer API, manifest schema, quantization metadata, and framework/RKNN capture examples are documented in [docs/tensor-artifact-v1.md](./docs/tensor-artifact-v1.md).

For a real FP16/INT8 failure, validate that the evidence represents the same input and preprocessing before comparing stages:

```powershell
tensorfence validate-capture `
  --contract contract.yaml `
  --artifact rknn-fp16=fp16.npz `
  --artifact rknn-int8=int8.npz
```

This requires canonical artifacts, matching `input_sha256` and `preprocess_id`, and exact `scale` and `zero_point` for every raw INT8 output. The full capture protocol and redacted-case template are in [examples/diagnostic-cases/README.zh-CN.md](./examples/diagnostic-cases/README.zh-CN.md).

## Qt UI Build

The Qt UI is configured with CMake from the project root and the `src/tensorfence/qt/` subtree.
It is intended to organize contracts, reports, and stage-diff artifacts. Python CLI remains the only diagnostic engine; the UI does not reimplement its rules.

Requirements:

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt modules: `Core`, `Quick`, `Qml`, `QuickControls2`, `QuickDialogs2`

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

If CMake cannot find Qt, point it at your Qt installation:

```bat
set QT_ROOT=<path-to-your-qt-kit>
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="%QT_ROOT%"
cmake --build build/qt --config Release
```

Minimal run instructions:

- single-config generators: `build/qt/bin/tensorfence_qt`
- multi-config generators on Windows: `build/qt/bin/Release/tensorfence_qt.exe`

The current Qt workspace provides:

- a left navigation rail
- a drag-and-drop home workspace
- `check-contract` from the Contracts page
- FP16/INT8 evidence validation and contract-aware ONNX probing from Compare
- system viewing for Markdown, HTML, and JSON reports
- an explicit Windows `tensorfence.exe` or `python.exe` selection in Settings, with live command output and exit status

On Windows, use the single Qt entry point:

```powershell
.\tools\qt.ps1 build
.\tools\qt.ps1 smoke
.\tools\qt.ps1 run
```

The script resolves Qt from command-line arguments, environment variables, `.env`, then automatic discovery, and pins CMake, MinGW, and `MinGW Makefiles` from that installation. For local configuration, copy `.env.example` to `.env` and set `QT_ROOT` and `QT_VERSION`; `.env` is ignored by Git. Codex environments automatically use the agent-safe CMake branch. The older `.bat` files remain as compatibility wrappers.

See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for Qt UI licensing notes.

Qt invokes only an explicitly selected local Windows CLI. It never enters WSL or guesses a Conda environment. Use WSL/RKNN Toolkit2 and board code for export and capture, then import canonical artifacts into Qt or the CLI for the evidence comparison.

## Agent Guide

If you are an agent helping a user with this repository:

- Read [AGENT.md](./AGENT.md) first.
- Then inspect [examples/detection_contract.yaml](./examples/detection_contract.yaml).
- Prefer asking for missing model, preprocess, and runtime details before guessing.
- If the user wants a fix, identify the failing stage first: preprocess, decode, NMS, quantization, or runtime.

## What a Contract File Looks Like

TensorFence works from an explicit contract, not from guessing.

<details>
<summary>Click to view a sample contract / 点击查看样例契约</summary>

```yaml
name: tensorfence-demo-yolo
task: detection
source_framework: pytorch
target_runtime: rknn
input:
  name: images
  shape: [1, 3, 640, 640]
  dtype: float32
  layout: NCHW
  semantic: model_input
outputs:
  - name: output0
    shape: [1, 8400, 85]
    dtype: float32
    layout: N/A
    semantic: raw_predictions
preprocess:
  input_color_space: BGR
  output_color_space: RGB
  input_layout: HWC  # layout before preprocessing; usually HWC for image data
  output_layout: NCHW  # layout after preprocessing; fed into the model
  resize:
    mode: letterbox
    target_size: [640, 640]
    interpolation: bilinear
    keep_aspect_ratio: true
decode:
  family: yolo
  mode: anchor_free
  num_classes: 80
  strides: [8, 16, 32]
  head_names: [output0]
  score_activation: sigmoid
  box_activation: sigmoid
nms:
  score_threshold: 0.25
  iou_threshold: 0.45
quantization:
  enabled: false
```

</details>

## What You Must Fill In

At minimum, a detection contract should declare:

| Group | Required fields |
| --- | --- |
| Basic metadata | `name`, `task`, `source_framework`, `target_runtime` |
| Input | `input.name`, `input.shape`, `input.dtype`, `input.layout`, `input.semantic` |
| Outputs | at least one item in `outputs`, each with `name`, `shape`, `dtype`, `layout`, `semantic` |
| Preprocess | `input_color_space`, `input_layout`, `output_layout` (`layout` alias), `resize.mode`, `resize.target_size`, `resize.interpolation`, `resize.keep_aspect_ratio` |
| Decode | `family`, `mode`, `num_classes`, `strides`, `head_names`, `score_activation`, `box_activation` |

If `quantization.enabled` is `true`, also fill:

- `quantization.calibration_dataset`
- `quantization.calibration_samples`

Recommended, but not strictly mandatory:

- `preprocess.output_color_space`
- `preprocess.normalize`
- `preprocess.pad_value`
- `nms`

## What TensorFence Checks

- Input contract: shape, dtype, layout, color space, and task-aware requirements
- Preprocess contract: resize, letterbox, normalize, pad value
- Output contract: explicit tensor names, semantics, and shapes
- Decode/NMS declarations: required fields and obvious internal inconsistencies
- Quantization declaration: calibration references and preprocess-match intent
- Stage tensors: finite values, zeros, saturation/clipping, and absolute/relative drift

## What TensorFence Can Do

- validate explicit deployment contracts before export and deployment
- inspect single-image preprocessing behavior
- compare framework, ONNX, and RKNN stages
- generate diagnostic artifacts and reports
- probe model structure and operator facts from imported files
- generate draft contracts from model facts and user-defined rules
- support CLI-first workflows with a Qt viewer layer

See [docs/product-scope.md](./docs/product-scope.md) for the formal scope.

## Current Status

TensorFence has reached its first artifact-first CLI MVP.

What exists now:

- strict, task-aware deployment contracts that reject unknown fields
- ONNX graph probing and direct ONNX Runtime execution
- single-image preprocessing inspection
- canonical tensor artifact schema v1 and the `dump-tensors` capture utility
- framework/ONNX/RKNN artifact comparison with JSON, Markdown, and HTML reports
- configurable numerical drift metrics and conservative likely-cause detection
- Python 3.12 CI, real ONNX integration coverage, and installed-wheel HTML smoke coverage

What you can use right now:

- validate or draft a contract before export work starts
- inspect the exact image preprocessing tensor
- extract ONNX model facts, operator histograms, and embedded-postprocess warnings
- run ONNX and compare it with captured framework/RKNN tensors
- detect numerical drift, non-finite output, small-value zero collapse, and clipping/saturation evidence
- produce reproducible, versioned artifacts without changing the model

Deliberate MVP boundaries:

- framework and RKNN models are not executed directly; their tensors are captured externally
- YOLO/PP-YOLOE decode and NMS are declared and inspected, but task-specific postprocessing is not executed
- preprocessing currently produces float32 image tensors
- the Qt application is a viewer/workspace preview and is not wired to every CLI workflow
- TensorFence never rewrites models or applies quantization fixes automatically

## Supported Scope

| Area | Status |
| --- | --- |
| Strict contract validation | MVP |
| ONNX probing and direct runtime comparison | MVP |
| Framework output comparison | MVP via tensor artifact |
| RKNN output comparison | MVP via tensor artifact |
| Tensor artifact manifest and quantization metadata | v1 |
| Numerical/quantization drift reports | MVP |
| YOLO/PP-YOLOE decode and NMS execution | Not implemented |
| Direct framework/RKNN adapters | Not implemented |
| Qt workbench | Preview shell |

## Repository Layout

- `CMakeLists.txt`: Qt UI CMake entry point
- `src/tensorfence/core/`: contract, validation, diff, and report foundations
- `src/tensorfence/adapters/`: framework and runtime adapters
- `src/tensorfence/cli/`: staged CLI command modules
- `src/tensorfence/probe/`: model probing and graph fact extraction
- `src/tensorfence/rules/`: user-defined inference and mapping rules
- `src/tensorfence/qt/`: Qt UI layer
- `src/tensorfence/qt/CMakeLists.txt`: Qt UI subtree
- `src/tensorfence/qt/app/`: Qt application target
- `src/tensorfence/artifacts/`: artifact schemas and serializers
- `src/tensorfence/artifacts/facts/`: model fact artifact schemas
- `src/tensorfence/artifacts/reports/`: report schema and exporters
- `src/tensorfence/artifacts/contracts/`: contract draft/export artifacts
- `src/tensorfence/`: shared package entry points and common modules
- `docs/`: design notes, screenshots, and architecture docs
- `docs/product-scope.md`: formal scope and capability statement
- `assets/`: icons and static UI resources
- `examples/`: sample contract files
- `examples/rules/`: sample user rules
- `examples/reports/`: sample report outputs
- `examples/models/`: sample imported model metadata or manifests
- `tests/unit/`: unit-level checks
- `tests/integration/`: real ONNX CLI pipeline checks
- `.github/workflows/`: Python test and wheel-install CI
- `tests/fixtures/`: shared test inputs
- `.github/ISSUE_TEMPLATE/`: issue templates for contributors
- `THIRD_PARTY_NOTICES.md`: third-party license notes

## Contributing

If you want to help, start with:

1. A new backend adapter
2. A contract validator rule
3. A sample model contract
4. A report improvement

See [CONTRIBUTING.md](./CONTRIBUTING.md) and [CONTRIBUTING.zh-CN.md](./CONTRIBUTING.zh-CN.md).

## License

TensorFence is released under the [Apache License 2.0](./LICENSE).
See [NOTICE](./NOTICE).
See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for Qt UI licensing notes.
