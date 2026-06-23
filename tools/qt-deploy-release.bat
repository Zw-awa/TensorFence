@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

if "%QT_ROOT%"=="" (
  echo [ERROR] QT_ROOT is not set.
  exit /b 1
)

if "%QT_BUILD_DIR%"=="" set "QT_BUILD_DIR=%REPO_ROOT%\build\qt-qml-release"
if "%QT_EXE%"=="" set "QT_EXE=%QT_BUILD_DIR%\bin\tensorfence_qt.exe"

if not exist "%QT_EXE%" (
  echo [ERROR] Built executable was not found.
  echo QT_EXE=%QT_EXE%
  exit /b 1
)

call "%QT_ROOT%\bin\windeployqt.exe" --qmldir "%REPO_ROOT%\src\tensorfence\qt\app" "%QT_EXE%"
exit /b %ERRORLEVEL%
