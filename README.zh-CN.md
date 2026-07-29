# TensorFence

[English](./README.md) | [简体中文](./README.zh-CN.md)

[![状态](https://img.shields.io/badge/status-CLI%20MVP-green)](#当前状态)
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
  - [零基础安装](#零基础安装)
  - [草稿契约](#草稿契约)
  - [阶段对比](#阶段对比)
  - [张量产物](#张量产物)
  - [Qt UI 构建](#qt-ui-构建)
  - [Agent 指南](#agent-指南)
  - [契约文件长什么样](#契约文件长什么样)
  - [必须填写什么](#必须填写什么)
  - [TensorFence 会检查什么](#tensorfence-会检查什么)
  - [TensorFence 可以做什么](#tensorfence-可以做什么)
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

如果要做 RKNN 转换和连板流程，建议单独准备一个 WSL/Linux 环境。
仓库里已经加了 `environment.wsl.yml`。RKNN-Toolkit2 请单独从 Rockchip 官方仓库安装对应的 Linux wheel，不要强行把它塞进当前这个 Windows 开发环境里。

## 零基础安装

如果你对 Conda、WSL、Python 环境这些还不熟，先看这两份文档：

- 中文版：[docs/setup-beginner.zh-CN.md](./docs/setup-beginner.zh-CN.md)
- 英文版：[docs/setup-beginner.md](./docs/setup-beginner.md)

如果你想清理测试缓存和临时文件，可以执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\cleanup-temp.ps1
```

如果还想一起清掉本地构建产物，比如 `build/`、`dist/`、`htmlcov/` 和 `*.egg-info/`，可以执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\cleanup-temp.ps1 -IncludeBuildArtifacts
```

项目内约定的本地目录：

- `.tmp/`：运行时临时产物和测试临时文件
- `.cache/`：本地工具缓存，比如 pytest 缓存

## 草稿契约

如果你已经有模型文件，或者已经拿到了模型事实，TensorFence 可以先帮你起草一份契约，而不是从零开始手写。

```bash
tensorfence probe-model --model model.onnx --out out/probe
tensorfence draft-contract --facts out/probe/model_facts.json --rules examples/rules/detection_yolo_v1.yaml --out out/draft.contract.yaml
tensorfence check-contract out/draft.contract.yaml
```

这份草稿会刻意保持保守：

- 图里能可靠拿到的内容直接复用
- 图里拿不到的内容从显式规则补齐
- 仍然需要人工确认的语义会放进报告里，不会假装“自动识别完成”

## 阶段对比

`compare-stages` 是 artifact-first 的端到端诊断命令：

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

它会输出：

- `out/compare/report.json`
- `out/compare/tensor_diffs.json`
- `out/compare/final_summary.json`
- 请求 HTML 时还会生成 `out/compare/report.html`

环境中安装了 `onnxruntime` 时，可以传 `--onnx model.onnx` 直接执行 ONNX。这个 MVP 尚未实现 framework 和 RKNN 的直接执行；应在各自原生环境抓取输出，再把标准 `.npz` artifact 交给 TensorFence。

输出名称必须和契约一致。TensorFence 默认拒绝名称不匹配；`--map-by-order` 只是兼容旧数据的显式逃生口，启用后会在报告中留下警告。`--max-abs-error`、`--min-cosine-similarity` 和小数值归零相关阈值都可以从 CLI 调整。

报告会给出绝对/相对误差、余弦相似度、有限值与 NaN/Inf 数量、零值比例、整数饱和比例和重复极值剪裁比例。当前的保守智能识别可以指出“小的非零参考值被压成零”和可能的剪裁/饱和；ONNX 探测还会提示图内后处理与应用侧重复执行的风险。它们都保留测量证据，不会自动修模型。

## 张量产物

张量 artifact v1 在 `.npz` 中保存具名数组和内嵌 manifest。manifest 记录阶段、来源、dtype、shape、provenance，以及可选的量化 scale/zero-point。旧的普通 `.npz` 仍可读取。带元数据的 raw INT8 会在数值比较域显式反量化，同时保留原始端点统计；任何缺少元数据的 raw INT 比较都会被拒绝。

当框架端或板端已经把输出保存成 `.npy` 时，不需要安装对应运行时适配器，直接打包即可：

```bash
tensorfence dump-tensors \
  --stage rknn \
  --source "rknn-runtime 2.3.2 / RK3588" \
  --tensor output0=output0.npy \
  --quantization-json quantization.json \
  --provenance-json provenance.json \
  --out rknn.npz
```

Python 写入 API、manifest schema、量化元数据和 framework/RKNN 抓取示例见 [docs/tensor-artifact-v1.md](./docs/tensor-artifact-v1.md)。

## Qt UI 构建

Qt UI 通过项目根目录和 `src/tensorfence/qt/` 子目录中的 CMake 配置。
它的职责是查看和轻量编辑契约、报告以及阶段差分 artifact，而不是再做一套执行引擎。

要求：

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt 模块：`Core`、`Quick`、`Qml`、`QuickControls2`、`QuickDialogs2`

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

如果 CMake 找不到 Qt，可以显式指定 Qt 安装路径：

```bat
set QT_ROOT=<你的 Qt kit 路径>
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="%QT_ROOT%"
cmake --build build/qt --config Release
```

最小启动方式：

- 单配置生成器：`build/qt/bin/tensorfence_qt`
- Windows 多配置生成器：`build/qt/bin/Release/tensorfence_qt.exe`

当前 Qt 版本会打开一个白色工作台壳层，包含：

- 左侧导航栏
- 支持拖拽导入的首页工作台
- Contracts、Reports、Compare、Settings 占位页
- 实时状态和反馈区域

Windows 下统一使用一个 Qt 入口：

```powershell
.\tools\qt.ps1 build
.\tools\qt.ps1 smoke
.\tools\qt.ps1 run
```

脚本按“命令行参数、环境变量、`.env`、自动发现”的顺序定位 Qt，并固定使用该安装中的 CMake、MinGW 和 `MinGW Makefiles`。需要本地配置时，将 `.env.example` 复制为 `.env` 并填写 `QT_ROOT`、`QT_VERSION`；`.env` 不会被 Git 提交。检测到 Codex 环境时会自动启用 agent-safe CMake 分支，旧 `.bat` 文件仍作为兼容包装保留。

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

- 输入契约：shape、dtype、layout、颜色空间和任务相关要求
- 预处理契约：resize、letterbox、normalize、pad value
- 输出契约：显式 tensor 名称、语义和 shape
- Decode/NMS 声明：必填字段和明显的内部矛盾
- 量化声明：校准集引用和预处理匹配意图
- 阶段张量：有限值、零值、饱和/剪裁及绝对/相对漂移

## TensorFence 可以做什么

- 在导出和部署前校验显式契约
- 检查单图预处理行为
- 对比 framework、ONNX、RKNN 三段结果
- 生成诊断 artifact 和报告
- 从导入文件中探测模型结构与算子事实
- 基于模型事实和用户规则生成草稿契约
- 支持 CLI first 工作流，并提供 Qt 查看层

正式范围说明见 [docs/product-scope.md](./docs/product-scope.md)。

## 当前状态

TensorFence 已达到第一个 artifact-first CLI MVP。

已具备的内容：

- 严格且按任务校验的部署契约，未知字段会直接报错
- ONNX 图探测和 ONNX Runtime 直接执行
- 单图预处理检查
- 标准张量 artifact schema v1 和 `dump-tensors` 抓取工具
- framework/ONNX/RKNN artifact 对比及 JSON、Markdown、HTML 报告
- 可配置的数值漂移指标和保守原因识别
- Python 3.12 CI、真实 ONNX 集成测试和 wheel 安装后 HTML 烟测

现在就能帮你：

- 在导出前校验或起草契约
- 检查图片预处理后的确切输入张量
- 提取 ONNX 模型事实、算子统计和图内后处理风险
- 直接运行 ONNX，并与抓取的 framework/RKNN 张量比较
- 识别数值漂移、非有限输出、小数值归零和剪裁/饱和证据
- 在不修改模型的前提下生成可复现、带版本的产物

MVP 的明确边界：

- 不直接执行 framework 和 RKNN 模型，需在外部抓取张量
- YOLO/PP-YOLOE decode 和 NMS 当前只做声明与风险检查，不执行专用后处理
- 预处理目前输出 float32 图片张量
- Qt 仍是查看器/工作台预览，并未接通每一条 CLI 流程
- TensorFence 不会自动改图、重导出或应用量化修复

## 支持范围

| 领域 | 状态 |
| --- | --- |
| 严格契约校验 | MVP |
| ONNX 探测和直接运行时对比 | MVP |
| Framework 输出对比 | MVP，通过张量 artifact |
| RKNN 输出对比 | MVP，通过张量 artifact |
| 张量 manifest 和量化元数据 | v1 |
| 数值/量化漂移报告 | MVP |
| YOLO/PP-YOLOE decode 与 NMS 执行 | 未实现 |
| Framework/RKNN 直接适配器 | 未实现 |
| Qt 工作台 | 预览壳层 |

## 仓库结构

- `CMakeLists.txt`：Qt UI 的 CMake 入口
- `src/tensorfence/core/`：契约、校验、差分与报告基础层
- `src/tensorfence/adapters/`：框架和运行时适配器
- `src/tensorfence/cli/`：分阶段 CLI 子命令模块
- `src/tensorfence/probe/`：模型探测和图结构事实提取
- `src/tensorfence/rules/`：用户自定义推断和映射规则
- `src/tensorfence/qt/`：Qt UI 层
- `src/tensorfence/qt/CMakeLists.txt`：Qt UI 子树
- `src/tensorfence/qt/app/`：Qt 应用目标
- `src/tensorfence/artifacts/`：artifact schema 和序列化
- `src/tensorfence/artifacts/facts/`：模型事实 artifact schema
- `src/tensorfence/artifacts/reports/`：报告 schema 和导出器
- `src/tensorfence/artifacts/contracts/`：契约草稿和导出 artifact
- `src/tensorfence/`：共享入口模块和公共代码
- `docs/`：设计说明、截图和架构文档
- `docs/product-scope.md`：正式范围和能力说明
- `assets/`：图标和静态 UI 资源
- `examples/`：示例契约文件
- `examples/rules/`：用户规则示例
- `examples/reports/`：示例报告输出
- `examples/models/`：导入模型的示例元信息或清单
- `tests/unit/`：单元测试
- `tests/integration/`：真实 ONNX CLI 流水线测试
- `.github/workflows/`：Python 测试和 wheel 安装 CI
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
