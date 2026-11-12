# Universal API Orchestrator

A protocol-agnostic gateway that connects heterogeneous systems, normalizes their schemas and composes unified responses.

> The goal is not to hard-code “every API in existence”. The goal is to make new APIs **configurable or pluggable** behind one stable contract.

## What it supports

- REST / HTTP APIs
- OpenAPI-friendly HTTP services
- GraphQL over HTTP
- JSON-RPC 2.0
- SOAP/XML
- gRPC (generic raw adapter + extension point for generated protobuf clients)
- Webhook ingestion
- Parallel multi-system execution
- Schema normalization with JMESPath
- Unified success/error envelope
- Deterministic response composition
- Host allowlists + SSRF guard
- Docker + GitHub Actions + tests

## Use cases

- One backend for ERP + CRM + e-commerce + payments + logistics.
- Data federation across legacy and modern systems.
- API aggregation for agents/LLMs without exposing provider-specific details.
- Migration layer while old and new platforms coexist.
- BFF/API gateway for web/mobile applications.
- Cross-system automation and operational dashboards.

## Quick start

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
python -m pip install -e '.[dev]'
uvicorn universal_api_orchestrator.main:app --reload --port 8080
```

Open:

- Swagger UI: `http://localhost:8080/docs`
- OpenAPI document: `http://localhost:8080/openapi.json`
- Health: `http://localhost:8080/health`

Or:

```bash
cp .env.example .env
docker compose up --build
```

## Unified execution

```bash
curl -X POST http://localhost:8080/v1/execute \
  -H 'content-type: application/json' \
  -d '{
    "system": "jsonplaceholder",
    "operation": "get_post",
    "params": {"id": 1}
  }'
```

Every connector returns the same envelope:

```json
{
  "ok": true,
  "system": "jsonplaceholder",
  "operation": "get_post",
  "protocol": "rest",
  "status_code": 200,
  "data": {"id": 1, "title": "...", "body": "..."},
  "error": null,
  "meta": {"elapsed_ms": 123.45}
}
```

## Query several systems at once

`POST /v1/batch` runs independent integrations concurrently:

```json
{
  "requests": [
    {
      "alias": "post",
      "system": "jsonplaceholder",
      "operation": "get_post",
      "params": {"id": 1}
    },
    {
      "alias": "country",
      "system": "countries_graphql_demo",
      "operation": "country",
      "params": {"code": "CL"}
    }
  ]
}
```

## Generate a composed response

`POST /v1/ask` executes all requested sources and produces one deterministic response object:

```json
{
  "question": "Combine the information from these systems",
  "requests": [
    {"alias":"a","system":"jsonplaceholder","operation":"get_post","params":{"id":1}},
    {"alias":"b","system":"countries_graphql_demo","operation":"country","params":{"code":"CL"}}
  ]
}
```

The response engine is deliberately independent of an LLM. You can later add OpenAI-compatible, local, rule-based or domain-specific generation without coupling integrations to one AI vendor.

## Configuration model

```yaml
systems:
  my_api:
    protocol: rest
    base_url: https://api.example.com
    allowed_hosts: [api.example.com]
    headers:
      Authorization: ${MY_API_TOKEN}
    operations:
      get_customer:
        method: GET
        path: /customers/{id}
        response_map:
          id: id
          name: customer.profile.name
```

Provider secrets stay in environment variables, not source control.

## Repository structure

```text
.
├── config/systems.yaml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONNECTOR_MATRIX.md
│   └── ADDING_CONNECTOR.md
├── examples/curl.sh
├── src/universal_api_orchestrator/
│   ├── adapters/
│   │   ├── rest.py
│   │   ├── graphql.py
│   │   ├── jsonrpc.py
│   │   ├── soap.py
│   │   └── grpc_adapter.py
│   ├── main.py
│   ├── models.py
│   ├── normalizer.py
│   ├── orchestrator.py
│   ├── registry.py
│   ├── response_engine.py
│   └── security.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Extending toward a production integration platform

The next layer should add:

- OAuth2/OIDC, mTLS, JWT signing and cloud-native auth providers.
- OpenAPI import that creates operations automatically.
- Async event adapters: Kafka, NATS, RabbitMQ, SQS/Pub/Sub.
- Databases as data sources: SQL Server, PostgreSQL, MySQL, MongoDB.
- Redis caching, idempotency keys, rate limiting and circuit breakers.
- OpenTelemetry + Prometheus/Grafana.
- Workflow/DAG composition with dependencies between calls.
- Transformation DSL / JSONata in addition to JMESPath.
- Secret stores: Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault.
- Policy/tenancy layer.
- Optional AI synthesis and tool-calling interface.

## Security notes

This project intentionally blocks private/reserved network targets by default and supports per-system host allowlists. In production, combine this with network egress controls, secret management, TLS verification, request-size limits, authentication, authorization, audit logging, and provider-specific rate limits.

## License

MIT.

## Optional natural-language answers

Set `AI_MODE=openai_compatible`, a model name, base URL and optional API key. The `/v1/ask` endpoint will then send the already-normalized API results to any service that implements the common `/v1/chat/completions` shape. With `AI_MODE=off` (default), the project remains fully deterministic and does not call an AI model.

## Import an OpenAPI description

```bash
python tools/import_openapi.py ./provider-openapi.yaml --name provider --output provider.system.yaml
```

This creates a starter REST system definition from `servers`, `paths`, HTTP methods and `operationId`. Review authentication, request bodies, parameter placement and response mappings before production use.
