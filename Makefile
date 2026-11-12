.PHONY: install test run lint
install:
	python -m pip install -e '.[auth,dev]'
	python scripts/bootstrap.py
test:
	python -m pytest -q
lint:
	python -m ruff check src tests tools scripts
run:
	python -m uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --workers 1 --no-access-log
