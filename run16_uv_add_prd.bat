REM ------------------------------------------------------------------------------
REM Purpose:
REM   Add runtime (production) dependencies required by the application.
REM   Updates pyproject.toml and uv.lock for deploy/runtime packages.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN16_SCRIPT_VERSION=v0.0.1"

cd /d %~dp0

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    exit /b 1
)

echo ========================================
echo      Add Production Packages
echo ========================================
echo Script version : %RUN16_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if "%~1"=="" (
    echo Usage: run16_uv_add_prd.bat ^<package^> [package2 ...]
    echo.
    echo Examples:
    echo   run16_uv_add_prd.bat numpy
    echo   run16_uv_add_prd.bat numpy scipy
    exit /b 1
)

echo Adding runtime dependencies: %*
uv add %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] Runtime dependency added successfully.
) else (
    echo [Error] uv add failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
