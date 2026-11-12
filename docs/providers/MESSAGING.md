# Slack, Telegram, Discord y correo transaccional

Todos los proveedores se activan individualmente: complete su secreto en `.env`, ejecute `uao enable NOMBRE` y reinicie/recree el servicio. `uao doctor` comprueba configuración, no validez remota del token. Los ejemplos de envío permanecen `confirmed:false`.

## Slack

Cree una aplicación Slack, configure los scopes necesarios, instálela en su workspace y obtenga el bot token. Guárdelo en `SLACK_BOT_TOKEN`. Para eventos entrantes, configure `SLACK_SIGNING_SECRET` con el signing secret de la misma app.

`auth_test` comprueba la identidad; `list_channels`, `history` y `replies` consultan conversaciones permitidas; `send_message` y `update_message` publican/actualizan. Para enviar se requiere `chat:write`; lectura y acceso a tipos de canal dependen de scopes como `channels:read`, `channels:history` o permisos correspondientes a conversaciones privadas. Una lista de scopes genérica no garantiza acceso a todo el workspace. Invite la app al canal cuando sea necesario.

[Ejemplo](../../examples/requests/slack-send.json). La API puede responder HTTP 200 con `ok:false`; el adaptador lo convierte en fallo del sobre unificado. El endpoint webhook `/v1/webhooks/slack` valida firma v0 y timestamp, responde al challenge verificado y persiste eventos. Configure suscripciones apropiadas en Events API. No hay Socket Mode ni gestión automática de instalaciones múltiples.

## Telegram Bot API

Cree un bot usando el flujo oficial de Telegram y guarde el token en `TELEGRAM_BOT_TOKEN`. El ID de un chat no es el número de teléfono ni el nombre visible. El bot debe tener acceso al chat; no permite leer conversaciones de una cuenta personal ni comenzar contacto con cualquier usuario arbitrariamente.

```bash
uao enable telegram
```

`get_me` verifica identidad, `send_message` envía texto y `send_photo` usa la referencia admitida por Telegram. `get_updates` admite sondeo; se clasifica como **write** porque avanzar el offset puede confirmar actualizaciones y modificar qué devuelve el proveedor. Por tanto necesita la política de aprobación aunque su finalidad sea obtener eventos.

Webhook y polling no se usan simultáneamente para el mismo bot. Para webhook, elija un secreto aleatorio admisible y guárdelo en `TELEGRAM_WEBHOOK_SECRET`; pase exactamente el mismo valor a `secret_token` de `set_webhook`, junto a su URL HTTPS `/v1/webhooks/telegram`. El secreto dentro de un archivo de solicitud también es confidencial: no lo versione. `get_webhook_info` comprueba estado y `delete_webhook` elimina el registro con aprobación.

El receptor compara `X-Telegram-Bot-Api-Secret-Token`; no lo describa como firma HMAC. El inbox deduplica por update_id. Los bot tokens aparecen en la URL del protocolo Telegram, por lo que este proyecto evita registrar URLs y deshabilita logs de acceso del gateway en los scripts incluidos.

## Discord

Cree una aplicación/bot, instálelo con los permisos necesarios y guarde `DISCORD_BOT_TOKEN`. Se usa el prefijo `Bot` en Authorization. `get_me`, `list_messages`, `send_message` y `edit_message` están implementados por REST; use IDs de canal y mensaje reales y permisos de lectura/envío apropiados.

El acceso al contenido puede depender de permisos/intents y la configuración de Discord. Esta versión no implementa Discord Gateway WebSocket, interactions/slash commands ni comandos entrantes en tiempo real. Tampoco automatiza una cuenta humana como self-bot. [Ejemplo de envío](../../examples/requests/discord-send.json).

## Twilio

Guarde `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN`. `send_message` convierte los parámetros a formulario con `To`, `From` y `Body`; `get_message` y `list_messages` consultan estado/listado. Necesita un remitente y destinatarios admitidos por su cuenta, además de los requisitos del país y canal.

SMS usa direcciones telefónicas apropiadas; WhatsApp a través de Twilio utiliza direcciones del canal y requiere su alta/sandbox o remitente aprobado. El conector actual implementa el envío simple `Body`; **no implementa el constructor de Content Templates de Twilio**. Para plantillas WhatsApp use el conector Meta documentado o agregue esa operación Twilio con su contrato específico.

Los campos de consulta/filtrado admitidos están en YAML. No se incluyó validación de firma de webhook Twilio, callback de estado, recepción de SMS ni voz. No apunte callbacks de Twilio a un handler sin verificar firma. [Ejemplo](../../examples/requests/twilio-send.json).

## SendGrid y Resend

Estos conectores son de **correo transaccional**, no de lectura de bandejas Gmail/Outlook. Cree la cuenta, valide la identidad/dominio de envío de acuerdo con el proveedor y genere un API key con permisos mínimos.

| Sistema | Variable | Operaciones incluidas | Ejemplo |
|---|---|---|---|
| SendGrid | `SENDGRID_API_KEY` | `send_mail` | [JSON](../../examples/requests/sendgrid-send.json) |
| Resend | `RESEND_API_KEY` | `send_mail`, `get_email` | [JSON](../../examples/requests/resend-send.json) |

SendGrid transforma destinatario/asunto/texto al objeto `personalizations` y content; Resend utiliza su cuerpo de envío. El resultado aceptado no equivale a entrega, ausencia de spam o apertura. Esta versión no incluye verificadores de webhooks de entrega/bounce, gestión de listas, campañas ni cancelación de suscripción.

## Costos, cuotas y operación

No se incluyen precios, créditos ni límites comerciales fijos. Consulte la cuenta y documentación vigente antes de contratar. Defina presupuesto y alertas por canal. Un semáforo de concurrencia no controla automáticamente la facturación del proveedor ni las reglas de marketing/consentimiento.

Fuentes oficiales: [SOURCES](../SOURCES.md). Todas las operaciones de esta entrega se verificaron mediante contratos locales simulados, no con cuentas reales.
