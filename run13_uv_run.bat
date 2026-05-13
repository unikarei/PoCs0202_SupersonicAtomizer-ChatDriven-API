REM ------------------------------------------------------------------------------
REM Purpose: Run commands through uv. No need to run under run10_uv_venv.
REM   Execute an arbitrary command through uv-managed environment.
REM   Useful for one-shot commands without manual venv activation.
REM   
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN13_SCRIPT_VERSION=v0.0.2"

cd /d %~dp0

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    exit /b 1
)

if "%~1"=="" (
    echo Usage: run13_uv_run.bat ^<command^> [args ...]
    echo.
    echo Examples:
    echo   run13_uv_run.bat python -m pip list
    echo   run13_uv_run.bat pytest tests/test_phase1_api.py -v
    exit /b 1
)

echo ========================================
echo             uv run passthrough
echo ========================================
echo Script version : %RUN13_SCRIPT_VERSION%
echo Project root   : %CD%
echo.
echo Running: uv run %*
uv run %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] uv run command completed successfully.
) else (
    echo [Error] uv run command failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
