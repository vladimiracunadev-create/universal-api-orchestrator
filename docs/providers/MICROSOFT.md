# Outlook y Teams con Microsoft Graph

## Modelo de autenticación

Esta versión utiliza **permisos delegados** y MSAL con device flow. Registre una aplicación en Microsoft Entra, elija el tipo de cuentas permitido y habilite el flujo de cliente público cuando corresponda. El tenant puede prohibir device flow o exigir consentimiento administrativo; siga esas reglas y no intente eludirlas.

```dotenv
MICROSOFT_TENANT_ID=ID_O_AUTORIDAD_ADMITIDA_POR_SU_APP
MICROSOFT_CLIENT_ID=ID_DE_APLICACION
```

No se usa client secret para esta aplicación pública. El JSON de configuración de cada sistema referencia la autoridad `login.microsoftonline.com` y el slot de caché `microsoft`.

Para Outlook con la configuración incluida:

```bash
uao auth-microsoft --scopes User.Read Mail.ReadWrite Mail.Send
uao enable outlook
```

El comando muestra la URL/código para consentir y guarda la caché cifrada. `Mail.ReadWrite` y `Mail.Send` son permisos amplios; para un servicio solo lectura reduzca **también** `auth.scopes` en el YAML (por ejemplo al permiso de lectura correspondiente) antes de autorizar. El bloqueo local de escrituras no reduce por sí mismo el alcance del token en Microsoft.

## Consultar y responder correo

`list_messages` admite campos de consulta definidos en el schema; `get_message` obtiene un mensaje concreto; `list_attachments` devuelve información de adjuntos; `list_folders` lista carpetas. Los cuerpos HTML no se ejecutan: un cliente web que los muestre debe sanitizarlos.

[Ejemplo de lectura](../../examples/requests/outlook-list.json). Para enviar: [outlook-send](../../examples/requests/outlook-send.json), con destinatarios como array. `create_draft` crea el objeto mensaje; `send_draft` lo envía por ID; `reply_message` utiliza el endpoint reply de Graph sobre el mensaje original.

El envío de Graph puede devolver **202 Accepted**: la solicitud fue aceptada, no se confirma con ello la entrega. El gateway devuelve `accepted:true` cuando la respuesta no trae cuerpo y mantiene la distinción en `meta.delivery`. Para comprobar entrega necesita los mecanismos/seguimiento del servicio; no hay consumidor de recibos Microsoft implementado aquí.

## Teams

La configuración utiliza estos permisos delegados:

```bash
uao auth-microsoft --scopes User.Read Mail.ReadWrite Mail.Send Team.ReadBasic.All Channel.ReadBasic.All ChannelMessage.Read.All ChannelMessage.Send
uao enable teams
```

Ese ejemplo combina Outlook y Teams en la misma caché; solicite solo los scopes de los sistemas utilizados y adapte YAML para no pedir más de lo necesario. `ChannelMessage.Read.All` puede requerir revisión/consentimiento adicional de la organización. Si no necesita Outlook, omita sus scopes.

`joined_teams` lista equipos del usuario; `list_channels` lista canales; `list_messages` consulta un canal; `send_message` publica en él. Debe usar IDs reales de equipo y canal y una identidad autorizada. No se presenta un permiso de aplicación para migración/importación como permiso general para enviar mensajes en cualquier canal.

El contenido debe ajustarse al contrato Graph. Esta versión no implementa chats privados, reuniones, llamadas, envío como bot de Bot Framework ni toda la API de Teams.

## Paginación y eventos

Algunas respuestas Graph pueden traer `@odata.nextLink`. El sistema conserva esa información pero no sigue automáticamente URLs recibidas; implemente un mapeo de cursor permitido para cada caso adicional. No se promete recuperar todos los mensajes de una cuenta en una sola operación.

No existen suscripciones/change notifications, endpoint de validación Graph, delta synchronization ni renovación automática de esas suscripciones. Los ejemplos actuales son consultas iniciadas por cliente y envíos autorizados.

## Problemas frecuentes

Una cuenta personal puede no disponer de recursos Teams del tenant. Una app configurada para un tenant no admite automáticamente otras organizaciones. Varias cuentas en la misma caché requieren selección explícita o slots distintos. Consentimiento correcto no reemplaza pertenencia al equipo/canal ni licencia/permisos de la organización.

Consulte [SOURCES](../SOURCES.md) para MSAL, sendMail y mensajes de canal. No se ejecutaron pruebas contra un tenant real al generar este código.
