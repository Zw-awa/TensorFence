# Qt UI

这个子目录包含 TensorFence 的 Qt 应用目标。
它由根目录 `CMakeLists.txt` 驱动，尽量只放 UI 层内容。

当前内容：

- `app/`：Qt 可执行程序目标
- `CMakeLists.txt`：Qt 子树入口

要求：

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt 模块：`Core`、`Widgets`

请在仓库根目录执行构建：

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

如果 Qt 没有被自动找到：

```bash
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="C:/Qt/6.8.0/msvc2022_64"
cmake --build build/qt --config Release
```

启动方式：

- 单配置生成器：`build/qt/bin/tensorfence_qt`
- Windows 多配置生成器：`build/qt/bin/Release/tensorfence_qt.exe`
