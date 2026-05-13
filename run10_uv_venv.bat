REM ------------------------------------------------------------------------------
REM Purpose:
REM   Create local virtual environment (.venv) using uv.
REM   Run once after sync, then activate .venv before day-to-day development.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN11_SCRIPT_VERSION=v0.0.1"

cd /d %~dp0

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    echo         Install uv first: https://docs.astral.sh/uv/
    exit /b 1
)

echo ========================================
echo         uv venv - Create Virtual Env
echo ========================================
echo Script version : %RUN11_SCRIPT_VERSION%
echo Project root   : %CD%
echo.
echo Running: uv venv
echo.

uv venv

echo.
echo Done! Next step:
echo   .venv\Scripts\Activate.ps1  (PowerShell)
echo   .venv\Scripts\activate.bat  (Command Prompt)
echo.
echo After activation, run:
echo   run12_app_start.bat
echo.

endlocal
