# Contributing to TensorFence

[English](./CONTRIBUTING.md) | [简体中文](./CONTRIBUTING.zh-CN.md)

TensorFence is a contract-first diagnostics tool.
Contributions should preserve that focus.

## Good Contribution Targets

- New contract validation rules
- Framework adapters
- ONNX / RKNN comparison stages
- Better diff summaries and reports
- More sample contracts

## Before You Open a PR

- Keep changes small and reviewable
- Add or update tests where possible
- Prefer explicit contract fields over implicit guessing
- Keep the CLI output readable

## Local Setup

```bash
conda env create -f environment.yml
conda activate tensorfence
pip install -e .
pytest
```

## Branch and PR Guidance

- Use one feature per branch
- Describe what stage of the export chain is affected
- Include sample input/output expectations when behavior changes
- Mention whether the change is contract-level, adapter-level, or report-level

## Issue Reports

Use the issue templates in `.github/ISSUE_TEMPLATE/` and include:

- model family
- source framework
- ONNX version
- RKNN version
- target device
- contract file
- a minimal reproduction if possible

