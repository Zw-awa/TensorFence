# 支持范围

[English](./SUPPORT.md) | [简体中文](./SUPPORT.zh-CN.md)

TensorFence 对契约完整性会保持严格。

## 当前重点

- 检测流水线
- YOLO 类 head
- PP-YOLOE 类部署
- 单图漂移诊断

## 目前明确限制

- 没有契约的任意自定义 head
- 未声明的解码逻辑
- 未声明的后处理逻辑
- 依赖隐式框架默认值的混合约定

## 一个好的契约应该说明什么

- 输入 shape、dtype、layout、颜色空间
- 预处理 resize 和 normalize 规则
- 输出 tensor 名称和语义
- 解码 family 与激活规则
- NMS 阈值与行为
- 量化设置与校准集来源

