# 真实诊断样本采集

本目录只保存采集模板、脱敏 contract 和可公开的微型 fixture；不要提交业务图片、模型、`.npy`、`.npz` 或板端日志。真实文件应保留在受控存储中，再按需要生成脱敏回归 fixture。

每一个量化故障案例至少需要同一张输入的 `framework`、`rknn-fp16`、`rknn-int8` 三组原始输出。对于没有 framework 输出的情况，至少采集 `rknn-fp16` 与 `rknn-int8`。不得对任何一组输出执行 decode、sigmoid、阈值过滤或 NMS 后再保存。

## 必填证据

- 同一输入的 SHA-256，写入每份 artifact 的 `provenance.input_sha256`。
- 同一预处理的稳定标识，写入 `provenance.preprocess_id`。建议由颜色顺序、resize、padding、layout、归一化和输入尺寸组成，例如 `rgb-letterbox640-pad114-nchw-div255`。
- 运行时、Toolkit、NPU 驱动、设备和模型变体信息。
- 所有原始整数输出的 `scale`、`zero_point`，以及可用时的 `qmin`、`qmax`、`scheme`。
- 与 contract 完全一致的输出名、shape 和原始 dtype。

不要在 provenance 写入 Token、业务路径、客户名或原始图片名。推荐只存模型 SHA-256、匿名 `sample_id` 和 `input_sha256`。

## 目录建议

```text
case-yolo26-int8-collapse/
  contract.yaml
  capture/
    framework.npz
    rknn-fp16.npz
    rknn-int8.npz
  evidence/
    fp16-output0.npy
    int8-output0.npy
    int8-quantization.json
    fp16-provenance.json
    int8-provenance.json
  expected-summary.md
```

`capture/` 和 `evidence/` 应在真实项目的私有目录中；本仓库只提交 `contract.yaml`、`expected-summary.md` 和脱敏的小型回归 fixture。

## 从板端/WSL 打包

先在每个运行环境中保存原始输出为 `.npy`。RKNN INT8 必须保存 Runtime 返回的原始 `int8` 字节，不要请求 float 输出后再伪造 INT8。然后在安装 TensorFence 的分析机执行：

```powershell
tensorfence dump-tensors `
  --stage rknn `
  --source "rknn-runtime 2.3.2 / RK3588" `
  --tensor output0=evidence/int8-output0.npy `
  --quantization-json evidence/int8-quantization.json `
  --provenance-json evidence/int8-provenance.json `
  --out capture/rknn-int8.npz
```

FP16 同样打包，但不传 `--quantization-json`。`rknn-fp16` 与 `rknn-int8` 可以都使用 stage `rknn`，由 artifact 标签区分模型变体。

量化 metadata 例子：

```json
{
  "output0": {
    "scale": 2.9,
    "zero_point": -128,
    "qmin": -128,
    "qmax": 127,
    "scheme": "asymmetric"
  }
}
```

provenance 例子：

```json
{
  "model_id": "sha256:<model hash>",
  "model_variant": "int8",
  "runtime_version": "2.3.2",
  "toolkit_version": "2.3.2",
  "npu_driver": "0.9.8",
  "device": "RK3588",
  "sample_id": "case-yolo26-001",
  "input_sha256": "<64-character SHA-256>",
  "preprocess_id": "rgb-letterbox640-pad114-nchw-div255"
}
```

## 打包后先校验

```powershell
tensorfence validate-capture `
  --contract contract.yaml `
  --artifact framework=capture/framework.npz `
  --artifact rknn-fp16=capture/rknn-fp16.npz `
  --artifact rknn-int8=capture/rknn-int8.npz
```

只有校验通过，才运行 `compare-stages`。这避免把不同图片、不同 resize 或错误量化参数误判为量化损失。
