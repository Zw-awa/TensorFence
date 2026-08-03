@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0qt.ps1" run %*
exit /b %ERRORLEVEL%
