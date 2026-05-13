REM ------------------------------------------------------------------------------
REM Purpose:
REM   Synchronize project dependencies from pyproject.toml/uv.lock into local env.
REM   Use this first when setting up or after dependency changes.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN10_SCRIPT_VERSION=v0.0.2"

cd /d %~dp0

where uv >nul 2>nul
if errorlevel 1 (
	echo [Error] uv is not installed or not in PATH.
	echo         Install uv first: https://docs.astral.sh/uv/
	exit /b 1
)

echo ========================================
echo              uv sync Script
echo ========================================
echo Script version : %RUN10_SCRIPT_VERSION%
echo Project root   : %CD%
echo.
echo Running: uv sync
uv sync
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
	echo [OK] uv sync completed successfully.
) else (
	echo [Error] uv sync failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
