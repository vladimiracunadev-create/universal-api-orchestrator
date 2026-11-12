#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -e '.[auth,dev]'
.venv/bin/python scripts/bootstrap.py
exec .venv/bin/python -m uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --workers 1 --no-access-log
