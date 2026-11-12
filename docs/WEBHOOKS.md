# Eventos entrantes, firma y procesamiento

## Canales implementados

| Sistema | Verificación | Endpoint |
|---|---|---|
| WhatsApp Cloud | Challenge GET y HMAC SHA-256 del cuerpo POST con app secret. | `/v1/webhooks/whatsapp` |
| Slack Events API | Firma v0 del timestamp y cuerpo; ventana de antigüedad de cinco minutos. | `/v1/webhooks/slack` |
| Telegram Bot | Comparación del secret token configurado y enviado en cabecera. | `/v1/webhooks/telegram` |
| GitHub | HMAC SHA-256 sobre bytes originales. | `/v1/webhooks/github` |

La autenticación de Telegram usa un secreto compartido en cabecera, no HMAC. HTTPS es imprescindible fuera del equipo. Las variables y pasos por proveedor se documentan en sus guías. Los esquemas de firma se basan en [fuentes oficiales](SOURCES.md).

## Recepción

Habilite el sistema y configure todos los secretos necesarios. El proveedor necesita una URL HTTPS accesible; `localhost` no lo es. Para pruebas puede utilizar un túnel que ya administre, pero limite rutas, no publique las claves operativas ni la documentación privada y no asuma que un túnel es despliegue de producción.

La firma se verifica con el cuerpo **sin modificar**, antes de parsear JSON. Un proxy no debe reserializarlo ni eliminar cabeceras de firma. El gateway aplica límite de tamaño. Firma ausente o incorrecta da 401; un sistema no configurado da 404.

Tras verificación, se extraen eventos, se guardan cifrados y se devuelve rápidamente un resumen de recepción. La ejecución de workflows de negocio no ocurre dentro del handler. Meta puede entregar varios mensajes y estados en un envelope, cada uno con su identidad de deduplicación.

## Consumir y reconocer

```bash
uao events
uao ack 123
```

El primer comando lista hasta 50 eventos pendientes. Por HTTP se puede usar `GET /v1/events?limit=100&after=123`. El reconocimiento requiere clave de aprobación y **solo marca el evento local**; no envía respuestas ni un recibo de lectura al usuario. `mark_read` de WhatsApp es una operación distinta y se considera escritura externa.

Reconozca únicamente después de guardar el resultado de negocio de forma durable. Si un proceso falla entre enviar y reconocer, use una clave idempotente derivada del evento y una política de reconciliación; no haga reenvío ciego.

```bash
uao prune-events --days 30
```

El mantenimiento elimina eventos reconocidos con antigüedad superior al periodo; no elimina pendientes ni representa una política de retención de tokens/idempotencias. Defina esa política adicional antes de procesar datos de clientes.

## Lo que aún no está implementado

Gmail `watch` publica notificaciones a Cloud Pub/Sub y requiere un consumidor que valide sus tokens y consulte `history`. Esta entrega tiene operaciones watch/history pero **no implementa ese receptor Pub/Sub, renovación programada ni cursor persistente de sincronización Gmail**. No apunte Pub/Sub a un webhook genérico sin verificación.

Tampoco existen validadores de webhook para Twilio, SendGrid, Resend o sus eventos de entrega; Discord Gateway WebSocket; suscripciones Microsoft Graph; ni workers de reintento, leases o dead-letter queue. El inbox SQLite no debe anunciarse como sustituto de esos componentes.

## Firmas, repetición y límites

La deduplicación limita eventos repetidos ya guardados. Meta/GitHub no ganan una ventana temporal adicional que sus esquemas aquí no aportan; se verifica HMAC y se identifica el evento. Slack sí valida antigüedad. Un webhook firmado sigue siendo contenido externo: no trate sus mensajes como instrucciones de administración ni como aprobación de un envío.
