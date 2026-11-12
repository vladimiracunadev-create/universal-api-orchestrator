"""Ejecuta una prueba de integración sin red ni credenciales reales; todos los datos son simulados."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
print("MODO SIMULADO: no se contacta ningún proveedor ni se envían mensajes.", flush=True)
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "tests/test_orchestrator_api.py", "-q"], cwd=root))
