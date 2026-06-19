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
  - [Qt UI Build](#qt-ui-build)
  - [Agent Guide](#agent-guide)
  - [What a Contract File Looks Like](#what-a-contract-file-looks-like)
  - [What You Must Fill In](#what-you-must-fill-in)
  - [What TensorFence Checks](#what-tensorfence-checks)
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

## Qt UI Build

The Qt UI is configured with CMake from the project root and the `src/tensorfence/qt/` subtree.

Requirements:

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt modules: `Core`, `Widgets`

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

If CMake cannot find Qt, point it at your Qt installation:

```bash
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="C:/Qt/6.8.0/msvc2022_64"
cmake --build build/qt --config Release
```

Minimal run instructions:

- single-config generators: `build/qt/bin/tensorfence_qt`
- multi-config generators on Windows: `build/qt/bin/Release/tensorfence_qt.exe`

The current skeleton opens a small `TensorFence Qt UI skeleton` window.

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

## Current Status

TensorFence is in the foundation stage.

What exists now:

- A conda-ready project skeleton
- A contract schema for input and output semantics
- Validation for obvious mismatch risks
- Tensor summary and tensor diff helpers
- A small CLI for `doctor`, `check-contract`, and `init`

What you can use right now:

- validate a model contract before export work starts
- catch input, output, preprocess, and decode mismatches early
- turn a vague deployment failure into a reproducible report
- build a clean baseline for future adapter work

<details>
<summary>What is not built yet / Next steps</summary>

- ONNX execution
- RKNN execution
- Framework adapters
- Image-level preprocessing pipeline
- End-to-end stage comparison

</details>

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
- `src/tensorfence/qt/`: Qt UI layer
- `src/tensorfence/qt/CMakeLists.txt`: Qt UI subtree
- `src/tensorfence/qt/app/`: Qt application target
- `src/tensorfence/artifacts/`: artifact schemas and serializers
- `src/tensorfence/`: shared package entry points and common modules
- `docs/`: design notes, screenshots, and architecture docs
- `assets/`: icons and static UI resources
- `examples/`: sample contract files
- `examples/reports/`: sample report outputs
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
