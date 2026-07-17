@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py environment_check.py
) else (
    python environment_check.py
)

pause
endlocal
