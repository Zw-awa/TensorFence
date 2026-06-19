# Roadmap

[English](./ROADMAP.md) | [简体中文](./ROADMAP.zh-CN.md)

## Phase 0: Foundation

- Contract schema
- Validation rules
- Tensor summaries and tensor diffs
- CLI and sample contracts

## Phase 1: Framework Adapters

- PyTorch export-side adapter
- Paddle export-side adapter
- Stage metadata normalization

## Phase 2: Stage Comparison

- Framework vs ONNX comparison
- ONNX vs RKNN comparison
- Single-image drift report

## Phase 3: Detection-Specific Reporting

- YOLO decode diagnostics
- PP-YOLOE decode diagnostics
- NMS and threshold drift hints

## Phase 4: Quantization Analysis

- Calibration dataset checks
- Preprocess consistency checks
- Quantization-sensitive layer hints

## Non-Goals For Now

- Supporting every vision task on day one
- Guessing model semantics without a contract
- Hiding ambiguous mismatches behind a green check mark

