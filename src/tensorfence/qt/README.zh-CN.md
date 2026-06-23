# Qt UI

这个子目录包含 TensorFence 的 Qt 应用目标。
它由根目录 `CMakeLists.txt` 驱动，尽量只放 UI 层内容。

当前内容：

- `app/`：Qt 可执行程序目标
- `CMakeLists.txt`：Qt 子树入口

当前行为：

- 启动一个白色工作台壳层
- 带左侧导航栏和右侧上下文面板
- 按文件类型把内容路由到占位工作区
- 优先强调即时交互反馈，而不是直接执行后端任务

要求：

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt 模块：`Core`、`Quick`、`Qml`、`QuickControls2`、`QuickDialogs2`

请在仓库根目录执行构建：

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

如果 Qt 没有被自动找到：

```bat
set QT_ROOT=<你的 Qt kit 路径>
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="%QT_ROOT%"
cmake --build build/qt --config Release
```

启动方式：

- 单配置生成器：`build/qt/bin/tensorfence_qt`
- Windows 多配置生成器：`build/qt/bin/Release/tensorfence_qt.exe`
