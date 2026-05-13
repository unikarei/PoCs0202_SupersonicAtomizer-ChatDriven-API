REM ------------------------------------------------------------------------------
REM Purpose:
REM   Add development dependencies to the dev dependency group.
REM   Updates pyproject.toml and uv.lock for tooling/test-only packages.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN15_SCRIPT_VERSION=v0.0.1"

cd /d %~dp0

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    exit /b 1
)

echo ========================================
echo       Add Dev Packages (--group dev)
echo ========================================
echo Script version : %RUN15_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if "%~1"="" (
    echo Usage: run15_uv_add_dev.bat ^<package^> [package2 ...]
    echo.
    echo Examples:
    echo   run15_uv_add_dev.bat ruff
    echo   run15_uv_add_dev.bat mypy ruff
    exit /b 1
)

echo Adding to dev group: %*
uv add --group dev %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] Dev dependency added successfully.
) else (
    echo [Error] uv add --group dev failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
