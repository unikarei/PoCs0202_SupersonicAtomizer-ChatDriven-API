REM ------------------------------------------------------------------------------
REM Purpose:Run tests through uv.
REM   Run project tests through uv-managed environment.
REM   Defaults to tests/ with verbose output, or passes custom pytest args.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN14_SCRIPT_VERSION=v0.0.2"

cd /d %~dp0

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    exit /b 1
)

echo ========================================
echo            Run Tests with uv
echo ========================================
echo Script version : %RUN14_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if "%~1"="" (
    echo Running: uv run pytest tests/ -v
    uv run pytest tests/ -v
) else (
    echo Running: uv run pytest %*
    uv run pytest %*
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] Test command completed successfully.
) else (
    echo [Warn] Test command finished with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
