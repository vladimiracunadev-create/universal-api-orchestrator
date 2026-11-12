# 09 · APIs e integraciones

Dos direcciones: las **APIs que este servicio consume** (13 proveedores y 5 ejemplos de protocolo) y la **API que expone** a su aplicación. La enumeración operación por operación está en la [matriz de conectores](../CONNECTOR_MATRIX.md); aquí está el contrato técnico de cada integración y sus límites reales.

## Resumen del catálogo

| Sistema | Protocolo | Ops | Autorización | Host permitido | Webhook | Sensible |
|---|---|---:|---|---|---|---|
| `gmail` | provider | 15 | OAuth 2 con refresco | `gmail.googleapis.com` | — | sí |
| `whatsapp` | provider | 9 | bearer | `graph.facebook.com` | meta | sí |
| `outlook` | provider | 9 | MSAL delegado | `graph.microsoft.com` | — | sí |
| `telegram` | provider | 7 | token en la ruta | `api.telegram.org` | telegram | sí |
| `slack` | provider | 6 | bearer | `slack.com` | slack | sí |
| `discord` | provider | 4 | bearer (`Bot`) | `discord.com` | — | sí |
| `twilio` | provider | 3 | basic | `api.twilio.com` | — | sí |
| `sendgrid` | provider | 1 | bearer | `api.sendgrid.com` | — | sí |
| `resend` | provider | 2 | bearer | `api.resend.com` | — | sí |
| `google_calendar` | provider | 3 | OAuth 2 | `www.googleapis.com` | — | sí |
| `google_drive` | provider | 3 | OAuth 2 | `www.googleapis.com` | — | sí |
| `teams` | provider | 4 | MSAL delegado | `graph.microsoft.com` | — | sí |
| `github` | provider | 3 | bearer | `api.github.com` | github | sí |
| `jsonplaceholder` | rest | 1 | ninguna | `jsonplaceholder.typicode.com` | — | no |
| `countries_graphql_demo` | graphql | 1 | ninguna | `countries.trevorblades.com` | — | no |
| `jsonrpc_example` | jsonrpc | 1 | ninguna | `example.invalid` | — | no |
| `soap_example` | soap | 1 | ninguna | `example.invalid` | — | no |
| `grpc_example` | grpc | 1 | ninguna | `localhost` | — | no |

**Los 13 proveedores empiezan deshabilitados.** Los cinco ejemplos de protocolo existen para documentar la forma del catálogo: tres apuntan a `example.invalid` o `localhost` y no funcionarán sin reemplazar el destino. Todos los proveedores están marcados `sensitive: true`, que es lo que impide enviar sus datos a un modelo sin autorización explícita.

## Integraciones con constructor propio

Tres proveedores no se pueden describir solo con plantillas de catálogo.

### Gmail

Las operaciones de lectura son REST declarativo. Las de escritura pasan por `builders.gmail`, que construye un mensaje MIME real con `EmailMessage` y lo codifica en base64url: Gmail no acepta un JSON con campos `to` y `subject`, acepta un correo. El constructor gestiona `To`, `From`, `Subject`, `Cc`, `Bcc`, `In-Reply-To` y `References`, alternativa HTML, adjuntos con su tipo MIME y `threadId` para responder en un hilo. `create_draft` envuelve el mismo cuerpo en `{"message": ...}`.

En la respuesta, `provider.py` llama a `normalize_gmail`, que añade `_content` cuando hay MIME: asunto, remitente, destinatario, fecha, texto decodificado con el charset declarado, lista de adjuntos y los indicadores `truncated` y `body_available`. Un listado de identificadores **no** lleva `_content`.

Límites reales: 512 kB de adjuntos decodificados por mensaje (del gateway, no de Gmail); 100.000 caracteres de texto extraído; los adjuntos se listan pero no se descargan; `watch` registra la suscripción pero **no hay consumidor de Pub/Sub**, así que las notificaciones de Gmail no llegan al inbox. Eso está en el [ROADMAP](../../ROADMAP.md), no implementado.

### WhatsApp Cloud API

`builders.whatsapp` arma el envelope que exige Meta: `messaging_product`, `recipient_type`, `to`, el tipo y su objeto. Cubre texto, plantilla con idioma y componentes, multimedia, interactivo, recibo de lectura y subida de medios como multipart. El `phone_number_id` sale del catálogo, no del cliente.

Límites reales: 512 kB de media decodificada; **la ventana de atención de 24 horas y la aprobación de plantillas son del proveedor y el gateway no las comprueba** (una plantilla no aprobada se rechaza en Meta, no aquí); los estados de entrega llegan por webhook y se extraen individualmente, con lo que es el único canal donde se puede seguir la entrega real.

### Outlook y Microsoft Graph

`builders.outlook` traduce a la forma de Graph: `toRecipients` como lista de objetos `emailAddress`, `body` con `contentType`, y adjuntos con `@odata.type` y `contentBytes`. `send_mail` usa `/me/sendMail` con `saveToSentItems`; `create_draft` crea el mensaje sin enviarlo.

La autorización es MSAL **delegado**: actúa como un usuario que dio consentimiento, no como una aplicación con permisos de organización. `acquire_token_silent` requiere exactamente una cuenta en la caché; con ninguna o varias, el error es `MSAL_CONSENT_OR_ACCOUNT_SELECTION_REQUIRED`.

Límite real declarado: algunos endpoints de Graph devuelven `@odata.nextLink`, y **no hay consumidor genérico de paginación**. Quien necesite recorrer páginas debe mapear el cursor en su propio `response_map`.

## Integraciones declarativas

Telegram, Slack, Discord, Twilio, SendGrid, Resend, Calendar, Drive, Teams y GitHub se describen con plantillas del catálogo. Particularidades que sí están implementadas:

- **Telegram** pone el token en la ruta, de modo que una URL completa de Telegram es un secreto: por eso los errores del gateway nunca incluyen URL.
- **Slack y Telegram** responden HTTP 200 con `ok: false` cuando rechazan algo. `provider.py` lo detecta y lo convierte en `PROVIDER_REJECTED_REQUEST`, en lugar de devolver un éxito falso.
- **Discord** exige el prefijo `Bot` en la autorización, y el constructor retira `message_reference` cuando está vacío porque la API lo rechaza.
- **Twilio** usa basic con SID y token. Cubre SMS y, según la cuenta, direcciones de WhatsApp.
- **Google Drive** incluye exportación de documentos a texto; no sincroniza ni descarga binarios grandes.
- **GitHub** cubre repositorios e issues, con webhook firmado con HMAC SHA-256.

## Protocolos genéricos

| Protocolo | Qué valida | Qué no cubre |
|---|---|---|
| REST | Esquema de parámetros, plantillas de query, cuerpo y formulario. | — |
| GraphQL | Rechaza la respuesta si trae `errors`. | No construye queries: la query está en el catálogo. Un POST de consulta debe declarar `effect: read`. |
| JSON-RPC | Que `id` y `jsonrpc` de la respuesta coincidan con lo enviado. | Lotes, notificaciones sin respuesta. |
| SOAP | Escapa valores, interpola la plantilla, analiza con `defusedxml` y detecta `Fault`. | WSDL, WS-Security, MTOM. La plantilla del sobre la escribe usted. |
| gRPC | Unary binario con TLS; `insecure` solo con redes privadas habilitadas. | Streaming, reflexión y contratos tipados: necesita stubs generados. |

## La API que expone

13 rutas, descritas en el [capítulo 05](05-technical-reference.md). Puntos para quien integra:

- **Un solo contrato.** Cambiar de proveedor no cambia la forma de la petición ni del sobre; cambian los parámetros de la operación.
- **Dos niveles de estado.** `HTTP 200` con `ok:false` es normal. Revise siempre `ok`.
- **La clave del gateway no es la del proveedor.** Su aplicación nunca ve un token de Gmail o de Meta.
- **Escribir exige cuatro condiciones.** Una variable de entorno no basta.
- **`/v1/ask` no puede enviar.** Devuelve siempre `sent: false`.
- **Hay límite de carga local.** Respete `Retry-After`; no es el 429 del proveedor.
- **Correlación.** Envíe su `X-Request-Id`; se devuelve si tiene formato seguro.

Clientes de ejemplo en [Python](../../examples/clients/python_client.py), [Node.js](../../examples/clients/node_client.mjs), [PHP](../../examples/clients/php_client.php), [PowerShell](../../examples/clients/powershell_client.ps1), [cURL](../../examples/curl.sh) y [Postman](../../examples/postman/collection.json).

## Lo que no está integrado

SMTP e IMAP con autenticación moderna, medios de pago, CRM y ERP concretos, almacenamiento de objetos, SFTP, bases de datos, colas y transporte streaming. Tampoco Pub/Sub de Gmail, suscripciones de Graph ni los webhooks de entrega de Twilio, SendGrid y Resend: esos tres proveedores se pueden consultar, pero sus eventos de estado no llegan al inbox.

Cada uno requiere contrato, documentación y pruebas, no una entrada con nombre comercial en el catálogo. La prioridad está en el [ROADMAP](../../ROADMAP.md).

## Estado de verificación

**Ninguna de estas 13 integraciones se ha ejecutado contra una cuenta real en esta entrega.** Lo que está probado son los constructores, los esquemas, el manejo de errores y la normalización, con transporte simulado: 162 pruebas. La ficha para registrar la aceptación real, proveedor por proveedor, está en [VALIDATION](../VALIDATION.md).

Un proveedor puede cambiar su API sin avisar. Las fuentes consultadas y su fecha están en [SOURCES](../SOURCES.md); al tocar un conector hay que volver a comprobarlas.

## Fuentes de este capítulo

`config/systems.yaml`, `src/universal_api_orchestrator/connectors/builders.py`, `connectors/mail_content.py`, `adapters/`, `auth.py`, `webhooks.py`, `docs/CONNECTOR_MATRIX.md`, `docs/providers/`, `docs/SOURCES.md`.
