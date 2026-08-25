# Diagnostic Case Capture

This directory contains templates only. Do not commit production images, model tensors, calibration data, or board captures here.

For an FP16 versus INT8 incident, capture both runs from the same input after identical preprocessing. Package every output as a canonical TensorFence artifact and include `input_sha256` and `preprocess_id` in provenance. Every raw integer output needs its exact `scale` and `zero_point`.

Validate evidence before diagnosis:

```powershell
tensorfence validate-capture `
  --contract contract.yaml `
  --artifact rknn-fp16=fp16.npz `
  --artifact rknn-int8=int8.npz
```

Then run `compare-stages` with the artifacts available for the relevant stages. For ONNX output-contract and duplicate postprocessing checks, run:

```powershell
tensorfence probe-model --model model.onnx --contract contract.yaml --out probe
```

The Chinese capture protocol and the redacted case template are in [README.zh-CN.md](README.zh-CN.md).
