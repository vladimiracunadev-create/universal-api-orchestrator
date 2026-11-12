# 19 · Matriz de trazabilidad

Cada capacidad que el proyecto declara, con el código que la implementa, la prueba que la fija y su estado real de verificación.

Leyenda del estado: **Probado offline** = hay prueba automatizada con transporte simulado. **Verificado en ejecución** = comprobado además contra el servicio real en loopback en esta entrega. **Guía** = hay configuración y procedimiento, sin ejecución verificada aquí. **No verificado con cuenta real** = ninguna comprobación contra el proveedor.

## Contrato HTTP

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| `GET /health` sin clave | `main.py:health` | `test_orchestrator_api.py` | Verificado en ejecución |
| Clave obligatoria en `/v1` | `main.py:authorize` | `test_orchestrator_api.py` | Verificado en ejecución |
| 503 si la clave no está configurada | `main.py:authorize` | — | Probado en el arranque del smoke |
| Catálogo público sin secretos | `registry.py:list_public` | `test_orchestrator_api.py`, `test_gateway_controls.py` | Verificado en ejecución |
| Ficha de un sistema, 404 si no existe | `main.py:system_detail`, `registry.py:public_system` | `test_gateway_controls.py` | Verificado en ejecución |
| `POST /v1/execute` con sobre unificado | `main.py:execute`, `orchestrator.py:execute` | `test_orchestrator_api.py` | Verificado en ejecución |
| `POST /v1/batch`, máximo 20, alias únicos | `models.py:BatchRequest`, `orchestrator.py:batch` | `test_orchestrator_api.py` | Probado offline |
| `POST /v1/ask` compone y **nunca** envía | `main.py:ask`, `response_engine.py` | `test_orchestrator_api.py` | Verificado en ejecución |
| Campo desconocido rechazado | `models.py` (`extra="forbid"`) | validación de ejemplos | Probado offline |
| Dos niveles de estado | `orchestrator.py` (sobre con `ok`) | toda la suite | Verificado en ejecución |
| OpenAPI publicado | FastAPI | `test_orchestrator_api.py` | Verificado en ejecución: 13 rutas |

## Políticas de escritura

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Cuatro condiciones simultáneas | `orchestrator.py:execute` | `test_orchestrator_api.py:test_write_requires_all_gates_and_replay` | Verificado en ejecución |
| `ALLOW_WRITES=false` bloquea | `config.py`, `orchestrator.py` | ídem | Verificado en ejecución |
| Clave de aprobación separada | `main.py:approved` | `test_orchestrator_api.py` | Verificado en ejecución |
| `confirmed` no se altera por `--approve` | `cli.py` | — | Guía (documentado y leído en el código) |
| `idempotency_key` obligatoria | `orchestrator.py` | `test_orchestrator_api.py` | Probado offline |
| `ask` rechaza escrituras con aprobación | `orchestrator.py` (`read_only`) | `test_orchestrator_api.py:test_ask_readonly_cannot_write` | Verificado en ejecución |
| POST sin `effect` se considera escritura | `orchestrator.py` | `test_connectors.py` (efecto por operación) | Probado offline |
| Ejemplos de escritura con `confirmed:false` | `examples/requests/` | `verify_repository.py` | Probado offline |
| `delivery` no afirma entrega | `orchestrator.py` | `test_orchestrator_api.py` | Probado offline |

## Idempotencia y reconciliación

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Huella del contenido por clave | `store.py:reserve` | `test_storage_auth.py` | Probado offline |
| Repetición devuelve el resultado guardado | `store.py:reserve`, `orchestrator.py` | `test_orchestrator_api.py` | Probado offline |
| Conflicto con otro contenido | `store.py:reserve` | `test_storage_auth.py` | Probado offline |
| Reserva en duda bloquea el reintento | `store.py:reserve` | `test_orchestrator_api.py:test_unknown_delivery_not_automatically_replayed` | Probado offline |
| `reservation_id` en la respuesta | `orchestrator.py` | `test_reconciliation.py` | Probado offline |
| Reserva pendiente inspeccionable | `store.py:pending` | `test_reconciliation.py` | Verificado en ejecución |
| Liberación exige aprobación y confirmación | `main.py:release` | `test_reconciliation.py` | Verificado en ejecución |
| `delivered_do_not_retry` conserva la reserva | `main.py:release` | `test_reconciliation.py` | Probado offline |
| Reserva completada no se libera | `store.py:release` | `test_reconciliation.py` | Probado offline |
| Liberar no reintenta ni contacta al proveedor | `main.py:release`, `store.py:release` | `test_reconciliation.py` | Probado offline |
| Purga que preserva lo pendiente | `store.py:prune_requests` | `test_reconciliation.py` | Probado offline |

## Autorización de proveedor

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| API key, bearer y basic | `auth.py:headers` | `test_storage_auth.py` | Probado offline |
| OAuth 2 con refresco | `auth.py:oauth` | `test_storage_auth.py` | Probado offline (transporte simulado) |
| Client credentials | `auth.py:oauth` | `test_storage_auth.py` | Probado offline |
| Lock y caché por token | `auth.py:oauth` | `test_storage_auth.py` | Probado offline |
| Credenciales ausentes sin filtrar el valor | `auth.py:env` | `test_storage_auth.py` | Probado offline |
| MSAL delegado con caché cifrada | `auth.py:microsoft` | — | **No verificado con cuenta real** |
| Consentimiento interactivo de Google | `cli.py:auth_google` | — | **No verificado con cuenta real** |
| Device code de Microsoft | `cli.py:auth_microsoft` | — | **No verificado con cuenta real** |

## Defensa de salida

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Allowlist de hosts obligatoria | `security.py`, `registry.py` | `test_security_webhooks.py`, `verify_repository.py` | Probado offline |
| Esquema y credenciales en URL rechazados | `security.py` | `test_security_webhooks.py` (5 casos) | Probado offline |
| TLS obligatorio salvo red privada | `security.py` | `test_security_webhooks.py` | Probado offline |
| Direcciones no globales bloqueadas | `security.py` | `test_security_webhooks.py` (5 casos) | Probado offline |
| Sin redirecciones | `transport.py` | `test_transport.py:test_redirects_rejected` | Probado offline |
| Cabeceras prohibidas y allowlist | `security.py:safe_caller_headers` | `test_security_webhooks.py` | Probado offline |
| Límite de respuesta durante la lectura | `transport.py` | `test_transport.py:test_response_limit` | Probado offline |
| Sin reintento de escrituras | `transport.py` | `test_transport.py:test_write_does_not_retry` | Probado offline |
| Reintento de lectura con `Retry-After` acotado | `transport.py:retry_delay` | `test_transport.py` | Probado offline |
| Timeout por operación acotado | `transport.py:bounded_timeout` | `test_transport.py` | Probado offline |

## Estado cifrado

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Tokens, reservas e inbox cifrados con Fernet | `store.py` | `test_storage_auth.py` | Probado offline |
| `STATE_KEY` requerida para arrancar | `store.py:__init__` | `test_repository_tools.py` (bootstrap) | Verificado en ejecución |
| WAL e índices | `store.py:SCHEMA`, `connect` | toda la suite de estado | Probado offline |
| Permisos 600 en POSIX | `store.py` | — | Guía (no ejecutado en POSIX en esta entrega) |
| Recuentos sin contenido | `store.py:stats` | `test_gateway_controls.py` | Verificado en ejecución |
| Fila ilegible marcada, no fatal | `store.py:pending` | — | Probado offline (ruta de excepción) |

## Eventos entrantes

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Firma verificada antes de deserializar | `webhooks.py:receive` | `test_security_webhooks.py` | Probado offline |
| HMAC de Meta y GitHub | `webhooks.py:verify_signature` | `test_security_webhooks.py` (2 casos) | Probado offline |
| Ventana de 300 s en Slack | `webhooks.py` | `test_security_webhooks.py` | Probado offline |
| Token secreto de Telegram | `webhooks.py` | `test_security_webhooks.py` | Probado offline |
| Challenge de Meta | `webhooks.py:challenge` | `test_orchestrator_api.py` | Probado offline |
| Mensajes y estados separados | `webhooks.py:extract_events` | `test_orchestrator_api.py` | Probado offline |
| Deduplicación por evento | `store.py:event_add` | `test_orchestrator_api.py`, `test_storage_auth.py` | Probado offline |
| `ack` requiere aprobación | `main.py:ack` | `test_orchestrator_api.py` | Probado offline |
| Webhook a sistema deshabilitado rechazado | `webhooks.py:webhook_config` | — | Verificado en ejecución (404) |
| Pub/Sub de Gmail, Graph, Twilio, SendGrid, Resend | — | — | **No implementado** |

## Composición de respuestas

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Composición determinista con fuentes | `response_engine.py` | `test_orchestrator_api.py` | Probado offline |
| `sent: false` siempre | `response_engine.py` | `test_orchestrator_api.py` | Probado offline |
| Datos sensibles bloqueados sin autorización | `response_engine.py` | `test_orchestrator_api.py:test_sensitive_data_not_sent_to_llm` | Probado offline |
| Modelo no configurado o entrada grande, con advertencia | `response_engine.py` | — | Probado offline (rutas de advertencia) |
| Fallo del modelo vuelve a determinista | `response_engine.py` | — | Probado offline |
| Evidencia reducida, sin inventar cuerpos | `mail_content.py:evidence_for_ai` | `test_mail_content.py` | Probado offline |
| Síntesis con un modelo real | `response_engine.py:_ai_answer` | — | **No verificado con endpoint real** |

## Conectores

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| 69 operaciones con esquema y efecto | `config/systems.yaml` | `test_connectors.py` (parametrizado), `verify_repository.py` | Probado offline |
| MIME de Gmail de ida | `builders.py:mime_message` | `test_connectors.py` | Probado offline |
| Rechazo de inyección en cabeceras | `builders.py` (`EmailMessage`) | `test_connectors.py` | Probado offline |
| MIME de Gmail de vuelta con `_content` | `mail_content.py` | `test_mail_content.py` (6 casos) | Probado offline |
| Envelope de WhatsApp y subida de medios | `builders.py:whatsapp` | `test_connectors.py` | Probado offline |
| Destinatarios y adjuntos de Graph | `builders.py:outlook` | `test_connectors.py` | Probado offline |
| Límite de 512 kB decodificados | `builders.py` | `test_connectors.py` | Probado offline |
| `ok:false` de Slack y Telegram detectado | `adapters/provider.py` | `test_adapters_extended.py` (2 casos) | Probado offline |
| Las 13 integraciones contra su proveedor | — | — | **No verificado con cuenta real** |

## Protocolos

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| REST con query, cuerpo y formulario | `adapters/rest.py`, `builders.py:generic` | `test_connectors.py` | Probado offline |
| GraphQL con detección de `errors` | `adapters/graphql.py` | `test_adapters_extended.py` | Probado offline |
| JSON-RPC con envelope validado | `adapters/jsonrpc.py` | `test_adapters_extended.py` | Probado offline |
| SOAP con escape y parser defensivo | `adapters/soap.py` | `test_adapters_extended.py` | Probado offline |
| gRPC unary con TLS | `adapters/grpc_adapter.py` | `test_adapters_extended.py` (falta del extra) | **No verificado con servicio real** |
| Normalización JMESPath | `normalizer.py` | `test_normalizer.py` | Probado offline |

## Operación

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Límite de carga con 429 y `Retry-After` | `ratelimit.py`, `main.py` | `test_gateway_controls.py` (3 casos) | Verificado en ejecución |
| `/health` exento del límite | `main.py` | `test_gateway_controls.py` | Verificado en ejecución |
| Identidad sin almacenar la clave | `ratelimit.py:identity` | `test_gateway_controls.py` | Probado offline |
| Desalojo acotado de buckets | `ratelimit.py:_evict` | `test_gateway_controls.py` | Probado offline |
| `X-Request-Id` propio o del cliente saneado | `main.py:body_limit` | `test_gateway_controls.py` | Verificado en ejecución |
| Cabeceras de seguridad en la respuesta | `main.py:body_limit` | — | Verificado en ejecución |
| Límite de petición con 413 | `main.py:body_limit` | `test_orchestrator_api.py` | Probado offline |
| Errores de catálogo precisos | `orchestrator.py:resolve`, `registry.py` | `test_gateway_controls.py` | Verificado en ejecución |
| Recarga en caliente con aprobación | `main.py:reload_catalog`, `registry.py:reload` | `test_gateway_controls.py` (2 casos) | Verificado en ejecución |
| Catálogo inválido conserva el anterior | `registry.py:reload` | `test_gateway_controls.py` | Verificado en ejecución |
| Pool HTTP reutilizado y cerrado | `transport.py` | `test_transport.py` | Probado offline |
| Semáforo de concurrencia | `orchestrator.py` | — | Probado offline (ruta ejercitada) |
| 18 comandos de CLI | `cli.py` | `test_repository_tools.py` (parcial) | Guía: `catalog`, `doctor`, `health`, `stats`, `reload`, `pending` ejecutados a mano |

## Calidad y coherencia

| Capacidad declarada | Código | Prueba | Estado |
|---|---|---|---|
| Bootstrap idempotente que no imprime claves | `scripts/bootstrap.py` | `test_repository_tools.py` | Probado offline |
| Negativa a reemplazar clave con base existente | `scripts/bootstrap.py` | `test_repository_tools.py` | Probado offline |
| Importador de OpenAPI deshabilitado | `tools/import_openapi.py` | `test_repository_tools.py` | Probado offline |
| Verificación de catálogo, ejemplos y enlaces | `scripts/verify_repository.py` | ejecución en CI | Verificado en ejecución |
| Coherencia de versión y recuentos | `scripts/verify_repository.py` | ídem | Verificado en ejecución |
| Detección de codificación dañada | `scripts/verify_repository.py` | ídem | Verificado en ejecución |
| ZIP reproducible sin secretos | `scripts/release.py` | — | Guía |
| Matriz de CI en 3 sistemas y 3 versiones | `.github/workflows/ci.yml` | — | Guía: definido, resultado en Actions |
| gitleaks, Bandit, pip-audit, CodeQL | `.github/workflows/security.yml` | — | Bandit y pip-audit ejecutados localmente sin hallazgos |

## Resumen del estado

| Estado | Capacidades |
|---|---|
| Verificado en ejecución (loopback, sin proveedores) | 28 |
| Probado offline con transporte simulado | 62 |
| Guía: configurado y documentado, sin ejecución aquí | 8 |
| **No verificado con cuenta real** | 8 |
| No implementado, declarado como tal | 2 |

Las ocho filas marcadas **no verificado con cuenta real** son el trabajo pendiente más importante del proyecto, y están priorizadas como D1 en el [capítulo 15](15-risks-and-technical-debt.md). La ficha para registrar esa verificación está en [VALIDATION](../VALIDATION.md).

## Fuentes de este capítulo

Cruce de `src/universal_api_orchestrator/`, los 13 archivos de `tests/`, `scripts/`, `config/systems.yaml`, `docs/validation-results/runtime-smoke.json` y `docs/validation-results/coverage.json`.
