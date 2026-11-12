"""Catálogo local confiable. Las peticiones externas no pueden modificarlo."""
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class SystemDisabled(ValueError):
    """El sistema existe en el catálogo pero está apagado de forma explícita."""


class MissingConfiguration(ValueError):
    """Falta una variable de entorno declarada por el catálogo."""


class SystemRegistry:
    def __init__(self, path: str):
        self.path = Path(path)
        self._systems = self._load()

    def _load(self) -> dict[str, Any]:
        paths = sorted(self.path.glob("*.yaml")) if self.path.is_dir() else [self.path]
        systems = {}
        for path in paths:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(raw, dict):
                raise ValueError(f"Catálogo inválido: {path.name} no define un mapa")
            declared = raw.get("systems", {})
            if not isinstance(declared, dict):
                raise ValueError(f"Catálogo inválido: 'systems' debe ser un mapa en {path.name}")
            for name, cfg in declared.items():
                if name in systems:
                    raise ValueError(f"Sistema duplicado: {name}")
                if not isinstance(cfg, dict):
                    raise ValueError(f"Definición inválida: {name}")
                if not isinstance(cfg.get("operations", {}), dict):
                    raise ValueError(f"Operaciones inválidas: {name}")
                cfg["_name"] = name
                systems[name] = cfg
        return systems

    def reload(self) -> int:
        """Relee el catálogo sin reiniciar el proceso. Si el archivo es inválido, conserva el anterior."""
        loaded = self._load()
        self._systems = loaded
        return len(loaded)

    def _expand_env(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {k: self._expand_env(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._expand_env(v) for v in value]
        if isinstance(value, str):
            def expand(match):
                key = match.group(1)
                val = os.getenv(key)
                if not val:
                    raise MissingConfiguration(f"Falta variable de configuración: {key}")
                return val
            return re.sub(r"\$\{([A-Z_][A-Z0-9_]*)\}", expand, value)
        return value

    def has(self, name: str) -> bool:
        return name in self._systems

    def get_system(self, name: str) -> dict[str, Any]:
        if name not in self._systems:
            raise KeyError(f"Sistema desconocido: {name}")
        cfg = deepcopy(self._systems[name])
        if cfg.get("enabled", True) is False:
            raise SystemDisabled(f"Sistema deshabilitado: {name}")
        return self._expand_env(cfg)

    @staticmethod
    def _public(cfg: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocol": cfg.get("protocol"), "provider": cfg.get("provider"),
            "enabled": cfg.get("enabled", True),
            "description": cfg.get("description", ""),
            "sensitive": cfg.get("sensitive", False),
            "operations": list(cfg.get("operations", {})),
            "capabilities": {op: {
                "effect": val.get("effect", "read" if val.get("method", "POST") in ["GET", "HEAD"] else "write"),
                "description": val.get("description", ""),
                "input_schema": val.get("input_schema", {}),
            } for op, val in cfg.get("operations", {}).items()},
        }

    def list_public(self) -> dict[str, Any]:
        return {name: self._public(cfg) for name, cfg in self._systems.items()}

    def public_system(self, name: str) -> dict[str, Any]:
        """Ficha de un solo sistema, sin credenciales ni URLs internas."""
        if name not in self._systems:
            raise KeyError(f"Sistema desconocido: {name}")
        return self._public(self._systems[name])
