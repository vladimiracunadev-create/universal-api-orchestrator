from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from universal_api_orchestrator.config import settings
from universal_api_orchestrator.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(str(tmp_path/"state.sqlite3"),Fernet.generate_key().decode())

@pytest.fixture
def app_settings(monkeypatch,tmp_path):
    monkeypatch.setattr(settings,"state_db",str(tmp_path/"state.sqlite3"))
    monkeypatch.setattr(settings,"state_key",Fernet.generate_key().decode())
    monkeypatch.setattr(settings,"gateway_api_key","g"*32)
    monkeypatch.setattr(settings,"approval_api_key","a"*32)
    monkeypatch.setattr(settings,"systems_config",str(Path("config/systems.yaml").resolve()))
    monkeypatch.setattr(settings,"allow_writes",False)
    monkeypatch.setattr(settings,"ai_mode","off")
    return settings
