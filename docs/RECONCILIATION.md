# Reconciliar una escritura en duda

## El problema

Un envío puede terminar de tres maneras: aceptado, rechazado o **desconocido**. El tercer caso es real y frecuente: el gateway envió la petición y se cortó la red antes de leer la respuesta. El proveedor pudo haber entregado el mensaje, o no. Nadie lo sabe desde este lado.

Ante esa duda hay dos errores posibles. Reintentar y enviar el mensaje dos veces. O no reintentar y no enviarlo nunca. Este proyecto no elige por usted: **bloquea la clave de idempotencia y pide una decisión humana**. Un sistema que reintenta solo es cómodo hasta el día que duplica una factura.

## Cómo se ve

Una escritura que falló después de reservar su clave devuelve:

```json
{
  "ok": false,
  "error": "NETWORK_OUTCOME_UNKNOWN",
  "meta": {
    "trace_id": "...",
    "requires_reconciliation": true,
    "reservation_id": "a1b2c3..."
  }
}
```

Si repite la misma operación con la misma clave, no se reenvía: recibe `OUTCOME_PENDING_OR_UNKNOWN_RECONCILE` con HTTP 409. Eso es el diseño funcionando, no un fallo del gateway.

`reservation_id` es el SHA-256 de `sistema:idempotency_key`. Se publica para que pueda reconciliar sin adivinar y sin exponer la clave original.

## Procedimiento

### 1. Listar lo pendiente

```bash
uao pending
```

```json
{
  "pending": [
    {
      "id": "a1b2c3...",
      "created": 1763000000.0,
      "age_seconds": 412.5,
      "system": "whatsapp",
      "operation": "send_text",
      "decode_warning": null
    }
  ],
  "guidance": "Compruebe el resultado en el proveedor antes de liberar la reserva."
}
```

La reserva guarda cifrados el sistema y la operación intentados, no el contenido del mensaje. Si `decode_warning` dice `UNREADABLE_WITH_CURRENT_STATE_KEY`, la fila se cifró con otra `STATE_KEY`: restaure la clave correcta antes de decidir nada.

### 2. Comprobar en el proveedor

Esto ocurre **fuera** del gateway y es la parte que no se puede automatizar aquí. Según el canal:

| Canal | Dónde mirar |
|---|---|
| WhatsApp | Eventos de estado en `/v1/events`, o el historial de la conversación en el número de negocio. |
| Gmail | La carpeta de enviados de la cuenta autorizada. |
| Outlook / Graph | Elementos enviados; recuerde que `sendMail` guarda copia. |
| Telegram, Slack, Discord | El canal o chat de destino: el mensaje está o no está. |
| Twilio, SendGrid, Resend | El registro de mensajes del panel del proveedor, por fecha y destinatario. |
| GitHub | La issue o el recurso que la operación iba a crear. |

Use `trace_id` y `X-Request-Id` para situar el intento en el tiempo. Un `age_seconds` alto no significa que no se enviara.

### 3. Decidir

| Lo que comprobó | Resultado a declarar | Efecto |
|---|---|---|
| No llegó nada al destinatario | `not_delivered` | Libera la reserva. Podrá reintentar **usted**, a mano. |
| Llegó, y un duplicado sería aceptable | `delivered_duplicate_acceptable` | Libera la reserva. Asume el riesgo de un segundo envío. |
| Llegó, y un duplicado sería inaceptable | `delivered_do_not_retry` | **Conserva** la reserva: responde 409 y el bloqueo se queda puesto. |

El tercer caso no es un error de la herramienta: es la forma de dejar constancia de que se revisó y se decidió no reintentar. Si además quiere que la operación aparezca como terminada, use una `idempotency_key` nueva para la siguiente acción lógica distinta; no para repetir la misma.

### 4. Liberar

```bash
uao release a1b2c3... --verified-outcome not_delivered --confirm --note "Buzón de enviados revisado"
```

O por HTTP:

```bash
curl -X POST http://127.0.0.1:8080/v1/reconciliation/a1b2c3.../release \
  -H "X-API-Key: $GATEWAY_API_KEY" \
  -H "X-Approval-Key: $APPROVAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true, "verified_outcome": "not_delivered", "note": "Buzón de enviados revisado"}'
```

Respuesta:

```json
{"released": true, "verified_outcome": "not_delivered", "retry_is_manual": true}
```

### 5. Reintentar, si corresponde

Liberar no reenvía nada. Vuelva a ejecutar la operación con las cuatro condiciones de siempre, revisando destinatario y contenido otra vez.

## Lo que liberar **no** hace

- No contacta al proveedor ni consulta el estado del mensaje: usted lo comprobó.
- No cancela, no retira ni deshace un mensaje que el proveedor ya entregó.
- No reenvía la operación.
- No toca una reserva completada: una escritura que terminó bien no se puede "liberar" para repetirla. Responde 404.
- No queda registrada como atribuible a una persona: la clave de aprobación es un secreto compartido. Para separación de funciones real hace falta identidad por usuario, que esta versión no implementa.

## Códigos de respuesta

| Código | Causa |
|---|---|
| 400 `INVALID_RESERVATION_ID` | El identificador no es un SHA-256 hexadecimal de 64 caracteres. |
| 403 `APPROVAL_REQUIRED` | Falta o no coincide `X-Approval-Key`. |
| 403 `RELEASE_CONFIRMATION_REQUIRED` | El cuerpo no trae `confirmed:true`. |
| 409 `RESERVATION_KEPT_TO_PREVENT_DUPLICATE` | Declaró `delivered_do_not_retry`. La reserva se mantiene a propósito. |
| 422 `UNKNOWN_VERIFIED_OUTCOME` | El resultado declarado no es uno de los tres admitidos. |
| 404 `RESERVATION_NOT_FOUND_OR_ALREADY_COMPLETE` | No existe, o la escritura terminó correctamente. |

## Higiene del estado

Las reservas completadas se pueden expirar sin riesgo:

```bash
uao prune-requests --days 90
```

Ese comando **nunca** borra una reserva pendiente: si lo hiciera, perdería la protección contra duplicados justo en el caso que importa. Revise `uao stats` de forma periódica: `requests_pending_reconciliation` creciendo es señal de que hay un problema de red o de proveedor sin atender, no de que el gateway esté lento.

## Límites honestos

La idempotencia es **local**. No garantiza entrega exactamente una vez, no sustituye la idempotencia o correlación que ofrezca cada proveedor, y no sobrevive a la pérdida de `STATE_KEY`. Con varias réplicas del proceso sobre bases SQLite distintas, cada una tiene sus propias reservas: ese escenario necesita un almacén transaccional compartido, descrito en el [ROADMAP](../ROADMAP.md).
