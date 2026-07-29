# TensorFence Product Scope

## Positioning

TensorFence is a contract-first diagnostics toolkit for `YOLO/PP -> ONNX -> RKNN` pipelines.
It is designed to answer:

`where did the deployment pipeline stop matching the original model behavior?`

TensorFence is not only an exporter.
It is a diagnostics and alignment layer for deployment workflows.

## Core Capabilities

### 1. Contract Definition

TensorFence defines explicit contracts for:

- input tensor semantics
- output tensor semantics
- preprocessing behavior
- decode behavior
- NMS behavior
- quantization settings

### 2. Contract Validation

TensorFence validates obvious mismatches before deployment work starts.

Examples:

- input/output shape mismatch
- layout ambiguity
- missing decode fields
- quantization fields missing when quantization is enabled

### 3. Single-Image Inspection

TensorFence inspects one image through a declared preprocessing path and produces:

- normalized preprocessing metadata
- transformed image outputs
- tensor summaries
- reproducible artifacts

### 4. Stage Comparison

TensorFence compares:

- source framework output
- ONNX output
- RKNN output

The goal is to locate the first likely drift point instead of only reporting a bad final result.

### 5. Drift Reporting

TensorFence produces machine-readable and human-readable reports that can point to likely causes:

- preprocess mismatch
- output ordering mismatch
- decode mismatch
- NMS mismatch
- quantization drift
- runtime-specific divergence

Likely-cause recognition should stay conservative and evidence-backed. For example, TensorFence may flag
small non-zero reference values that collapse to zero in a later stage as possible quantization
under-resolution, or an exported ONNX graph containing NMS as a duplicate-postprocessing risk, while still
reporting the evidence behind each conclusion.

### 6. Model Probing

TensorFence can inspect imported model files and extract factual graph information:

- inputs and outputs
- tensor shapes and dtypes
- operator histogram
- graph summary
- suspicious operator patterns

This layer should not pretend to infer hidden engineering semantics with full certainty.

### 7. Draft Contract Generation

TensorFence can generate a draft contract from model facts and rule sets.

Each inferred field should be marked as one of:

- `confirmed`
- `inferred`
- `guessed`
- `unresolved`

### 8. User-Configurable Rule Inference

TensorFence supports user-defined or agent-maintained rules for mapping graph facts to likely semantics.

Examples:

- likely model family
- likely decode mode
- candidate stride sets
- candidate output meanings

### 9. Shared Artifacts

TensorFence should emit shared artifacts for CLI, CI, reports, and Qt UI.

Expected outputs include:

- JSON facts
- YAML draft contracts
- JSON reports
- HTML reports

### 10. Qt Viewer Layer

TensorFence uses a CLI-first architecture and a Qt-based viewer layer.

Qt should help visualize:

- contracts
- image inspection results
- tensor diffs
- stage comparison reports

Qt should not duplicate core business logic.

## What TensorFence Can Do

- validate contracts before export and deployment
- reduce ambiguity in preprocess, decode, and NMS handling
- detect common deployment drift causes
- help agents and users collaborate around the same artifacts
- provide structured facts from imported model files
- generate draft contracts from user-configurable rules
- support reproducible debugging and reporting

## What TensorFence Should Not Do

- claim perfect semantic understanding from model files alone
- replace explicit contracts with opaque guessing
- become a generic exporter collection
- move core logic into the UI layer
- automatically rewrite models or apply quantization fixes; TensorFence should expose measurements and a
  small set of high-confidence likely causes, leaving engineering decisions to the user

## Recommended Architecture

- `core/`
  Contract, validation, preprocess, diff, and report foundations.
- `adapters/`
  Framework, ONNXRuntime, and RKNN integration.
- `probe/`
  Model graph inspection and fact extraction.
- `rules/`
  User-defined inference rules and mapping logic.
- `artifacts/`
  Shared report and contract artifact schemas.
- `cli/`
  Main command-line entry points.
- `qt/`
  Viewer and editing layer for artifacts.

## Near-Term Priorities

1. Single-image preprocessing inspection
2. Shared artifact schema
3. Model probing outputs
4. Draft contract generation
5. ONNX stage comparison
6. RKNN stage comparison
