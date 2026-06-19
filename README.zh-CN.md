# TensorFence

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![状态](https://img.shields.io/badge/status-foundation-blue)](#当前状态)
[![协议](https://img.shields.io/badge/license-Apache%202.0-green)](./LICENSE)

TensorFence 适合这些场景：

- 模型导出成功了，但 RKNN 跑出来就是不对
- 模型能跑，但框偏了、分数掉了、类别漂了
- 框架里和 ONNX 看着都正常，到了 RKNN 之后就坏了
- 问题根源在预处理、解码或 NMS 没对齐

如果你的问题像上面这些，这个项目就是专门冲着这类故障来的。

## 目录

- [TensorFence](#tensorfence)
  - [目录](#目录)
  - [为什么要做这个](#为什么要做这个)
  - [什么时候适合用 TensorFence](#什么时候适合用-tensorfence)
  - [快速开始](#快速开始)
  - [Qt UI 构建](#qt-ui-构建)
  - [Agent 指南](#agent-指南)
  - [契约文件长什么样](#契约文件长什么样)
  - [必须填写什么](#必须填写什么)
  - [TensorFence 会检查什么](#tensorfence-会检查什么)
  - [当前状态](#当前状态)
  - [支持范围](#支持范围)
  - [仓库结构](#仓库结构)
  - [参与贡献](#参与贡献)
  - [许可证](#许可证)

如果你是代用户阅读这个仓库的 Agent，先看 [AGENT.md](./AGENT.md)。

## 为什么要做这个

大多数转换工具回答的是：
`能不能导出，能不能运行？`

TensorFence 想回答更难的那句：
`导出链路到底从哪一步开始不再像原模型？`

它是一个面向 `YOLO/PP -> ONNX -> RKNN` 的契约优先漂移诊断工具。

## 什么时候适合用 TensorFence

如果你遇到下面这些症状，TensorFence 就比较对口：

| 你看到的现象 | 常见问题 |
| --- | --- |
| 导出成功，运行正常，但结果仍然很差 | 预处理、解码、NMS、量化 |
| ONNX 看起来正常，RKNN 输出却不一样 | 算子下沉、layout、精度、输出顺序 |
| resize / letterbox 后框整体偏移 | resize 模式、padding、输入尺寸、颜色顺序 |
| 置信度大幅下降 | normalize、量化、激活位置 |
| 只有部分类别错 | 输出映射、解码规则、标签对齐 |

## 快速开始

```bash
conda env create -f environment.yml
conda activate tensorfence
pip install -e .
tensorfence doctor
tensorfence init tensorfence.contract.yaml
tensorfence check-contract tensorfence.contract.yaml
```

如果你已经有自己的模型契约，也可以直接运行：

```bash
tensorfence doctor
tensorfence check-contract your.contract.yaml
```

`tensorfence init` 会把一个起步契约写到你指定的路径。

## Qt UI 构建

Qt UI 通过项目根目录和 `src/tensorfence/qt/` 子目录中的 CMake 配置。

要求：

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt 模块：`Core`、`Widgets`

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

如果 CMake 找不到 Qt，可以显式指定 Qt 安装路径：

```bash
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="C:/Qt/6.8.0/msvc2022_64"
cmake --build build/qt --config Release
```

最小启动方式：

- 单配置生成器：`build/qt/bin/tensorfence_qt`
- Windows 多配置生成器：`build/qt/bin/Release/tensorfence_qt.exe`

当前 skeleton 会打开一个小的 `TensorFence Qt UI skeleton` 窗口。

Qt UI 的许可说明见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。

## Agent 指南

如果你是代用户阅读这个仓库的 Agent：

- 先看 [AGENT.md](./AGENT.md)
- 再看 [examples/detection_contract.yaml](./examples/detection_contract.yaml)
- 在不知道输入、预处理、runtime 细节时，优先向用户提问，而不是猜
- 如果用户要修问题，先判断故障阶段：预处理、解码、NMS、量化，还是 runtime

## 契约文件长什么样

TensorFence 依赖显式契约，不靠猜。

<details>
<summary>点击查看样例契约</summary>

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
  input_layout: HWC  # 预处理前的布局；图像数据通常是 HWC
  output_layout: NCHW  # 预处理后的布局；喂给模型的布局
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

## 必须填写什么

检测类契约至少要声明这些内容：

| 分组 | 必填字段 |
| --- | --- |
| 基本信息 | `name`、`task`、`source_framework`、`target_runtime` |
| 输入 | `input.name`、`input.shape`、`input.dtype`、`input.layout`、`input.semantic` |
| 输出 | `outputs` 至少 1 项，每项都要有 `name`、`shape`、`dtype`、`layout`、`semantic` |
| 预处理 | `input_color_space`、`input_layout`、`output_layout`（兼容别名 `layout`）、`resize.mode`、`resize.target_size`、`resize.interpolation`、`resize.keep_aspect_ratio` |
| 解码 | `family`、`mode`、`num_classes`、`strides`、`head_names`、`score_activation`、`box_activation` |

如果 `quantization.enabled` 为 `true`，还要补：

- `quantization.calibration_dataset`
- `quantization.calibration_samples`

建议补充，但不强制：

- `preprocess.output_color_space`
- `preprocess.normalize`
- `preprocess.pad_value`
- `nms`

## TensorFence 会检查什么

- 输入契约：shape、dtype、layout、颜色空间
- 预处理契约：resize、letterbox、normalize、pad value
- 输出契约：tensor 顺序、tensor 语义、tensor shape
- 解码契约：YOLO / PP-YOLOE 类解码规则
- NMS 契约：阈值、类别处理、方法
- 量化契约：校准集与推理预处理是否一致

## 当前状态

TensorFence 目前处于基础建设阶段。

已具备的内容：

- 支持 `conda` 的项目骨架
- 输入/输出语义契约
- 明显不匹配项的校验
- 张量摘要与差分辅助函数
- `doctor`、`check-contract`、`init` 三个基础命令

现在就能帮你：

- 在导出前先把契约和预处理问题拦住
- 快速定位输入、输出、预处理、解码这几类明显漂移
- 把模糊的部署失败变成可复现的报告
- 为后续适配器和回归测试提供统一基线

<details>
<summary>下一步会补什么</summary>

- ONNX 执行
- RKNN 执行
- 框架适配器
- 图像级预处理流水线
- 端到端分阶段对比

</details>

## 支持范围

| 领域 | 状态 |
| --- | --- |
| 检测任务契约 | 基础阶段 |
| YOLO 类解码规则 | 基础阶段 |
| PP-YOLOE 契约 | 计划中 |
| ONNX 运行时对比 | 计划中 |
| RKNN 运行时对比 | 计划中 |
| 量化漂移报告 | 计划中 |

## 仓库结构

- `CMakeLists.txt`：Qt UI 的 CMake 入口
- `src/tensorfence/core/`：契约、校验、差分与报告基础层
- `src/tensorfence/adapters/`：框架和运行时适配器
- `src/tensorfence/qt/`：Qt UI 层
- `src/tensorfence/qt/CMakeLists.txt`：Qt UI 子树
- `src/tensorfence/qt/app/`：Qt 应用目标
- `src/tensorfence/artifacts/`：artifact schema 和序列化
- `src/tensorfence/`：共享入口模块和公共代码
- `docs/`：设计说明、截图和架构文档
- `assets/`：图标和静态 UI 资源
- `examples/`：示例契约文件
- `examples/reports/`：示例报告输出
- `tests/unit/`：单元测试
- `tests/integration/`：适配器和流水线测试
- `tests/fixtures/`：共享测试输入
- `.github/ISSUE_TEMPLATE/`：贡献者使用的 issue 模板
- `THIRD_PARTY_NOTICES.md`：第三方协议说明

## 参与贡献

如果你想参与，建议从下面几类内容开始：

1. 新的后端适配器
2. 新的契约校验规则
3. 一个样例模型契约
4. 一项报告改进

同时也可以阅读 [CONTRIBUTING.md](./CONTRIBUTING.md) 和 [CONTRIBUTING.zh-CN.md](./CONTRIBUTING.zh-CN.md)。

## 许可证

TensorFence 采用 [Apache 2.0](./LICENSE) 开源协议。
详见 [NOTICE](./NOTICE)。
Qt UI 的许可说明见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
