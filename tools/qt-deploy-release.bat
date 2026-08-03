@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0qt.ps1" deploy %*
exit /b %ERRORLEVEL%
