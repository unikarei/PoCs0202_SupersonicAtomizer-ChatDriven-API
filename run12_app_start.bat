REM ------------------------------------------------------------------------------
REM Purpose:
REM   Start FastAPI development server (uvicorn with --reload) for this project.
REM   Intended as the primary local app startup entry point.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions

set "RUN12_SCRIPT_VERSION=v0.0.1"
set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src"
set "UVICORN_HOST=127.0.0.1"
set "UVICORN_PORT=8000"

cd /d %ROOT%

if not exist "%ROOT%src" (
  echo [Error] src directory not found: %ROOT%src
  exit /b 1
)

echo ========================================
echo      Start Supersonic Atomizer OptByAPI
echo ========================================
echo Script version : %RUN12_SCRIPT_VERSION%
echo Root           : %ROOT%
echo PYTHONPATH     : %PYTHONPATH%
echo URL            : http://%UVICORN_HOST%:%UVICORN_PORT%/
echo.
echo Running FastAPI app with auto-reload...
echo.

python -m uvicorn supersonic_atomizer_optbyapi.api.app:app --reload --host %UVICORN_HOST% --port %UVICORN_PORT%

endlocal
