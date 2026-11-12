# Gmail y Google Workspace

## Crear la autorización

En Google Cloud seleccione/cree el proyecto, habilite Gmail API y configure la pantalla de consentimiento con los usuarios de prueba o audiencia correspondiente. Cree credenciales OAuth para **aplicación de escritorio** y guarde su JSON en `secrets/google-client.json`, que no debe versionarse.

Después de instalar el extra `auth`, ejecute desde su equipo:

```bash
uao auth-google --client secrets/google-client.json --token-key google --scopes https://www.googleapis.com/auth/gmail.readonly
uao enable gmail
```

Se abre el consentimiento en Google y un callback temporal en `127.0.0.1:8765`. La biblioteca oficial usa PKCE; no se solicita la contraseña por este servidor. Al aceptar, se guarda el token y la información de refresco cifrados en `data/state.sqlite3`.

En Windows use `.\.venv\Scripts\uao.exe` en lugar de `uao` si no activó el entorno. En Docker autorice preferentemente en el host y comparta estado/STATE_KEY como explica [ENVIRONMENTS](../ENVIRONMENTS.md). `--no-browser` imprime la autorización para abrirla manualmente, pero no elimina la necesidad de que el callback alcance el proceso local.

## Permisos mínimos

`gmail.readonly` permite consultas, no envíos ni cambios. Para ampliar, vuelva a autorizar con el conjunto de scopes necesario. Use scopes de Gmail como `gmail.send`, `gmail.compose` o `gmail.modify` según la operación; verifique su alcance en la documentación oficial. Ejemplo para lectura y envío (no todos los cambios de etiquetas):

```bash
uao auth-google --client secrets/google-client.json --token-key google --scopes https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send
```

Una operación de borrador requiere permisos de composición, y modificar etiquetas requiere permisos de modificación. Los requisitos de verificación de aplicaciones, políticas de usuarios externos y restricciones del administrador de Workspace dependen de los scopes y audiencia. El código no evita esa revisión. No implemente delegación de dominio copiando una service account en el lugar del JSON de escritorio: ese flujo no está implementado.

## Buscar, leer y comprender el resultado

```bash
uao execute examples/requests/gmail-search.json
python examples/workflows/gmail_brief.py --query "is:unread" --limit 3
```

`list_messages` devuelve IDs/hilos y un posible pageToken, no cuerpos completos. `get_message` recupera el mensaje; `get_thread` recupera el hilo. El adaptador mantiene campos nativos y añade `_content` cuando existe MIME: asunto, remitente, destinatario, fecha, texto y referencias a adjuntos. Se prefiere texto plano y se extrae texto de HTML sin ejecutar scripts ni cargar recursos remotos. El texto está acotado a 100.000 caracteres y marca truncamiento.

El modo `metadata` puede no incluir cuerpo. `get_attachment` obtiene datos codificados; nunca se descargan adjuntos implícitamente al pedir un resumen. El flujo de ejemplo hace dos etapas: buscar IDs y consultarlos explícitamente desde `/ask`.

La composición determinista devuelve evidencia organizada. Un resumen semántico solo aparece al configurar un modelo y permitirle datos sensibles. Las fuentes conservan alias e identificadores: revise siempre la respuesta antes de enviarla a otra persona.

## Escribir, responder y gestionar borradores

`send_message` construye MIME RFC 2822, lo codifica base64url y envía `raw`. Soporta texto, HTML, copia, copia oculta y adjuntos pequeños. El límite decodificado conjunto de adjuntos es 512.000 bytes, una decisión del gateway y no el máximo del servicio.

`reply_message` requiere recuperar el hilo correcto y pasar `thread_id`, `in_reply_to`, `references`, destinatario y asunto compatibles con el mensaje original. El thread ID del API y el Message-ID de la cabecera no son el mismo identificador. No adivine ninguno ni confunda responder con un correo nuevo.

`create_draft` crea un borrador en Gmail; `list_drafts` permite verlo y `send_draft` lo envía por ID. Aunque un borrador no se entrega todavía al destinatario, modifica una cuenta externa: está clasificado como escritura y exige aprobación. No existe interfaz gráfica de edición de borradores dentro del repositorio.

Revise los ejemplos [gmail-send](../../examples/requests/gmail-send.json) y [gmail-draft](../../examples/requests/gmail-draft.json). Ambos empiezan no confirmados. Para evitar suplantación, omita `from` y use la identidad autorizada, o configure un remitente válido que la cuenta tenga permitido.

## Etiquetas e historial

`list_labels` lista etiquetas, `modify_labels` las agrega/elimina sobre un mensaje y `list_history` permite consultar cambios desde un history ID válido. No hay barrido automático de todo el buzón ni borrado masivo. Controle pageToken y los campos mínimos necesarios para su proceso.

## Notificaciones: watch no es todo el sistema push

`watch` registra un tópico Pub/Sub; `stop_watch` detiene el registro. Gmail envía notificaciones a Cloud Pub/Sub y el consumidor debe consultar history para conocer cambios reales. Además se debe renovar watch antes de su expiración y conservar el cursor de historial.

Aquí están implementadas las operaciones HTTP **watch/history**, pero no el consumidor Pub/Sub autenticado, la renovación programada ni una sincronización incremental durable. La integración entrante completa requiere esos componentes; no se presenta un webhook genérico como sustituto.

## Recuperación y seguridad

`OAUTH_CONSENT_REQUIRED` indica falta de token de refresco almacenado. Un rechazo remoto puede ser revocación, scopes insuficientes o restricción de la app. Compruebe las políticas de su consola antes de reautorizar. Proteja tanto la base de datos como STATE_KEY, y nunca envíe `google-client.json` por un canal público.

Fuentes oficiales, scopes y conceptos utilizados: [SOURCES](../SOURCES.md). Las cuentas Gmail/Workspace no fueron conectadas durante las pruebas de esta entrega.
