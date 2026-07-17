@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py bootstrap.py
) else (
    python bootstrap.py
)

if errorlevel 1 pause
endlocal
