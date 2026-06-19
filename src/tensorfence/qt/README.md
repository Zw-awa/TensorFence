# Qt UI

This subtree contains the Qt application target for TensorFence.
It is built by the root `CMakeLists.txt` and should stay UI-only.

Current contents:

- `app/`: the Qt executable target
- `CMakeLists.txt`: Qt subtree entry point

Requirements:

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt modules: `Core`, `Widgets`

Build from the repository root:

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

If Qt is not auto-detected:

```bash
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="C:/Qt/6.8.0/msvc2022_64"
cmake --build build/qt --config Release
```

Run:

- single-config generators: `build/qt/bin/tensorfence_qt`
- multi-config generators on Windows: `build/qt/bin/Release/tensorfence_qt.exe`
