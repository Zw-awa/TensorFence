@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

if "%QT_ROOT%"=="" (
  echo [ERROR] QT_ROOT is not set.
  echo Example: set QT_ROOT=path-to-your-qt-kit
  exit /b 1
)

if not exist "%QT_ROOT%\bin\qt-cmake.bat" (
  echo [ERROR] qt-cmake.bat was not found under QT_ROOT.
  echo QT_ROOT=%QT_ROOT%
  exit /b 1
)

if "%VCVARS64_BAT%"=="" (
  echo [ERROR] VCVARS64_BAT is not set.
  echo Example: set VCVARS64_BAT=path-to-vcvars64.bat
  exit /b 1
)

if not exist "%VCVARS64_BAT%" (
  echo [ERROR] VCVARS64_BAT does not exist.
  echo VCVARS64_BAT=%VCVARS64_BAT%
  exit /b 1
)

if "%QT_BUILD_DIR%"=="" set "QT_BUILD_DIR=%REPO_ROOT%\build\qt-qml-release"
if "%QT_GENERATOR%"=="" set "QT_GENERATOR=Ninja"

call "%VCVARS64_BAT%" || exit /b 1
call "%QT_ROOT%\bin\qt-cmake.bat" -S "%REPO_ROOT%" -B "%QT_BUILD_DIR%" -G "%QT_GENERATOR%" -DCMAKE_BUILD_TYPE=Release
exit /b %ERRORLEVEL%
