# 05 · Referencia técnica

Contratos exactos: rutas, modelos, funciones públicas y códigos de error. Para el razonamiento, el [capítulo 06](06-deep-code-explanation.md); para el uso, [API_GUIDE](../API_GUIDE.md).

## Rutas HTTP

13 rutas publicadas en OpenAPI. `X-API-Key` significa clave del gateway; `X-Approval-Key`, clave de aprobación.

| Método y ruta | Claves | Cuerpo | Respuesta |
|---|---|---|---|
| `GET /health` | ninguna | — | `{"status":"ok","version":"0.3.0"}` |
| `GET /v1/systems` | API key | — | mapa de sistemas públicos |
| `GET /v1/systems/{system}` | API key | — | ficha de un sistema, o 404 |
| `POST /v1/execute` | API key (+ aprobación si escribe) | `ExecuteRequest` | `UnifiedResponse` |
| `POST /v1/batch` | API key (+ aprobación si escribe) | `BatchRequest` | mapa alias → `UnifiedResponse` |
| `POST /v1/ask` | API key | `AskRequest` | composición con fuentes |
| `GET /v1/events` | API key | — | `{"events":[...]}` |
| `POST /v1/events/{event_id}/ack` | API key + aprobación | — | `{"ok":true\|false}` |
| `GET /v1/reconciliation` | API key | — | `{"pending":[...],"guidance":"..."}` |
| `POST /v1/reconciliation/{reservation_id}/release` | API key + aprobación | `ReleaseRequest` | `{"released":true,...}` |
| `GET /v1/stats` | API key | — | versión, política y recuentos |
| `POST /v1/admin/reload` | API key + aprobación | — | `{"reloaded":true,"systems":N}` |
| `GET/POST /v1/webhooks/{system}` | firma del proveedor | según proveedor | challenge o recuento de eventos |

Parámetros de consulta: `/v1/events` acepta `limit` (1–100, por defecto 50) y `after` (≥0); `/v1/reconciliation` acepta `limit` (1–200, por defecto 50).

Cabeceras de toda respuesta: `X-Request-Id`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, y `X-RateLimit-Remaining` cuando el control de carga está activo.

## Modelos

### `ExecuteRequest`

| Campo | Tipo | Restricción |
|---|---|---|
| `system` | str | 1–80, patrón `^[a-zA-Z0-9_-]+$` |
| `operation` | str | 1–100 |
| `params` | objeto | validado contra el `input_schema` de la operación |
| `headers` | objeto de str | solo las que el sistema declare en `allowed_request_headers` |
| `confirmed` | bool | `false` por defecto |
| `idempotency_key` | str o nulo | 8–128 caracteres; obligatoria para escribir |

`extra="forbid"`: un campo desconocido produce 422, no se ignora en silencio.

### `BatchItem`, `BatchRequest` y `AskRequest`

`BatchItem` es `ExecuteRequest` más `alias` (hasta 80 caracteres). `BatchRequest` lleva `requests` (1–20) y `fail_fast`, y valida que los alias resultantes sean únicos; sin alias se generan `item_0`, `item_1`… `AskRequest` añade `question` (1–4000) y `response_template` (hasta 2000), que admite `{question}`, `{data}` y `{errors}`.

### `ReleaseRequest`

| Campo | Tipo | Restricción |
|---|---|---|
| `confirmed` | bool | debe ser `true` o la petición se rechaza con 403 |
| `verified_outcome` | str | 3–40, patrón `^[a-z_]+$`, y uno de los tres admitidos |
| `note` | str o nulo | hasta 500 caracteres |

Valores de `verified_outcome`: `not_delivered`, `delivered_duplicate_acceptable` (ambos liberan) y `delivered_do_not_retry` (conserva la reserva y responde 409).

### `UnifiedResponse`

| Campo | Significado |
|---|---|
| `ok` | éxito de la **operación**, no del HTTP externo |
| `system`, `operation`, `protocol` | qué se ejecutó y por qué transporte |
| `status_code` | código del proveedor, o el del error del gateway; nulo si no hubo HTTP |
| `data` | payload normalizado si hay `response_map`, o el original |
| `error` | código estable, nulo si `ok` |
| `meta` | ver abajo |

Claves de `meta`: `trace_id` siempre; `elapsed_ms` siempre; `effect`, `sensitive` y `delivery` en el camino correcto; `idempotent_replay` en una repetición servida desde la reserva; `requires_reconciliation` y `reservation_id` cuando una escritura falló después de reservar.

## Funciones públicas por módulo

### `registry.SystemRegistry`

| Función | Devuelve | Lanza |
|---|---|---|
| `has(name)` | bool | — |
| `get_system(name)` | configuración expandida | `KeyError`, `SystemDisabled`, `MissingConfiguration` |
| `list_public()` | mapa de sistemas sin secretos | — |
| `public_system(name)` | ficha de uno | `KeyError` |
| `reload()` | número de sistemas cargados | `ValueError`, `OSError` (conserva el anterior) |

### `orchestrator.Orchestrator`

`resolve(system, operation)` devuelve la pareja sistema/operación o lanza `IntegrationError`. `execute(...)` devuelve siempre un `UnifiedResponse` y **no propaga excepciones**. `batch(items, fail_fast, approved, read_only)` devuelve el mapa por alias.

### `store.Store`

| Función | Devuelve | Nota |
|---|---|---|
| `token_get/token_put(name, …)` | valor descifrado / nada | Fernet |
| `digest(value)` | SHA-256 hexadecimal | también calcula `reservation_id` |
| `reserve(key, request)` | resultado guardado, o `None` si reservó | lanza `IDEMPOTENCY_CONFLICT` u `OUTCOME_PENDING_OR_UNKNOWN_RECONCILE` |
| `complete(key, value)` | nada | cierra la reserva |
| `pending(limit)` | lista de reservas en duda | sin contenido del mensaje |
| `release(reservation_id)` | bool | nunca toca una completada |
| `event_add(source, key, payload)` | bool: `True` si era nuevo | deduplica |
| `events(limit, after)` | eventos sin reconocer | descifrados |
| `ack(event_id)` | bool | reconocimiento local |
| `prune(days)` / `prune_requests(days)` | filas borradas | solo reconocidos / solo completadas |
| `stats()` | cinco recuentos | sin contenidos |

### `transport`

`get_client()`, `close_client()`, `bounded_timeout(value)`, `retry_delay(header, attempt)` y `request(method, url, allowed_hosts, *, timeout=None, **kwargs)`.

### `security`, `ratelimit`, `webhooks`, `response_engine`

`assert_safe_endpoint(url, allowed_hosts)` y `safe_caller_headers(headers, allowed)`. `RateLimiter(per_minute, burst, max_identities)` con `identity()` y `check()`. `verify_signature(kind, secret, raw, headers, now=None)` y `extract_events(kind, payload, raw, headers)`. `compose_answer(question, results, template=None)`.

## Códigos de error

### Del gateway, como HTTP

| Código | HTTP | Causa |
|---|---|---|
| `GATEWAY_KEY_NOT_CONFIGURED` | 503 | clave del gateway ausente o menor de 24 caracteres |
| `INVALID_API_KEY` | 401 | no coincide |
| `APPROVAL_REQUIRED` | 403 | falta la clave de aprobación |
| `ACK_APPROVAL_REQUIRED` | 403 | reconocer un evento sin aprobación |
| `REQUEST_TOO_LARGE` | 413 | supera `MAX_REQUEST_BYTES` |
| `RATE_LIMIT_EXCEEDED` | 429 | límite local; trae `Retry-After` |
| `SYSTEM_NOT_FOUND` | 404 | ficha de un sistema inexistente |
| `INVALID_RESERVATION_ID` | 400 | no es un SHA-256 de 64 hexadecimales |
| `RELEASE_CONFIRMATION_REQUIRED` | 403 | falta `confirmed:true` |
| `UNKNOWN_VERIFIED_OUTCOME` | 422 | resultado declarado no admitido |
| `RESERVATION_KEPT_TO_PREVENT_DUPLICATE` | 409 | `delivered_do_not_retry` |
| `RESERVATION_NOT_FOUND_OR_ALREADY_COMPLETE` | 404 | nada que liberar |
| `INVALID_CATALOG_PREVIOUS_KEPT` | 422 | recarga con YAML inválido |
| `WEBHOOK_NOT_CONFIGURED` | 404 | sistema sin webhook o deshabilitado |
| `INVALID_WEBHOOK_SIGNATURE` | 401 | firma incorrecta |
| `INVALID_VERIFICATION_TOKEN` | 401 | challenge de Meta incorrecto |
| `INVALID_EVENT` | 400 | cuerpo no interpretable |

### Dentro del sobre unificado

| Código | `status_code` | Causa |
|---|---|---|
| `SYSTEM_NOT_FOUND` | 404 | el sistema no está en el catálogo |
| `SYSTEM_DISABLED` | 409 | está apagado |
| `OPERATION_NOT_FOUND` | 404 | la operación no existe en ese sistema |
| `SYSTEM_CONFIGURATION_INCOMPLETE` | 503 | falta una variable declarada |
| `INVALID_INPUT_SCHEMA` | 422 | los parámetros no validan |
| `INVALID_OPERATION_CONFIGURATION_OR_INPUT` | 400 | entrada o configuración inválida no clasificada |
| `WRITE_APPROVAL_REQUIRED` | 403 | falta alguna de las cuatro condiciones |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | escritura sin clave |
| `IDEMPOTENCY_CONFLICT` | 409 | misma clave, otro contenido |
| `OUTCOME_PENDING_OR_UNKNOWN_RECONCILE` | 409 | reserva en duda |
| `ASK_IS_READ_ONLY` | 403 | escritura desde `/v1/ask` |
| `CALLER_HEADER_NOT_ALLOWED` | 403 | cabecera prohibida o no declarada |
| `MISSING_CREDENTIALS` | — | falta el secreto del proveedor |
| `OAUTH_CONSENT_REQUIRED` | — | no hay refresh token guardado |
| `INVALID_TOKEN_RESPONSE` | — | el proveedor no devolvió `access_token` |
| `MSAL_CONSENT_REQUIRED` | — | caché MSAL sin token válido |
| `MSAL_CONSENT_OR_ACCOUNT_SELECTION_REQUIRED` | — | ninguna o varias cuentas |
| `INSTALL_AUTH_EXTRA` / `INSTALL_GRPC_EXTRA` | — | falta el extra |
| `UNSUPPORTED_AUTH` / `UNSUPPORTED_PROTOCOL` | — | tipo no implementado |
| `UNSAFE_ENDPOINT` / `UNSAFE_SCHEME` | — | URL rechazada |
| `HOST_NOT_ALLOWED` | — | fuera de la allowlist |
| `TLS_REQUIRED` | — | HTTP sin habilitar red privada |
| `DNS_UNRESOLVED` | — | el host no resuelve |
| `PRIVATE_NETWORK_BLOCKED` | — | dirección no global |
| `UPSTREAM_HTTP_<código>` | el del proveedor | respuesta 3xx o de error |
| `UPSTREAM_RESPONSE_TOO_LARGE` | — | supera `MAX_RESPONSE_BYTES` |
| `NETWORK_ERROR` | — | fallo de red en operación reintentable |
| `NETWORK_OUTCOME_UNKNOWN` | — | fallo de red en una escritura: resultado ambiguo |
| `GRAPHQL_ERROR` / `JSONRPC_ERROR` / `SOAP_FAULT` / `PROVIDER_REJECTED_REQUEST` | el del proveedor | el proveedor rechazó |
| `INTEGRATION_FAILURE` | — | fallo no clasificado; no revela detalles |
| `ATTACHMENTS_TOO_LARGE` / `MEDIA_TOO_LARGE` | — | supera 512 kB decodificados |
| `INVALID_CONTENT_TYPE` / `INVALID_PATH_PARAMETER` | — | entrada mal formada |

### Advertencias de composición

`AI_SENSITIVE_DATA_BLOCKED`, `AI_MODEL_NOT_CONFIGURED`, `AI_INPUT_TOO_LARGE_USE_RESPONSE_MAP` y `AI_FAILED_DETERMINISTIC_FALLBACK` aparecen en `warnings` y no impiden la respuesta: se devuelve la composición determinista.

## Catálogo: campos admitidos

**Del sistema:** `enabled`, `protocol`, `provider`, `base_url`, `allowed_hosts`, `sensitive`, `description`, `headers`, `allowed_request_headers`, `auth`, `webhook`, `insecure` (solo gRPC) y los valores propios que use un constructor, como `phone_number_id`.

**De la operación:** `method`, `path`, `effect`, `description`, `timeout_seconds`, `defaults`, `input_schema`, `response_map`, `headers`, `query_template`, `body_template`, `form_template`, `action` (constructores), `query` (GraphQL), `rpc_method` (JSON-RPC), `envelope_template` y `soap_action` (SOAP), `grpc_method` (gRPC).

En las plantillas, una cadena que empieza por `@` se sustituye por el parámetro completo con ese nombre; no hay evaluación de expresiones.

## Fuentes de este capítulo

`src/universal_api_orchestrator/main.py`, `models.py`, `registry.py`, `orchestrator.py`, `store.py`, `transport.py`, `security.py`, `ratelimit.py`, `webhooks.py`, `response_engine.py`, `connectors/builders.py`, `config/systems.yaml`, y la especificación OpenAPI que publica el propio servicio.
