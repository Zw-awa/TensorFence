# TensorFence

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![Status](https://img.shields.io/badge/status-foundation-blue)](#current-status)
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

`compare-stages` is the first end-to-end diagnosis command. In v1 it works best with exported stage outputs:

```bash
tensorfence compare-stages \
  --contract contract.yaml \
  --image demo.jpg \
  --framework-out framework.npz \
  --onnx-out onnx.npz \
  --rknn-out rknn.npz \
  --out out/compare
```

It writes:

- `out/compare/report.json`
- `out/compare/tensor_diffs.json`
- `out/compare/final_summary.json`

If `onnxruntime` is installed, you can also provide `--onnx model.onnx` or `--onnx-out onnx.npz`.
Direct framework and RKNN execution are still staged behind adapter hooks, so v1 expects `.npz` artifacts there.

## Qt UI Build

The Qt UI is configured with CMake from the project root and the `src/tensorfence/qt/` subtree.
It is intended as a viewer and lightweight editor for contracts, reports, and stage-diff artifacts, not as a second execution engine.

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

The current Qt build opens a compact warm-white workspace shell with:

- a left navigation rail
- a drag-and-drop home workspace
- contracts, reports, compare, and settings placeholder pages
- live status and feedback surfaces

Windows helper scripts are available under `tools/`:

- `qt-configure-release.bat`
- `qt-build-release.bat`
- `qt-deploy-release.bat`
- `qt-run-release.bat`
- `qt-release-all.bat`

See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md) for Qt UI licensing notes.

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

- Input contract: shape, dtype, layout, color space
- Preprocess contract: resize, letterbox, normalize, pad value
- Output contract: tensor order, tensor semantics, tensor shape
- Decode contract: YOLO / PP-YOLOE style decode rules
- NMS contract: thresholds, class handling, method
- Quantization contract: calibration data and preprocess match

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

TensorFence is in the foundation stage.

What exists now:

- A conda-ready project skeleton
- A contract schema for input and output semantics
- Validation for obvious mismatch risks
- Tensor summary and tensor diff helpers
- A CLI for `doctor`, `check-contract`, `init`, `inspect-image`, `probe-model`, and `draft-contract`

What you can use right now:

- validate a model contract before export work starts
- catch input, output, preprocess, and decode mismatches early
- turn a vague deployment failure into a reproducible report
- build a clean baseline for future adapter work
- extract ONNX model facts, operator histograms, and graph summaries
- generate a rule-driven draft contract from ONNX facts

Next capability milestones:

- shared report and artifact schema
- ONNX stage comparison
- RKNN stage comparison

## Supported Scope

| Area | Status |
| --- | --- |
| Detection contracts | Foundation only |
| YOLO-style decode rules | Foundation only |
| PP-YOLOE contracts | Planned |
| ONNX runtime comparison | Planned |
| RKNN runtime comparison | Planned |
| Quantization drift reports | Planned |

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
- `tests/integration/`: adapter and pipeline checks
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
