# 08 · Flujo de datos

Cuatro recorridos completos, paso a paso: una consulta, una escritura, una escritura que falla y un evento entrante. Cada paso dice qué archivo lo ejecuta.

## 1. Una consulta de Gmail

```mermaid
sequenceDiagram
    participant C as Cliente
    participant M as main.py
    participant O as orchestrator.py
    participant R as registry.py
    participant A as auth.py
    participant P as adapters/provider.py
    participant T as transport.py
    participant G as Gmail API
    C->>M: POST /v1/execute con X-API-Key
    M->>M: tamano, request id, limite de carga, clave
    M->>O: execute(gmail, get_message, params)
    O->>R: get_system(gmail)
    R-->>O: configuracion con variables expandidas
    O->>O: validar JSON Schema, efecto read
    O->>A: headers(auth del sistema)
    A->>A: token en cache o refresco
    A-->>O: Authorization Bearer
    O->>P: execute(system, operation, params, headers)
    P->>T: request(GET, url, allowed_hosts)
    T->>T: assert_safe_endpoint en un hilo
    T->>G: GET https://gmail.googleapis.com/...
    G-->>T: 200 con JSON
    T-->>P: codigo y payload acotados
    P->>P: normalize_gmail agrega _content
    P-->>O: codigo y payload
    O->>O: response_map y sobre unificado
    O-->>M: UnifiedResponse ok true
    M-->>C: HTTP 200 con el sobre y X-Request-Id
```

Qué viaja en cada tramo:

| Tramo | Contiene | No contiene |
|---|---|---|
| Cliente → gateway | sistema, operación, parámetros, clave del gateway | ningún token de proveedor |
| Gateway → Gmail | `Authorization` resuelto en el backend, ruta con el identificador codificado | la clave del gateway, cabeceras del cliente no declaradas |
| Gmail → gateway | JSON del proveedor, cortado si supera 4 MB | — |
| Gateway → cliente | sobre unificado con `data`, `_content` y `meta` | credenciales, URL internas, cabeceras del proveedor |

El token nunca sale hacia el cliente y la clave del gateway nunca sale hacia el proveedor. Es la razón de ser del intermediario.

## 2. Una escritura aprobada

```mermaid
sequenceDiagram
    participant C as Cliente
    participant M as main.py
    participant O as orchestrator.py
    participant A as auth.py
    participant S as store.py
    participant T as transport.py
    participant W as API del proveedor
    C->>M: POST /v1/execute con X-API-Key y X-Approval-Key
    M->>M: approved(x_approval_key)
    M->>O: execute(confirmed true, idempotency_key, approved true)
    O->>O: efecto write
    O->>O: ALLOW_WRITES, approved, confirmed, clave presente
    O->>A: obtener credenciales
    A-->>O: cabecera de autorizacion
    O->>S: reserve(sistema:clave, huella del contenido)
    S-->>O: None, reserva creada como pending
    O->>T: un unico intento, sin reintento
    T->>W: POST
    W-->>T: 200 aceptado
    T-->>O: codigo y payload
    O->>S: complete(clave, sobre)
    O-->>M: ok true, delivery provider_accepted_not_delivery_receipt
    M-->>C: HTTP 200
```

Las cuatro condiciones se comprueban en una sola expresión:

```python
if not settings.allow_writes or not approved or not confirmed:
    raise IntegrationError("WRITE_APPROVAL_REQUIRED", 403)
if not idempotency_key:
    raise IntegrationError("IDEMPOTENCY_KEY_REQUIRED", 400)
```

El mensaje de error es el mismo para las tres primeras, a propósito: no se informa a un cliente **cuál** de las condiciones falta.

Una repetición con la misma clave y el mismo contenido no vuelve a salir: `reserve()` devuelve el sobre guardado y se marca `idempotent_replay: true`. Con otro contenido, `IDEMPOTENCY_CONFLICT`.

El campo `delivery` dice `provider_accepted_not_delivery_receipt`. Esa cadena es el resumen de una política: el proveedor aceptó la petición, y eso no es lo mismo que el destinatario lo haya recibido.

## 3. Una escritura cuyo resultado se desconoce

```mermaid
sequenceDiagram
    participant O as orchestrator.py
    participant S as store.py
    participant T as transport.py
    participant W as API del proveedor
    participant H as Operador
    O->>S: reserve, queda pending
    O->>T: POST, un solo intento
    T->>W: POST
    W--xT: se corta la red
    T-->>O: NETWORK_OUTCOME_UNKNOWN
    O-->>O: ok false, requires_reconciliation, reservation_id
    Note over S: la fila sigue pending
    H->>S: uao pending, ve sistema, operacion y antiguedad
    H->>W: comprueba en el proveedor si salio
    H->>S: uao release con resultado comprobado
    S-->>H: released true, retry_is_manual true
    H->>O: repite la operacion deliberadamente
```

El punto crítico es el `--x`: el gateway envió la petición y no leyó la respuesta. No sabe si el mensaje salió. Las tres opciones serían reintentar (riesgo de duplicado), descartar (riesgo de no enviar nunca) o bloquear y preguntar. Elige la tercera.

Mientras la fila sigue `pending`, cualquier petición con esa clave responde `OUTCOME_PENDING_OR_UNKNOWN_RECONCILE` con 409. El procedimiento completo está en [RECONCILIATION](../RECONCILIATION.md).

## 4. Un evento entrante

```mermaid
sequenceDiagram
    participant P as Proveedor
    participant M as main.py
    participant K as webhooks.py
    participant R as registry.py
    participant S as store.py
    participant C as Consumidor
    P->>M: POST /v1/webhooks/whatsapp con firma
    M->>M: limite de tamano y limite de carga por IP
    M->>K: receive(system)
    K->>R: get_system para leer la configuracion de webhook
    R-->>K: tipo y variable del secreto
    K->>K: verify_signature sobre los bytes originales
    K->>K: json.loads solo despues de verificar
    K->>K: extract_events separa mensajes y estados
    K->>S: event_add por cada evento
    S-->>K: nuevo o duplicado
    K-->>P: 200 con received, new_events, duplicates
    C->>S: GET /v1/events con la clave del gateway
    S-->>C: eventos descifrados sin reconocer
    C->>S: POST /v1/events/{id}/ack con aprobacion
```

Tres propiedades de este flujo:

1. **La firma se verifica antes de deserializar.** Entrada no autenticada no llega al parser de JSON.
2. **El gateway no responde al proveedor nada más que un acuse HTTP.** No hay respuesta automática al remitente, no hay reenvío, no hay lógica de negocio en el handler.
3. **Reconocer es local.** `ack` marca la fila; el proveedor no se entera. Si su consumidor falla después de leer y antes de reconocer, el evento sigue disponible: es entrega al menos una vez, y su consumidor debe ser idempotente.

El challenge `GET` existe solo para Meta y exige que el `hub.verify_token` coincida con la variable configurada, comparado con `compare_digest`.

## Dónde está cada dato, en qué momento

| Dato | En tránsito | En reposo | Durante cuánto |
|---|---|---|---|
| Clave del gateway | cabecera del cliente | `.env` del servidor | vida de la instalación |
| Clave de aprobación | cabecera del cliente | `.env` | ídem |
| Token de proveedor | cabecera hacia el proveedor | tabla `tokens`, cifrado | hasta revocar o reautorizar |
| Contenido de un correo | respuesta del proveedor y del gateway | **en ninguna parte** | solo en memoria durante la petición |
| Parámetros de una escritura | petición del cliente | tabla `requests`, cifrado, hasta completarse o purgarse | según retención |
| Resultado de una escritura | respuesta | tabla `requests`, cifrado | hasta `prune-requests` |
| Evento entrante | cuerpo del webhook | tabla `events`, cifrado | hasta `ack` y `prune-events` |
| Identidad de carga | — | memoria del proceso, como hash | hasta reiniciar |

La fila que más sorprende es la del contenido: el gateway **no guarda** los mensajes que consulta. Si necesita un archivo histórico, lo construye su aplicación, con sus propias políticas de retención y consentimiento.

## Qué se registra

El registro de auditoría (`uao.audit`) anota una línea por operación con `trace_id`, sistema, operación y, si falló, el código. **No** anota parámetros, cuerpos, URL con token ni cabeceras. Un registro no sirve para reconstruir un mensaje; sirve para localizarlo en el registro del proveedor.

La CLI sí muestra en pantalla los datos que el operador pidió: su terminal y cualquier redirección de salida son parte de la superficie a proteger.

## Fuentes de este capítulo

`src/universal_api_orchestrator/main.py`, `orchestrator.py`, `auth.py`, `transport.py`, `store.py`, `webhooks.py`, `adapters/provider.py`, `connectors/mail_content.py`, y las pruebas `tests/test_orchestrator_api.py`, `tests/test_reconciliation.py`, `tests/test_security_webhooks.py`.
