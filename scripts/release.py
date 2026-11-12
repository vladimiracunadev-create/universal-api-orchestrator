"""Crear ZIP de código (raíz plana), sin estados, secretos, builds ni cachés."""
from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__", "data", "secrets", "dist", "build", "htmlcov"}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(ROOT.rglob("*")):
        parts = path.relative_to(ROOT).parts
        if not path.is_file() or path == output or any(p in EXCLUDED or p.endswith(".egg-info") for p in parts):
            continue
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            continue
        if path.suffix in {".pyc", ".db", ".sqlite", ".sqlite3", ".pem", ".key", ".zip"} or path.name in {".coverage", "coverage.xml", "junit.xml"}:
            continue
        files.append(path)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), date_time=(2026, 9, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"{len(files)} archivos; {output.stat().st_size} bytes; SHA256 {digest}")

if __name__ == "__main__":
    main()
