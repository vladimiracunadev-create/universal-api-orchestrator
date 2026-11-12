# CLI: comandos de `uao`

`uao` es una herramienta local. Hace tres cosas distintas y conviene no confundirlas: **configura** el catálogo y el estado en su equipo, **obtiene consentimiento** OAuth abriendo un flujo en su navegador, y **llama** al servidor HTTP como cualquier otro cliente.

Nunca imprime credenciales. Ante un error devuelve un mensaje genérico y código de salida distinto de cero, precisamente para no volcar un token en la terminal o en un archivo de registro.

```bash
uao --url http://127.0.0.1:8080 <comando> [opciones]
```

`--url` solo afecta a los comandos que hablan con el servidor. El valor predeterminado es `http://127.0.0.1:8080`.

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | El comando terminó y, si consultó, la respuesta no traía errores. |
| 1 | Error de uso, de archivo, de variables, de extras no instalados o de conexión. |
| 2 | El servidor respondió, pero la operación falló (`ok:false` o `errors` con contenido). |

Ese 2 es deliberado: `HTTP 200` del gateway puede contener una operación fallida, y un script no debería tratarlo como éxito.

## Configuración local

Estos comandos no contactan al servidor ni a ningún proveedor.

| Comando | Qué hace | Qué **no** hace |
|---|---|---|
| `uao catalog` | Imprime el catálogo público: sistemas, operaciones, efecto y esquemas. | No muestra base URLs con token, secretos ni cabeceras de autenticación. |
| `uao doctor` | Informa versión, Python, si las claves están configuradas, modo de IA, límite de carga, si se permiten redes privadas y el estado de cada sistema. | **No** verifica una sesión con el proveedor. `config_ready_credentials_not_verified` significa que el entorno está completo, no que la cuenta funcione. |
| `uao enable <sistema>` | Marca `enabled: true` en `config/systems.yaml`. | No concede permisos ni valida credenciales. Recuerde `uao reload`. |
| `uao disable <sistema>` | Marca `enabled: false`. | No revoca un consentimiento OAuth ya concedido. |
| `uao prune-events --days N` | Borra del inbox los eventos **ya reconocidos** anteriores a N días. | No borra eventos sin reconocer. |
| `uao prune-requests --days N` | Borra las reservas de idempotencia **completadas** anteriores a N días. | No toca una reserva pendiente de reconciliación. |

Los valores predeterminados de `--days` provienen de `EVENTS_RETENTION_DAYS` (30) y `REQUESTS_RETENTION_DAYS` (90).

## Consentimiento OAuth

```bash
uao auth-google --client secrets/google-client.json --token-key google \
  --scopes https://www.googleapis.com/auth/gmail.readonly
```

Abre un servidor local en `127.0.0.1:8765` (cambie con `--port`, o use `--no-browser` en una máquina sin navegador), completa el flujo de aplicación de escritorio y guarda el resultado **cifrado** en el estado local. Pida solo los scopes que vaya a usar: `gmail.readonly` no permite enviar.

```bash
uao auth-microsoft --token-key microsoft --scopes Mail.Read
```

Usa device code flow: imprime un código para pegar en el portal de Microsoft. Requiere `MICROSOFT_TENANT_ID` y `MICROSOFT_CLIENT_ID` y el extra `auth` instalado. Guarda la caché MSAL cifrada.

Ninguno de los dos lee correos ni envía nada: solo obtienen y guardan el permiso.

## Operación contra el servidor

| Comando | Endpoint | Notas |
|---|---|---|
| `uao health` | `GET /health` | No necesita clave. Dice que el proceso responde, nada más. |
| `uao stats` | `GET /v1/stats` | Recuentos del estado local y política vigente. |
| `uao execute <archivo>` | `POST /v1/execute` | Una operación descrita en un JSON. |
| `uao batch <archivo>` | `POST /v1/batch` | Hasta 20 operaciones independientes. |
| `uao ask <archivo>` | `POST /v1/ask` | Compone una respuesta con fuentes. Rechaza toda escritura. |
| `uao events` | `GET /v1/events` | Eventos recibidos y sin reconocer. |
| `uao ack <id>` | `POST /v1/events/{id}/ack` | Envía la clave de aprobación automáticamente. |
| `uao pending` | `GET /v1/reconciliation` | Escrituras cuyo resultado real se desconoce. |
| `uao release <id> ...` | `POST /v1/reconciliation/{id}/release` | Ver abajo. |
| `uao reload` | `POST /v1/admin/reload` | Relee el catálogo sin reiniciar. Requiere aprobación. |

### Aprobar una escritura

```bash
uao execute /ruta/privada/solicitud-revisada.json --approve
```

`--approve` añade la cabecera `X-Approval-Key` con el valor de su `.env`. **No modifica `confirmed` dentro del archivo**: ejecutar un ejemplo por descuido no lo aprueba. Para que una escritura salga hacen falta, a la vez, `ALLOW_WRITES=true` en el servidor, esa cabecera, `confirmed:true` en el JSON y una `idempotency_key` sin conflicto.

Copie el ejemplo, edítelo y revise destinatario y contenido antes de usarlo. No reutilice una `idempotency_key` para otro contenido: la huella incluye sistema, operación, parámetros y cabeceras.

### Liberar una reserva en duda

```bash
uao pending
uao release <id-de-reserva> --verified-outcome not_delivered --confirm --note "Buzón revisado: no llegó"
```

`--confirm` es obligatorio y `--verified-outcome` admite `not_delivered`, `delivered_duplicate_acceptable` y `delivered_do_not_retry`. El último **conserva** la reserva a propósito: si el proveedor sí entregó el mensaje y un duplicado sería inaceptable, el bloqueo debe quedarse. Liberar no contacta al proveedor ni deshace nada: es su afirmación de haber comprobado el resultado real. El procedimiento completo está en [RECONCILIATION](RECONCILIATION.md).

## Formato de los archivos de petición

`execute` acepta el cuerpo de `/v1/execute`; `batch` y `ask`, el suyo. Hay ejemplos reales en [`examples/requests`](../examples/requests) y colecciones equivalentes en [Postman](../examples/postman/collection.json).

```json
{
  "system": "gmail",
  "operation": "list_messages",
  "params": {"q": "is:unread", "maxResults": 5}
}
```

## Qué no hace la CLI

No es un cliente interactivo ni un panel: no pagina sola, no guarda los resultados en disco, no reintenta, no programa tareas y no decide qué operación llamar a partir de una frase. Tampoco administra cuentas: crear la aplicación OAuth, habilitar APIs, aprobar plantillas o pagar consumos se hace en el proveedor.
