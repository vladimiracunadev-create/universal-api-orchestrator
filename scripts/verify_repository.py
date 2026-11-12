"""Verificación offline de sintaxis, catálogo, esquemas, ejemplos y enlaces Markdown locales."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".venv", ".git", "__pycache__", "build", "dist", ".pytest_cache", "htmlcov"}

MARKERS = ("Ã", "Â", "â€", "ðŸ")

def read_version() -> str:
    match = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise SystemExit("pyproject.toml sin versión declarada")
    return match.group(1)

def version_drift(version: str, operations: int, providers: int) -> list[str]:
    """La versión y los recuentos se declaran en varios sitios: deben coincidir siempre."""
    errors = []
    init = (ROOT / "src/universal_api_orchestrator/__init__.py").read_text(encoding="utf-8")
    if f'__version__ = "{version}"' not in init:
        errors.append("__init__.py: versión distinta de pyproject.toml")
    catalog = json.loads((ROOT / "config/catalog.json").read_text(encoding="utf-8"))
    if catalog.get("version") != version:
        errors.append("config/catalog.json: versión distinta de pyproject.toml")
    if catalog.get("operations") != operations:
        errors.append(f"config/catalog.json: operations={catalog.get('operations')} pero el catálogo tiene {operations}")
    if len(catalog.get("providers", [])) != providers:
        errors.append(f"config/catalog.json: providers={len(catalog.get('providers', []))} pero el catálogo tiene {providers}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"v{version}" not in readme.splitlines()[0]:
        errors.append("README.md: el título no declara la versión actual")
    return errors

def mojibake() -> list[str]:
    """Detecta UTF-8 leído como ANSI; un editor mal configurado rompe los acentos.

    El código entre comillas invertidas se excluye: un documento puede mostrar a propósito
    cómo se ve un archivo dañado, como hace AGENTS.md.
    """
    errors = []
    for path in sorted(ROOT.rglob("*.md")):
        if any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        prose = re.sub(r"```.*?```|`[^`]*`", "", text, flags=re.DOTALL)
        if any(marker in prose for marker in MARKERS) or "�" in prose:
            errors.append(f"{path.relative_to(ROOT)}: codificación sospechosa")
    return errors

def main() -> None:
    errors: list[str] = []
    files = [p for p in ROOT.rglob("*") if p.is_file() and not any(x in EXCLUDED or x.endswith(".egg-info") for x in p.relative_to(ROOT).parts)]
    for path in files:
        try:
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            elif path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix in {".yml", ".yaml"}:
                yaml.safe_load(path.read_text(encoding="utf-8"))
        except (SyntaxError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{path.relative_to(ROOT)}: {type(exc).__name__}")
    systems = yaml.safe_load((ROOT / "config/systems.yaml").read_text(encoding="utf-8"))["systems"]
    providers = {name: cfg for name, cfg in systems.items() if cfg.get("protocol") == "provider"}
    operations = sum(len(cfg["operations"]) for cfg in providers.values())
    for name, cfg in systems.items():
        if not cfg.get("allowed_hosts"):
            errors.append(f"{name}: allowed_hosts obligatorio")
        for operation, op in cfg.get("operations", {}).items():
            if op.get("effect") not in {"read", "write"}:
                errors.append(f"{name}.{operation}: effect inválido")
            if "input_schema" in op:
                jsonschema.Draft202012Validator.check_schema(op["input_schema"])
    example_count = 0
    for path in (ROOT / "examples/requests").glob("*.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        requests = value.get("requests", [value])
        for request in requests:
            try:
                op = systems[request["system"]]["operations"][request["operation"]]
                jsonschema.validate(request.get("params", {}), op.get("input_schema", {}))
                if op["effect"] == "write" and request.get("confirmed") is not False:
                    errors.append(f"{path.name}: las escrituras de ejemplo deben tener confirmed=false")
            except (KeyError, jsonschema.ValidationError) as exc:
                errors.append(f"{path.name}: {type(exc).__name__}")
        example_count += 1
    for path in files:
        if path.suffix != ".md" or "history" in path.parts:
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            clean = unquote(target.split("#")[0])
            if clean and not (path.parent / clean).exists():
                errors.append(f"{path.relative_to(ROOT)}: enlace inexistente {target}")
    version = read_version()
    errors.extend(version_drift(version, operations, len(providers)))
    errors.extend(mojibake())
    result = {"ok": not errors, "version": version, "providers": len(providers), "provider_operations": operations, "request_examples": example_count, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
