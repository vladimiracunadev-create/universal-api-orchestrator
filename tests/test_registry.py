from pathlib import Path

from universal_api_orchestrator.registry import SystemRegistry


def test_registry_loads_systems(tmp_path: Path):
    path = tmp_path / "systems.yaml"
    path.write_text(
        "systems:\n  demo:\n    protocol: rest\n    base_url: https://example.com\n    operations:\n      ping:\n        method: GET\n        path: /\n",
        encoding="utf-8",
    )
    registry = SystemRegistry(str(path))
    assert registry.get_system("demo")["protocol"] == "rest"
    assert registry.list_public()["demo"]["operations"] == ["ping"]
