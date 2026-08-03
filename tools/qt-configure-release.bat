@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0qt.ps1" configure %*
exit /b %ERRORLEVEL%
