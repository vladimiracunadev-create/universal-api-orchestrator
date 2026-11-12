# Contrato HTTP, ejecución y respuestas

## Autenticación de la aplicación

Incluya `X-API-Key: <GATEWAY_API_KEY>` para catálogo, ejecución, batch, ask y lectura de eventos. No use aquí el access token del proveedor: ese secreto se resuelve en el backend. Health y documentación no requieren clave en el proceso local. Los webhooks se autorizan con la firma/secreto del canal, no con la clave privada del gateway.

## Solicitud de ejecución

```json
{
  "system": "gmail",
  "operation": "get_message",
  "params": {"id": "ID_REAL", "format": "full"},
  "headers": {},
  "confirmed": false
}
```

`system` y `operation` deben estar registrados y habilitados. `params` se valida con JSON Schema. Los IDs se codifican al incorporarlos a rutas. No se aceptan URLs arbitrarias como destino de una operación ni se aceptan cabeceras del cliente salvo allowlist explícita; Authorization, Cookie y Host están prohibidas como cabeceras sobreescribibles.

El catálogo de `GET /v1/systems` incluye operaciones, descripción, effect, marca `sensitive` y esquemas. `GET /v1/systems/{system}` devuelve la ficha de uno solo y responde 404 si no existe. Ninguno devuelve base URLs con tokens, secretos ni cabeceras de autenticación.

Un problema de catálogo se distingue por código: `SYSTEM_NOT_FOUND` (404), `SYSTEM_DISABLED` (409), `OPERATION_NOT_FOUND` (404) y `SYSTEM_CONFIGURATION_INCOMPLETE` (503) cuando falta una variable que el catálogo declara. Esos códigos viajan dentro del sobre, no en el HTTP externo.

## Sobre unificado

```json
{
  "ok": true,
  "system": "gmail",
  "operation": "list_messages",
  "protocol": "provider",
  "status_code": 200,
  "data": {"messages": [{"id": "...", "threadId": "..."}]},
  "error": null,
  "meta": {
    "trace_id": "...",
    "elapsed_ms": 15.4,
    "effect": "read",
    "sensitive": true,
    "delivery": null
  }
}
```

El cuerpo `data` conserva generalmente el formato del proveedor; `response_map` permite seleccionar campos mediante JMESPath. Gmail agrega `_content` al obtener cuerpos MIME completos o raw, conservando campos nativos. Un listado de IDs no contiene `_content` inventado.

Toda respuesta incluye `X-Request-Id`. Si envía el suyo con formato seguro (8 a 64 caracteres de letras, dígitos, `.`, `_`, `:` o `-`) se reutiliza; si no, el gateway genera uno. Sirve para correlacionar sus registros con los suyos sin volcar credenciales. Se añaden también `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` y `Referrer-Policy: no-referrer`.

**Dos niveles de estado:** `HTTP 401/403/413/422` puede indicar un rechazo del gateway. Una operación procesada puede responder HTTP 200 con `ok:false` y un `status_code` interno, para mantener el mismo contrato en batch. Siempre revise `ok`, no solamente el código HTTP externo.

## Escrituras, aprobación e idempotencia

Para una escritura deben coincidir:

1. Servidor con `ALLOW_WRITES=true`.
2. Cabecera `X-Approval-Key` con la clave separada del operador autorizado.
3. Solicitud con `confirmed:true`.
4. `idempotency_key` definida por acción lógica.

La CLI añade la cabecera de aprobación con `--approve`, pero **no cambia** `confirmed` en el archivo. Así, ejecutar accidentalmente un ejemplo no lo aprueba. La aprobación es un secreto compartido, no una firma de un humano concreto: una aplicación con ambas claves puede aprobar. Para separación de funciones real debe agregarse identidad y autorización por usuario.

Copie, edite y revise un ejemplo antes de usarlo. Ejemplo de ejecución una vez completada la revisión:

```bash
uao execute /ruta/privada/solicitud-revisada.json --approve
```

No se reutiliza una clave para otro contenido. La huella incluye sistema, operación, parámetros y cabeceras. La clave se separa por sistema: úsela única también entre operaciones del mismo sistema. Mismo contenido y clave completada devuelve el resultado almacenado sin repetir el envío. Misma clave con otro contenido produce conflicto.

Si se pierde la respuesta o el proveedor rechaza una escritura después de reservarla, se conserva el estado pendiente; `requires_reconciliation:true` exige revisar el proveedor antes de un nuevo intento, y `meta.reservation_id` identifica la reserva. Esta política es conservadora incluso ante algunos rechazos definitivos. No cambie de clave automáticamente para saltarse ese bloqueo.

`GET /v1/reconciliation` lista las reservas en duda con su sistema, operación y antigüedad; no expone el contenido del mensaje. `POST /v1/reconciliation/{id}/release` libera una reserva y exige, a la vez, clave de aprobación, `confirmed:true` y un `verified_outcome` de `not_delivered`, `delivered_duplicate_acceptable` o `delivered_do_not_retry`; el último conserva la reserva a propósito y responde 409. Liberar **no** contacta al proveedor, no deshace un envío aceptado y no reintenta: es la afirmación de que alguien comprobó el resultado real. El procedimiento está en [RECONCILIATION](RECONCILIATION.md).

La idempotencia es **local**. No garantiza exactamente una entrega, ni sustituye la idempotencia/correlación ofrecida por cada proveedor. El campo `delivery: provider_accepted_not_delivery_receipt` significa aceptación, no lectura ni recepción del destinatario.

## Batch

```json
{
  "requests": [
    {"alias":"correos", "system":"gmail", "operation":"list_messages", "params":{"q":"is:unread", "maxResults":5}},
    {"alias":"agenda", "system":"google_calendar", "operation":"list_events", "params":{"calendar_id":"primary", "maxResults":5}}
  ],
  "fail_fast": false
}
```

Máximo 20 operaciones. Los alias no pueden repetirse; si se omiten se generan `item_N`. Con `fail_fast:false` se ejecutan en paralelo bajo un semáforo de concurrencia. Con `fail_fast:true` se ejecutan secuencialmente y se detienen en el primer fallo. No es una transacción ni un DAG: el resultado de una operación no se inyecta automáticamente en la siguiente, y un fallo no deshace escrituras completadas.

## Ask: generar sin enviar

`POST /v1/ask` recibe `question`, `requests`, `fail_fast` y, opcionalmente, `response_template` con `{question}`, `{data}` y `{errors}`. Toda operación de escritura se rechaza, aunque el operador tenga claves de aprobación.

La salida incluye `answer`, `mode`, `sources`, `data`, `errors`, `warnings` y **`sent:false`**. Las fuentes identifican alias, sistema, operación y trace_id. El modo `deterministic` presenta datos/plantilla; no interpreta intenciones ni decide qué APIs llamar. El cliente selecciona las operaciones.

Para síntesis de lenguaje natural:

```dotenv
AI_MODE=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com
OPENAI_COMPATIBLE_MODEL=MODELO_HABILITADO_EN_SU_CUENTA
OPENAI_COMPATIBLE_API_KEY=SECRETO_LOCAL
AI_ALLOWED_HOST=api.openai.com
AI_ALLOW_SENSITIVE_DATA=true
```

No copie valores ficticios como credenciales. `AI_ALLOW_SENSITIVE_DATA=true` permite transferir resultados de correo y mensajería al modelo configurado: requiere decisión explícita y políticas de su organización. También puede configurar un endpoint compatible local; para IP privada/loopback debe permitir redes privadas de forma deliberada y restringir allowlists. No se incorpora ni descarga un modelo.

La implementación usa la forma Chat Completions. No equivale a soporte de todos los productos de IA ni incluye tools autónomas, búsqueda web o entrenamiento. Si falla el modelo se vuelve a composición determinista con advertencia. El límite de entrada y las instrucciones contra prompt injection son defensas parciales; no garantizan comprensión perfecta ni seguridad absoluta.

## Paginación, adjuntos y límites

Los parámetros de cursor soportados están en cada esquema: pageToken, cursor, offset, etc. La aplicación no recorre todas las páginas automáticamente ni sigue cualquier `nextLink` recibido. En Microsoft algunos endpoints exponen nextLink sin un consumidor de paginación genérico: agregue mapeo seguro del cursor cuando su caso lo exija.

Límites predeterminados del gateway: 2.000.000 bytes por solicitud, 4.000.000 por respuesta HTTP, concurrencia 8 y timeout de transporte 20 segundos. Una operación del catálogo puede declarar `timeout_seconds` propio, acotado entre 0,5 y 120 segundos: un valor fuera de rango se recorta y un valor no numérico se ignora. Los constructores de adjuntos/media restringen carga decodificada a 512.000 bytes. Son límites de **esta implementación**, no máximos comerciales de Gmail/Meta/Microsoft.

El gateway aplica además un control de carga local por clave de llamada: 120 peticiones por minuto con ráfaga de 30 de forma predeterminada (`RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_BURST`; `0` lo desactiva). Al superarlo responde `429` con `Retry-After` y `X-RateLimit-Remaining: 0`; el resto de las respuestas lleva los tokens restantes. La identidad es el resumen de la clave, o de la dirección del cliente cuando no hay clave, y el contador vive en memoria de este proceso: no se comparte entre réplicas ni sustituye un límite en el proxy inverso. `/health` queda fuera para no romper la sonda del contenedor.

Las conexiones HTTP de salida se reutilizan en un pool compartido del proceso (`HTTP_MAX_CONNECTIONS`, `HTTP_MAX_KEEPALIVE_CONNECTIONS`, `HTTP_KEEPALIVE_EXPIRY_SECONDS`) y se cierran al apagar el servicio.

Solo GET/HEAD se reintentan ante determinados fallos temporales; POST/PUT/PATCH/DELETE no se reintentan automáticamente. Un POST de consulta como GraphQL tampoco gana retries HTTP por declarar `effect:read`. Las operaciones de envío mantienen un solo intento de transporte.

## Operación y mantenimiento

`GET /v1/stats` devuelve la versión, la política vigente (`allow_writes`, `ai_mode`, límite de carga), el número de sistemas y los recuentos del estado local: eventos pendientes y reconocidos, reservas completadas y pendientes de reconciliación, y tokens guardados. No consulta proveedores ni verifica credenciales.

`POST /v1/admin/reload` relee `config/systems.yaml` sin reiniciar el proceso y requiere clave de aprobación; si el archivo queda inválido responde `422 INVALID_CATALOG_PREVIOUS_KEPT` y el catálogo anterior sigue en uso. Las variables de entorno **no** se recargan: `.env` se lee al iniciar. El procedimiento diario está en el [RUNBOOK](RUNBOOK.md).

## Errores y diagnóstico

Consulte [TROUBLESHOOTING](TROUBLESHOOTING.md). Los mensajes técnicos son deliberadamente estables y no incluyen URLs con tokens, payloads completos del proveedor ni cabeceras secretas. Use trace_id y registros del proveedor para investigar sin volcar credenciales.
