# Qt UI

This subtree contains the Qt application target for TensorFence.
It is built by the root `CMakeLists.txt` and should stay UI-only.

Current contents:

- `app/`: the Qt executable target
- `CMakeLists.txt`: Qt subtree entry point

Current behavior:

- launches a white workspace shell
- shows a left navigation rail and right context panel
- routes files by type into placeholder workspaces
- emphasizes immediate UI feedback over backend execution

Requirements:

- `CMake >= 3.24`
- `Qt >= 6.5`
- Qt modules: `Core`, `Quick`, `Qml`, `QuickControls2`, `QuickDialogs2`

Build from the repository root:

```bash
cmake -S . -B build/qt
cmake --build build/qt
```

If Qt is not auto-detected:

```bat
set QT_ROOT=<path-to-your-qt-kit>
cmake -S . -B build/qt -DCMAKE_PREFIX_PATH="%QT_ROOT%"
cmake --build build/qt --config Release
```

Run:

- single-config generators: `build/qt/bin/tensorfence_qt`
- multi-config generators on Windows: `build/qt/bin/Release/tensorfence_qt.exe`
