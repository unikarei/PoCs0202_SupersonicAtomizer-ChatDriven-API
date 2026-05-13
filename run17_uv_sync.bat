REM ------------------------------------------------------------------------------
REM Purpose:
REM   Compatibility wrapper for dependency synchronization.
REM   Delegates to run11_uv_sync.bat so teams/scripts can use run17 uniformly.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "ROOT=%~dp0"
set "TARGET=%ROOT%run11_uv_sync.bat"

cd /d %ROOT%

if not exist "%TARGET%" (
	echo [Error] Target script not found: %TARGET%
	exit /b 1
)

echo ========================================
echo        run17 wrapper - uv sync
echo ========================================
echo Delegating to: run11_uv_sync.bat
echo.

call "%TARGET%"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
	echo [OK] run17 wrapper completed successfully.
) else (
	echo [Error] run17 wrapper failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%