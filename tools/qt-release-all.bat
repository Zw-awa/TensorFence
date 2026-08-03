@echo off
call "%~dp0qt-build-release.bat" || exit /b 1
call "%~dp0qt-deploy-release.bat" || exit /b 1
call "%~dp0qt-run-release.bat" || exit /b 1
exit /b 0
