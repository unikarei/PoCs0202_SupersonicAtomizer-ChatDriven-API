# Supersonic Atomizer OptByAPI - Setup & Startup Guide

## Quick Setup (First Time)

### Step 1: Install uv (if not already installed)
```powershell
# Windows - using choco or direct download
# See: https://docs.astral.sh/uv/
```

### Step 2: Create Virtual Environment
```powershell
.\run10_uv_venv.bat
```
Creates `.venv/` directory with isolated Python environment.

### Step 3: Sync Dependencies
```powershell
.\run11_uv_sync.bat
```
This downloads all dependencies defined in `pyproject.toml` and syncs the environment using `uv.lock`.

### Step 4: Activate Virtual Environment
**PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

**Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

After activation, your terminal prompt will change to show `(.venv)` prefix.

### Step 5: Start the Application
```powershell
.\run12_app_start.bat
```

Opens the GUI at: **http://127.0.0.1:8000/**

---

## Development Workflow

### Run the App (after venv activated)
```powershell
.\run12_app_start.bat
```
- Starts FastAPI with auto-reload
- Changes to files are reflected immediately

### Run Tests
```powershell
.\run14_uv_test.bat
# Or with specific test file:
.\run14_uv_test.bat tests/test_phase1_api.py
```

### Add Production Dependencies
```powershell
.\run16_uv_add_prd.bat numpy scipy
```
Updates `pyproject.toml` and lock file.

### Add Development Dependencies
```powershell
.\run15_uv_add_dev.bat pytest ruff mypy
```
Adds to `[dependency-groups] dev` section.

---

## File Organization

| File | Purpose |
|------|---------|
| `run10_uv_venv.bat` | Create virtual environment |
| `run11_uv_sync.bat` | Sync all dependencies from `pyproject.toml` |
| `run12_app_start.bat` | Start FastAPI application (main entry point) |
| `run13_uv_run.bat` | Execute arbitrary command via `uv run` |
| `run14_uv_test.bat` | Run pytest test suite |
| `run15_uv_add_dev.bat` | Add dev package dependency (testing, linting, etc.) |
| `run16_uv_add_prd.bat` | Add production package dependency |

Dependency update flow:
- Add packages with `run15_uv_add_dev.bat` or `run16_uv_add_prd.bat`
- Then run `run11_uv_sync.bat` to apply updated lock/dependencies to the local environment

---

## Troubleshooting

### "uv is not installed or not in PATH"
- Install uv: https://docs.astral.sh/uv/
- Verify: `where uv`

### "src directory not found"
- Ensure you run from project root
- Check `.venv\Scripts\activate.bat` is loaded

### Port 8000 already in use
- Edit `run12_app_start.bat` and change `%UVICORN_PORT%` to another port (e.g., 8001)

---

## Project Structure
```
d:\usr8_work\work_23_chatgpt\16_PoCs\0202_SupersonicAtomizer_OptByAPI
├── src/                      # Application source code
│   └── supersonic_atomizer_optbyapi/
│       ├── api/              # FastAPI app, routes, static files
│       ├── services/         # Business logic
│       ├── models.py         # Data models
│       ├── config.py         # Configuration
│       └── __init__.py
├── tests/                     # Test suite
├── docs/                      # Documentation
├── workspace/                 # Project working directory (runtime)
├── pyproject.toml             # Project metadata & dependencies
├── run10_uv_venv.bat          # Setup scripts
├── run11_uv_sync.bat          # ...
├── run12_app_start.bat        # Start app (main command)
├── ... (other run scripts)
└── .venv/                     # Virtual environment (created by run10)
```

---

## Key Commands Summary

| Task | Command |
|------|---------|
| First-time setup | `run10`, then `run11`, then activate `.venv`, then `run12` |
| Daily startup | Activate `.venv`, then `run12_app_start.bat` |
| Run tests | `run14_uv_test.bat` |
| Add dependency | `run16_uv_add_prd.bat <package>` or `run15_uv_add_dev.bat <package>` |

Role mapping (current naming):
- `run10` = `uv venv`
- `run11` = `uv sync`

---

## Notes

- Keep `.venv/` in `.gitignore` (large directory)
- Always activate virtual environment before running scripts manually
- `run12_app_start.bat` will not start if venv is not active
- Dependencies are locked in `uv.lock` for reproducibility
