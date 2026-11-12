"""Configuración del proceso; nunca incluye credenciales en respuestas públicas."""
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Expande también las variables utilizadas por los catálogos YAML.
load_dotenv(override=False)

class Settings(BaseSettings):
    app_name: str = "Universal API Orchestrator"
    app_env: str = "development"
    systems_config: str = "config/systems.yaml"
    gateway_api_key: str = ""
    approval_api_key: str = ""
    allow_writes: bool = False
    state_key: str = ""
    state_db: str = "data/state.sqlite3"
    request_timeout_seconds: float = Field(20, gt=0, le=120)
    max_concurrency: int = Field(8, ge=1, le=100)
    max_request_bytes: int = 2_000_000
    max_response_bytes: int = 4_000_000
    allow_private_networks: bool = False
    log_level: str = "INFO"
    # Pool HTTP compartido: evita un handshake TLS por operación.
    http_max_connections: int = Field(50, ge=1, le=1000)
    http_max_keepalive_connections: int = Field(20, ge=0, le=1000)
    http_keepalive_expiry_seconds: float = Field(30, gt=0, le=600)
    # Control de carga local por clave de llamada; 0 desactiva el límite.
    rate_limit_per_minute: int = Field(120, ge=0, le=100000)
    rate_limit_burst: int = Field(30, ge=1, le=10000)
    # Retención del estado local; la purga es explícita, nunca automática.
    events_retention_days: int = Field(30, ge=1, le=3650)
    requests_retention_days: int = Field(90, ge=1, le=3650)
    ai_mode: str = "off"
    ai_allow_sensitive_data: bool = False
    ai_max_input_chars: int = 24000
    openai_compatible_api_key: str = ""
    openai_compatible_base_url: str = "https://api.openai.com"
    openai_compatible_model: str = ""
    ai_allowed_host: str = "api.openai.com"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
