"""Contratos HTTP, compatibles con los campos de la primera versión."""
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Protocol(StrEnum):
    REST = "rest"
    GRAPHQL = "graphql"
    JSONRPC = "jsonrpc"
    SOAP = "soap"
    GRPC = "grpc"
    WEBHOOK = "webhook"
    PROVIDER = "provider"

class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    operation: str = Field(min_length=1, max_length=100)
    params: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    confirmed: bool = False
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)

class BatchItem(ExecuteRequest):
    alias: str | None = Field(default=None, max_length=80)

class BatchRequest(BaseModel):
    requests: list[BatchItem] = Field(min_length=1, max_length=20)
    fail_fast: bool = False

    @model_validator(mode="after")
    def unique_aliases(self):
        keys = [x.alias or f"item_{i}" for i, x in enumerate(self.requests)]
        if len(keys) != len(set(keys)):
            raise ValueError("Los alias deben ser únicos")
        return self

class AskRequest(BatchRequest):
    question: str = Field(min_length=1, max_length=4000)
    response_template: str | None = Field(default=None, max_length=2000)

class ReleaseRequest(BaseModel):
    """Liberar una reserva es una afirmación humana: alguien comprobó el resultado real."""
    model_config = ConfigDict(extra="forbid")
    confirmed: bool = False
    verified_outcome: str = Field(min_length=3, max_length=40, pattern=r"^[a-z_]+$")
    note: str | None = Field(default=None, max_length=500)

class UnifiedResponse(BaseModel):
    ok: bool
    system: str
    operation: str
    protocol: str
    status_code: int | None = None
    data: Any = None
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
