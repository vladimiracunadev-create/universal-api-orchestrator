# 16 · Glosario

El glosario de uso diario está en [GLOSSARY](../GLOSSARY.md) y define los términos **del proyecto**. Este capítulo añade los términos **del dominio** —correo, mensajería y protocolos— con el significado que tienen al leer este código, y señala las trampas de vocabulario.

## Correo electrónico

**MIME.** El formato de un correo real: cabeceras, partes anidadas y codificación del contenido. Gmail no acepta un JSON con `to` y `subject` para enviar: acepta un mensaje MIME completo, codificado en base64url. Por eso existe `builders.mime_message`.

**base64url.** Variante de base64 que usa `-` y `_` en lugar de `+` y `/`, apta para URL. Gmail la usa tanto para el campo `raw` de salida como para el contenido de las partes de entrada. El decodificador del proyecto repone el relleno `=` que Google omite.

**Parte (part).** Un nodo del árbol MIME. Un correo con texto, HTML y un adjunto tiene varias. `mail_content` recorre ese árbol con una pila explícita y prefiere `text/plain`.

**Charset.** La codificación declarada en el `Content-Type` de una parte. Asumir UTF-8 produce acentos rotos en correos antiguos, así que el decodificador lee el declarado y usa `errors="replace"` como último recurso.

**`In-Reply-To` y `References`.** Cabeceras que enlazan un correo con el anterior para que el cliente lo muestre como conversación. Sin ellas, una respuesta aparece como mensaje nuevo.

**`threadId`.** Identificador de hilo propio de Gmail, distinto del identificador de mensaje. Enviar con `threadId` mantiene la respuesta en la conversación.

**Sent items / carpeta de enviados.** El lugar donde comprobar si un envío salió realmente, y el primer sitio al que ir durante una reconciliación.

**SMTP e IMAP.** Los protocolos clásicos de envío y lectura de correo. **No están implementados**: los conectores de correo usan las APIs HTTP de Gmail y Graph.

## Mensajería

**Ventana de atención (customer service window).** En WhatsApp, el periodo —24 horas desde el último mensaje del usuario— en el que se puede enviar texto libre. Fuera de ella solo se admiten plantillas aprobadas. **El gateway no comprueba esa ventana**: el rechazo llega de Meta.

**Plantilla (template).** Mensaje preaprobado por Meta, con parámetros. Aprobarla es un trámite en el proveedor; el gateway solo la envía.

**`messaging_product`.** Campo obligatorio del envelope de WhatsApp Cloud API. Un cuerpo sin él se rechaza, y por eso el constructor lo pone siempre.

**`phone_number_id`.** Identificador del número de negocio emisor. Sale del catálogo, no del cliente: así una petición no puede enviar desde otro número.

**Estado de mensaje (`sent`, `delivered`, `read`).** Eventos que WhatsApp envía por webhook. El mismo mensaje pasa por los tres, y los tres son eventos distintos en el inbox, con claves de deduplicación distintas.

**Recibo de entrega (delivery receipt).** La confirmación de que el destinatario recibió el mensaje. Es lo que `delivery: provider_accepted_not_delivery_receipt` dice que **no** se tiene.

**Bot token.** Credencial de una aplicación de mensajería. En Telegram va **en la ruta**, lo que convierte cualquier URL completa de Telegram en un secreto: de ahí que los errores del gateway nunca incluyan URL.

**Events API (Slack).** El mecanismo de eventos de Slack, con su propia firma: `v0=` más HMAC sobre `v0:timestamp:cuerpo`, con ventana de 300 segundos.

## Autorización

**OAuth 2.** Protocolo por el que un usuario concede a una aplicación acceso limitado a sus datos sin entregarle su contraseña. Lo que se guarda es un token, no una credencial del usuario.

**Scope.** El permiso concreto concedido. `gmail.readonly` permite leer y **no** enviar. Un 403 del proveedor con un token válido suele ser un scope insuficiente.

**Access token y refresh token.** El primero caduca en minutos u horas; el segundo sirve para obtener uno nuevo sin molestar al usuario. Sin refresh token, el error es `OAUTH_CONSENT_REQUIRED`.

**Consentimiento (consent).** El acto por el que el usuario autoriza. Ocurre en el proveedor, en un navegador, y no se puede automatizar: por eso `uao auth-google` abre un servidor local y espera.

**Device code flow.** Variante para dispositivos sin navegador: el usuario pega un código en otra pantalla. Es lo que usa `uao auth-microsoft`.

**Client credentials.** Flujo en el que la aplicación actúa por sí misma, sin usuario. Está implementado, y es distinto de actuar en nombre de alguien.

**MSAL.** Biblioteca de Microsoft para autenticación. Mantiene su propia caché, que aquí se guarda cifrada y serializada. Es síncrona, así que se ejecuta en un hilo.

**Delegado vs. aplicación.** Un permiso delegado actúa como el usuario que consintió; uno de aplicación actúa como la organización. Los conectores de Microsoft usan el primero.

**Revocar.** Retirar un consentimiento en el proveedor. **Borrar el estado local no revoca nada**, y revocar en el proveedor no borra la copia local.

## Protocolos

**REST.** Estilo sobre HTTP con recursos y verbos. Es un transporte, no un contrato: dos APIs REST pueden exigir cuerpos completamente distintos.

**GraphQL.** Un endpoint, una query y variables. Devuelve HTTP 200 con un campo `errors` cuando algo falla, así que el adaptador lo comprueba. Sus consultas son POST y deben declarar `effect: read`.

**JSON-RPC 2.0.** Envelope con `jsonrpc`, `method`, `params` e `id`. El adaptador valida que el `id` y la versión de la respuesta coincidan con lo enviado: una respuesta que no corresponde a la petición es un error, no un resultado.

**SOAP y envelope.** XML con un sobre `Envelope`/`Body`. Un fallo llega como `Fault` dentro de una respuesta 200. El proyecto interpola una plantilla con valores escapados y analiza la respuesta con un parser defensivo.

**WSDL.** El descriptor de un servicio SOAP. **No se consume**: la plantilla del sobre la escribe quien configura el sistema.

**XXE.** Ataque por entidades externas en XML. Es el motivo de usar `defusedxml` para analizar, en lugar del parser estándar.

**gRPC y unary.** RPC sobre HTTP/2 con Protocol Buffers. *Unary* es una llamada con una petición y una respuesta, frente a streaming. El adaptador hace solo unary y con bytes crudos.

**Protobuf y stub.** El formato binario y el código generado desde un `.proto`. Sin stubs, el adaptador no puede tipar nada: de ahí su alcance limitado.

**Webhook.** Petición HTTP que el proveedor hace **hacia** su servicio cuando ocurre algo. Invierte la dirección habitual, y por eso necesita una URL pública y una verificación de firma.

**Challenge.** Comprobación inicial que algunos proveedores hacen antes de registrar un webhook. En Meta es un GET con `hub.mode`, `hub.verify_token` y `hub.challenge`.

## Seguridad

**SSRF.** Hacer que un servidor con credenciales emita una petición a un destino elegido por el atacante: típicamente el servicio de metadatos de la nube. Es la amenaza que explica la allowlist, el bloqueo de direcciones no globales y la prohibición de redirecciones.

**Allowlist.** Lista de lo permitido, frente a una lista de lo prohibido. Más segura porque lo desconocido se rechaza por omisión.

**Dirección no global.** Loopback, red privada, enlace local (`169.254.0.0/16`, donde viven los metadatos de varias nubes) o reservada. `ipaddress.ip_address(x).is_global` lo resuelve sin mantener una lista a mano.

**HMAC.** Código de autenticación de mensaje con una clave compartida. Prueba que el cuerpo viene de quien conoce el secreto y no se modificó.

**`compare_digest`.** Comparación en tiempo constante. Un `==` sobre una firma filtra información por el tiempo que tarda en fallar, carácter a carácter.

**Fernet.** Esquema de cifrado autenticado (AES-CBC más HMAC-SHA256) de la biblioteca `cryptography`. Cifra y detecta modificaciones; es lo que protege tokens, reservas e inbox.

**Inyección de cabeceras.** Insertar `\r\n` en un valor para añadir cabeceras no previstas, por ejemplo un `Bcc`. `EmailMessage` lo rechaza, y de ahí que se use para construir el MIME.

**Prompt injection.** Texto dentro de un dato que intenta dar instrucciones a un modelo. La defensa real aquí no es una instrucción al modelo: es que `/v1/ask` no puede ejecutar acciones.

**WAL (write-ahead logging).** Modo de SQLite en el que las escrituras van a un archivo aparte, de forma que los lectores no se bloquean. Crea los archivos `-wal` y `-shm`, que hay que incluir en un respaldo en caliente.

## Operación

**Idempotencia.** Propiedad de una operación que, repetida, produce el mismo efecto que una sola vez. Aquí se consigue con una clave y la huella del contenido, y es **local**.

**Exactly-once.** La garantía de que algo ocurra exactamente una vez. **No se promete**, y el código lo dice: si un proveedor aceptó un mensaje y se cortó la red, nadie puede afirmarlo desde este lado.

**At-least-once.** Lo que ofrece el inbox: un evento puede entregarse más de una vez a su consumidor, que debe ser idempotente.

**Token bucket.** Algoritmo de limitación: una reserva que se recarga a ritmo constante y permite ráfagas sin perder el promedio.

**Backoff exponencial.** Esperar cada vez más entre reintentos. Se usa solo para GET y HEAD; las escrituras no se reintentan.

**`Retry-After`.** Cabecera con la que un servidor pide esperar. Se respeta, acotada a 10 segundos para que un proveedor no deje colgada una petición.

**Reconciliación.** Cerrar un estado ambiguo comparándolo con la realidad del otro sistema. Es un término contable, y aquí tiene el mismo sentido: no se inventa un saldo, se comprueba.

## Trampas de vocabulario

| Si alguien dice | Aquí significa |
|---|---|
| "enviado" | puede querer decir *aceptado por el proveedor*. No es lo mismo que entregado |
| "funciona" | puede querer decir *las pruebas pasan*. No es lo mismo que probado con una cuenta real |
| "aprobado" | la clave de aprobación se usó. No identifica a una persona |
| "idempotente" | local a esta instancia. No es *exactly-once* |
| "reconocido" (`ack`) | un consumidor local lo procesó. El proveedor no se enteró |
| "seguro" | tiene controles concretos y límites declarados. No está certificado |
| "429" | puede ser del gateway (`RATE_LIMIT_EXCEEDED`) o del proveedor (`UPSTREAM_HTTP_429`) |

## Fuentes de este capítulo

`docs/GLOSSARY.md`, el código y sus comentarios en `connectors/`, `adapters/`, `auth.py`, `security.py`, `store.py` y `webhooks.py`, `docs/SOURCES.md`, y la documentación de los proveedores allí referenciada.
