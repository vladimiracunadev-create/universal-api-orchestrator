# Diagnóstico sin exponer secretos

| Síntoma/código | Qué revisar |
|---|---|
| No inicia / STATE_KEY inválida | Ejecute bootstrap para una instalación nueva. Para un estado existente restaure la misma clave, no genere otra. |
| `GATEWAY_KEY_NOT_CONFIGURED` | Clave de gateway ausente o menor a 24 caracteres; bootstrap y reinicio. |
| `INVALID_API_KEY` | Clave del cliente distinta a la del servidor; no confundir con el token del proveedor. |
| `SYSTEM_NOT_FOUND` (404) | El nombre no existe en el catálogo. `uao catalog` lista los válidos; distinga mayúsculas y guiones bajos. |
| `SYSTEM_DISABLED` (409) | `uao enable NOMBRE` y después `uao reload` o reinicio. Habilitar no concede permisos del proveedor. |
| `OPERATION_NOT_FOUND` (404) | La operación no existe en ese sistema. Consulte `GET /v1/systems/<sistema>` o la matriz de conectores. |
| `SYSTEM_CONFIGURATION_INCOMPLETE` (503) | El catálogo declara una variable que no está en el proceso. `uao doctor` marca el sistema como `missing_environment`. |
| `INVALID_CATALOG_PREVIOUS_KEPT` (422) | `uao reload` encontró un YAML inválido; el catálogo anterior sigue en uso. Corrija el archivo y repita. |
| `MISSING_CREDENTIALS` | Nombre y valor del secreto en el proceso que ejecuta el servidor. Docker no relee el `.env` solo por editarlo. |
| `OAUTH_CONSENT_REQUIRED` | Autorizar el slot correcto con CLI y scopes adecuados. |
| `MSAL_CONSENT_REQUIRED` | Caché/permiso insuficiente; revisar tenant, cuenta y consentimiento. |
| `MSAL_CONSENT_OR_ACCOUNT_SELECTION_REQUIRED` | No hay cuenta o hay varias sin selección; usar slot o username explícito. |
| `WRITE_APPROVAL_REQUIRED` | Revisar las cuatro condiciones; habilitar un proveedor no aprueba envíos. |
| `IDEMPOTENCY_KEY_REQUIRED` | Asignar clave estable a la acción revisada. |
| `IDEMPOTENCY_CONFLICT` (409) | Reutilizó una clave con contenido distinto. Use una clave nueva para una acción lógica nueva. |
| `OUTCOME_PENDING_OR_UNKNOWN_RECONCILE` (409) | Hay una reserva en duda con esa clave. Verifique el resultado real y siga [RECONCILIATION](RECONCILIATION.md). No cambie la clave para saltarse el bloqueo. |
| `RESERVATION_KEPT_TO_PREVENT_DUPLICATE` (409) | Declaró `delivered_do_not_retry`: la reserva se conserva a propósito. |
| `RESERVATION_NOT_FOUND_OR_ALREADY_COMPLETE` (404) | La reserva no existe o la escritura terminó bien; una escritura completada no se libera para repetirla. |
| `RELEASE_CONFIRMATION_REQUIRED` (403) | Falta `confirmed:true` en el cuerpo, o `--confirm` en la CLI. |
| `INVALID_RESERVATION_ID` (400) | El identificador debe ser el SHA-256 hexadecimal de 64 caracteres que devuelve `uao pending`. |
| `APPROVAL_REQUIRED` (403) | Falta `X-Approval-Key` en reconciliación o recarga de catálogo. |
| `ASK_IS_READ_ONLY` | Se intentó una escritura desde ask; separar composición y envío. |
| `INVALID_INPUT_SCHEMA` | Parámetro, tipo o nombre no admitido; leer esquema de operación. |
| `UPSTREAM_HTTP_401/403` | Token, scopes, recurso, políticas de la app o permisos de cuenta. |
| `UPSTREAM_HTTP_429` | Cuota/rate limit del **proveedor**; pausar y revisar consumo, no saturar con reintentos externos. |
| `RATE_LIMIT_EXCEEDED` (429) | Límite local de **este gateway**. Respete `Retry-After`, reparta el tráfico o ajuste `RATE_LIMIT_PER_MINUTE`. No lo ponga en 0 para tapar un bucle del cliente. |
| `REQUEST_TOO_LARGE` (413) | La petición supera `MAX_REQUEST_BYTES` (2 MB). La carga decodificada de adjuntos está limitada a 512 kB. |
| `NETWORK_OUTCOME_UNKNOWN` | Se perdió una respuesta de transporte de un solo intento; no asumir que no hubo acción. |
| `UPSTREAM_RESPONSE_TOO_LARGE` | Reducir rango, campos o tamaño; no desactivar todos los límites. |
| `AI_SENSITIVE_DATA_BLOCKED` | Protección activada; revisar permiso/política antes de cambiarla. |
| `AI_MODEL_NOT_CONFIGURED` | Modelo no definido en el endpoint seleccionado. |
| `AI_FAILED_DETERMINISTIC_FALLBACK` | El modelo falló; se mantiene resultado sin generación. |
| Webhook 401 | Secretos/cabeceras, cuerpo original, timestamp Slack y proxy sin reserialización. |
| Webhook 404 | Sistema no habilitado o sin configuración webhook. |
| SQLite Permission denied | Propietario de volumen, UID/GID en Docker y ACLs de Windows. |
| `UNREADABLE_WITH_CURRENT_STATE_KEY` en `uao pending` | La reserva se cifró con otra `STATE_KEY`. Restaure la clave correcta antes de decidir nada. |
| `CALLER_HEADER_NOT_ALLOWED` (403) | Envió una cabecera fuera de la allowlist del sistema, o una prohibida (`Authorization`, `Host`, `Cookie`, `Proxy-Authorization`, `X-API-Key`). |
| `HOST_NOT_ALLOWED` / `TLS_REQUIRED` / `PRIVATE_NETWORK_BLOCKED` / `DNS_UNRESOLVED` | Defensa de salida actuando. Corrija `allowed_hosts` o la URL del catálogo; no desactive el bloqueo de redes privadas en producción. |

## Procedimiento de análisis

Compruebe primero `/health`, después `uao doctor`, luego una consulta de solo lectura del proveedor. Si health falla no investigue scopes aún; si solo un proveedor falla, no cambie credenciales de todos. Doctor no hace autenticación remota y puede indicar configuración lista aun cuando falte consentimiento válido en el store.

Use `X-Request-Id` de la respuesta HTTP, el `trace_id` de la operación, el nombre de la operación y la hora para correlacionar. `uao stats` indica si hay reservas pendientes de reconciliación o eventos sin consumir, que suelen ser la causa real de un comportamiento "detenido". No vuelque headers, URLs Telegram ni cuerpos de correo al log. Los errores del gateway reducen detalles deliberadamente; una consulta al dashboard del proveedor puede ser necesaria.

## Preguntas frecuentes

**¿Por qué responde HTTP 200 si falló Gmail?** Porque el transporte entre cliente y gateway fue procesado y la operación devuelve `ok:false` dentro del contrato unificado. Revise ambos niveles.

**¿Por qué no recibo webhooks en localhost?** El proveedor externo no puede conectar al loopback de su equipo. Necesita una URL HTTPS accesible, con rutas restringidas.

**¿Por qué aprobar no envía?** `--approve` no cambia `confirmed:false`; ambas decisiones son independientes. Además se requiere ALLOW_WRITES, idempotencia y permisos remotos.

**¿Por qué dos correos no aparecen en el resumen?** El listado devuelve IDs, el filtro puede excluirlos, puede existir paginación o el cuerpo no se consultó. Use get_message y examine las fuentes fallidas; no invente contenido.

**¿Puedo usarlo sin Internet?** Sí para pruebas y datos ya almacenados. No para consultar o enviar por APIs remotas. La demostración offline es una suite simulada claramente identificada.

**¿Por qué recibo 429 si el proveedor no me ha limitado?** Porque el límite es local del gateway, no del proveedor. Los códigos son distintos a propósito: `RATE_LIMIT_EXCEEDED` es de esta instancia y `UPSTREAM_HTTP_429` es del servicio remoto.

**Edité `.env` y nada cambió.** `uao reload` recarga el **catálogo**, no las variables de entorno: `.env` se lee al iniciar el proceso. Reinícielo.

**¿Puedo exponerlo como producto multiempresa?** No con claves globales/SQLite compartidos sin implementar aislamiento, identidad, límites y operación del servicio. Consulte seguridad y roadmap.
