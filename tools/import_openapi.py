#!/usr/bin/env python3
"""Generate a starter systems.yaml fragment from an OpenAPI JSON/YAML document."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import yaml


def load_spec(path: Path):
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)


def build_fragment(spec, name: str):
    servers = spec.get("servers") or []
    base_url = servers[0].get("url", "https://api.example.com") if servers else "https://api.example.com"
    host = urlparse(base_url).hostname or "api.example.com"
    operations = {}
    for route, item in (spec.get("paths") or {}).items():
        for method in ("get", "post", "put", "patch", "delete", "head"):
            if method not in item:
                continue
            op = item[method]
            op_name = op.get("operationId") or f"{method}_{route.strip('/').replace('/', '_').replace('{', '').replace('}', '') or 'root'}"
            operations[op_name] = {"method": method.upper(), "path": route, "effect": "read" if method in {"get", "head"} else "write"}
    return {
        "systems": {
            name: {
                "protocol": "rest",
                "enabled": False,
                "base_url": base_url,
                "allowed_hosts": [host],
                "operations": operations,
            }
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", default="generated-system.yaml")
    args = parser.parse_args()
    fragment = build_fragment(load_spec(Path(args.spec)), args.name)
    Path(args.output).write_text(yaml.safe_dump(fragment, sort_keys=False), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
