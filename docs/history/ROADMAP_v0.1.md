# Roadmap

## v0.2 — Authentication and resilience
- OAuth2 client credentials + refresh tokens
- JWT/API-key/mTLS auth providers
- Redis cache and idempotency
- Rate limiting and circuit breaker
- Structured audit logs

## v0.3 — More systems
- Kafka, NATS, RabbitMQ
- PostgreSQL, SQL Server, MySQL, MongoDB
- S3-compatible object stores
- SFTP/FTP adapter
- Typed gRPC code generation workflow

## v0.4 — Workflow engine
- DAG-based operations
- Conditional steps
- Data dependencies between calls
- Retry/compensation policies
- Scheduled workflows

## v0.5 — AI/tool layer
- Tool schema export for agents
- Natural-language routing to registered operations
- Source-aware answer synthesis
- Local/OpenAI-compatible model support
- Guardrails, budgets and per-source policies

## v1.0 — Production platform
- Multi-tenant policy engine
- Secret manager integrations
- OpenTelemetry + Prometheus/Grafana
- Admin UI and connector catalog
- Versioned schemas/contracts
- Horizontal scaling and HA deployment examples
