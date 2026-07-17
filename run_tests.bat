@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -m pytest -q
) else (
    python -m pytest -q
)

pause
endlocal
