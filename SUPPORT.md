# Supported Scope

[English](./SUPPORT.md) | [简体中文](./SUPPORT.zh-CN.md)

TensorFence is intentionally strict about contract completeness.

## Current Emphasis

- Detection pipelines
- YOLO-style heads
- PP-YOLOE-style deployments
- Single-image drift diagnosis

## Explicitly Limited For Now

- Arbitrary custom heads without a contract
- Unspecified decode logic
- Unspecified postprocess logic
- Mixed conventions that rely on implicit framework defaults

## What a Good Contract Should Specify

- input shape, dtype, layout, and color space
- preprocessing resize and normalization rules
- output tensor names and semantics
- decode family and activation rules
- NMS thresholds and behavior
- quantization settings and calibration data source

