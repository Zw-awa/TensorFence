# 参与 TensorFence 贡献

[English](./CONTRIBUTING.md) | [简体中文](./CONTRIBUTING.zh-CN.md)

TensorFence 是一个契约优先的诊断工具。
贡献内容也应该保持这个方向。

## 适合贡献的内容

- 新的契约校验规则
- 框架适配器
- ONNX / RKNN 对比分阶段
- 更好的差分摘要和报告
- 更多样例契约

## 提交 PR 前

- 控制改动范围，尽量小而清晰
- 能补测试就补测试
- 优先显式声明契约字段，不要靠隐式猜测
- 保持 CLI 输出清晰可读

## 本地环境

```bash
conda env create -f environment.yml
conda activate tensorfence
pip install -e .
pytest
```

## 分支与 PR 建议

- 一个分支只做一类事情
- 说明这次改动影响导出链路的哪一段
- 行为变化时请说明输入/输出的预期
- 说明这次改动是契约层、适配层，还是报告层

## Issue 说明

请使用 `.github/ISSUE_TEMPLATE/` 里的模板，并尽量提供以下信息：

- 模型系列
- 源框架
- ONNX 版本
- RKNN 版本
- 目标设备
- 契约文件
- 最小复现步骤

