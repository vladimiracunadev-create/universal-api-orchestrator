$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (!(Test-Path ".venv")) { py -3.12 -m venv .venv; if ($LASTEXITCODE -ne 0) { throw "Instale Python 3.12" } }
& .\.venv\Scripts\python.exe -m pip install -e ".[auth,dev]"
if ($LASTEXITCODE -ne 0) { throw "Falló instalación" }
& .\.venv\Scripts\python.exe scripts/bootstrap.py
& .\.venv\Scripts\python.exe -m uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --workers 1 --no-access-log
