@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

if "%VCVARS64_BAT%"=="" (
  echo [ERROR] VCVARS64_BAT is not set.
  exit /b 1
)

if "%QT_BUILD_DIR%"=="" set "QT_BUILD_DIR=%REPO_ROOT%\build\qt-qml-release"

call "%VCVARS64_BAT%" || exit /b 1
cmake --build "%QT_BUILD_DIR%" --config Release
exit /b %ERRORLEVEL%
