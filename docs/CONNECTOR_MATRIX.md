# Matriz de conectores y operaciones

Versión 0.3.0 · 13 servicios · 69 operaciones de proveedor. Todas empiezan deshabilitadas. Pruebas de contrato offline; ninguna cuenta externa conectada durante esta entrega.

Los requisitos de parámetros listados aquí son los obligatorios; el schema en `config/systems.yaml` contiene campos opcionales, tipos y límites. La validación remota del proveedor sigue siendo necesaria.

## gmail (15 operaciones)

Correo Gmail / Google Workspace con OAuth delegado.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `get_profile` | read | Ninguno | Leer dirección de la cuenta e identificador de historial. |
| `list_messages` | read | Ninguno | Buscar correos y paginar; devuelve IDs, no todos los cuerpos. |
| `get_message` | read | `id` | Leer mensaje MIME estructurado, cabeceras y partes. |
| `get_thread` | read | `id` | Leer un hilo de correo completo. |
| `get_attachment` | read | `message_id`, `id` | Obtener adjunto codificado base64url; límite del gateway 4 MB. |
| `send_message` | write | `to`, `subject`, `text` | Construir MIME y enviar un correo. |
| `reply_message` | write | `to`, `subject`, `text`, `thread_id`, `in_reply_to`, `references` | Responder conservando threadId, Subject y cabeceras RFC. |
| `create_draft` | write | `to`, `subject`, `text` | Crear borrador MIME, sin enviarlo. |
| `list_drafts` | read | Ninguno | Listar borradores paginados. |
| `send_draft` | write | `id` | Enviar borrador existente por ID. |
| `list_labels` | read | Ninguno | Listar etiquetas de Gmail. |
| `modify_labels` | write | `id` | Agregar o quitar etiquetas, incluidos estados leído/no leído. |
| `list_history` | read | `startHistoryId` | Leer cambios desde un historyId; requiere recuperación ante 404. |
| `watch` | write | `topicName` | Registrar observación mediante Cloud Pub/Sub previamente configurado. |
| `stop_watch` | write | Ninguno | Cancelar observación push. |

## whatsapp (9 operaciones)

WhatsApp Business Platform Cloud API oficial.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `send_text` | write | `to`, `text` | Enviar texto dentro de ventana permitida por Meta. |
| `send_template` | write | `to`, `template_name`, `language` | Enviar plantilla aprobada y componentes. |
| `send_media` | write | `to`, `media_type`, `media` | Enviar imagen/audio/video/documento por ID o enlace HTTPS. |
| `send_interactive` | write | `to`, `interactive` | Enviar objeto interactivo oficial (botones/listas). |
| `mark_read` | write | `message_id` | Marcar mensaje recibido como leído. |
| `upload_media` | write | `filename`, `content_type`, `data_base64` | Subir archivo base64; límite local 512 KB. |
| `get_media_metadata` | read | `media_id` | Consultar metadata y URL temporal de media; no descarga arbitraria. |
| `get_business_profile` | read | Ninguno | Leer perfil de negocio. |
| `list_templates` | read | `waba_id` | Listar plantillas de la WABA autorizada. |

## outlook (9 operaciones)

Outlook / Microsoft 365 mediante Graph delegado.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `get_profile` | read | Ninguno | Consultar perfil del usuario autorizado. |
| `list_messages` | read | Ninguno | Listar o filtrar correos mediante OData. |
| `get_message` | read | `id` | Leer correo. |
| `list_attachments` | read | `id` | Listar adjuntos pequeños en la respuesta. |
| `send_mail` | write | `to`, `subject`, `body` | Enviar correo; 202 significa aceptado, no entregado. |
| `create_draft` | write | `to`, `subject`, `body` | Crear borrador sin enviarlo. |
| `send_draft` | write | `id` | Enviar borrador existente. |
| `reply_message` | write | `id`, `comment` | Responder en el hilo de Microsoft Graph. |
| `list_folders` | read | Ninguno | Listar carpetas de correo. |

## telegram (7 operaciones)

Telegram Bot API; no automatización de cuentas personales.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `get_me` | read | Ninguno | Verificar identidad del bot. |
| `get_updates` | write | Ninguno | Polling y confirmación por offset; no combinar con webhook. |
| `send_message` | write | `chat_id`, `text` | Enviar texto al chat autorizado. |
| `send_photo` | write | `chat_id`, `photo` | Enviar fotografía por file_id o enlace público. |
| `get_webhook_info` | read | Ninguno | Consultar estado del webhook. |
| `set_webhook` | write | `url`, `secret_token` | Registrar HTTPS y secreto del webhook. |
| `delete_webhook` | write | Ninguno | Quitar webhook para usar polling. |

## slack (6 operaciones)

Slack Web API y Events API autenticada.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `auth_test` | read | Ninguno | Verificar token e identidad de workspace. |
| `list_channels` | read | Ninguno | Listar canales visibles al bot. |
| `history` | read | `channel` | Leer historial visible y paginado. |
| `replies` | read | `channel`, `ts` | Leer respuestas de un hilo autorizado. |
| `send_message` | write | `channel`, `text` | Publicar texto y opcionalmente responder en hilo. |
| `update_message` | write | `channel`, `ts`, `text` | Actualizar mensaje del bot. |

## discord (4 operaciones)

Discord REST con bot; Gateway WebSocket no implementado.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `get_me` | read | Ninguno | Verificar cuenta del bot. |
| `list_messages` | read | `channel_id` | Leer mensajes según permisos e intents. |
| `send_message` | write | `channel_id`, `content` | Enviar mensaje sin menciones automáticas. |
| `edit_message` | write | `channel_id`, `message_id`, `content` | Editar mensaje existente. |

## twilio (3 operaciones)

Twilio Messaging API; callbacks de entrega no implementados.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `send_message` | write | `to`, `from`, `body` | Enviar SMS o WhatsApp con remitente aprobado. |
| `get_message` | read | `sid` | Consultar estado de mensaje Twilio. |
| `list_messages` | read | Ninguno | Listar mensajes por filtros. |

## sendgrid (1 operaciones)

SendGrid Mail Send.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `send_mail` | write | `from_email`, `to_email`, `subject`, `text` | Enviar correo transaccional con remitente verificado. |

## resend (2 operaciones)

Resend envío y consulta de correo.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `send_mail` | write | `from`, `to`, `subject`, `text` | Enviar correo transaccional. |
| `get_email` | read | `id` | Consultar correo por identificador. |

## google_calendar (3 operaciones)

Google Calendar con consentimiento independiente.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `list_events` | read | `calendar_id` | Consultar agenda y paginar. |
| `get_event` | read | `calendar_id`, `event_id` | Leer evento. |
| `create_event` | write | `calendar_id`, `event` | Crear evento con fechas RFC3339 y zonas horarias. |

## google_drive (3 operaciones)

Google Drive: búsqueda y exportación de texto.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `list_files` | read | Ninguno | Buscar metadata de archivos, no todos sus contenidos. |
| `get_file` | read | `file_id` | Obtener metadata de archivo. |
| `export_text` | read | `file_id` | Exportar documento compatible a texto plano. |

## teams (4 operaciones)

Microsoft Teams por Graph delegado, sujeto a políticas del tenant.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `joined_teams` | read | Ninguno | Listar equipos del usuario autorizado. |
| `list_channels` | read | `team_id` | Listar canales del equipo. |
| `list_messages` | read | `team_id`, `channel_id` | Leer mensajes de canal permitidos. |
| `send_message` | write | `team_id`, `channel_id`, `content` | Publicar mensaje con autorización delegada. |

## github (3 operaciones)

GitHub REST: repositorios y tickets.

| Operación | Efecto | Requeridos | Propósito |
|---|---|---|---|
| `get_repo` | read | `owner`, `repo` | Consultar metadata del repositorio. |
| `list_issues` | read | `owner`, `repo` | Listar issues y paginar. |
| `create_issue` | write | `owner`, `repo`, `title` | Crear ticket con autorización explícita. |

## Protocolos adicionales

REST, GraphQL, JSON-RPC, SOAP y gRPC unary binario opcional se conservan. Hay cinco configuraciones de ejemplo heredadas; no se cuentan dentro de los 13 servicios ni de las 69 operaciones. Los ejemplos `.invalid` no son proveedores reales.

## No equivale a cobertura total

No se incluyen todos los endpoints, versiones, modos de autenticación, paginación automática ni webhooks de cada servicio. Consulte las guías para límites explícitos. SMTP/IMAP, bases de datos y colas no tienen adaptadores en esta versión.
