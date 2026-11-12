# 10 · Configuración

Dos fuentes, con papeles distintos:

| Fuente | Qué define | Se recarga |
|---|---|---|
| `.env` y variables de entorno | Comportamiento del proceso: claves, políticas, límites. | **No.** Se leen al iniciar; hay que reiniciar. |
| `config/systems.yaml` | Qué sistemas y operaciones existen. | Sí, con `uao reload` o `POST /v1/admin/reload`. |

Confundirlas es el malentendido más frecuente: `uao reload` no relee `.env`.

## Variables de proceso

Todas se declaran en `config.py` como un `Settings` de pydantic-settings con `extra="ignore"`: una variable desconocida en `.env` no rompe el arranque. Los campos numéricos llevan cotas, así que un valor absurdo falla al iniciar y no en producción.

### Identidad y políticas

| Variable | Por defecto | Qué hace | Si falta o es inválida |
|---|---|---|---|
| `GATEWAY_API_KEY` | vacío | Autentica a la aplicación cliente. Mínimo 24 caracteres. | Toda ruta `/v1` responde `503 GATEWAY_KEY_NOT_CONFIGURED`. |
| `APPROVAL_API_KEY` | vacío | Aprueba escrituras, reconoce eventos, libera reservas y recarga el catálogo. Mínimo 24 caracteres. | Esas operaciones responden `403`. |
| `ALLOW_WRITES` | `false` | Habilita el envío en esta instancia. | Las escrituras se rechazan con `WRITE_APPROVAL_REQUIRED`. |
| `STATE_KEY` | vacío | Clave Fernet que cifra tokens, reservas e inbox. | **El proceso no arranca.** |
| `STATE_DB` | `data/state.sqlite3` | Ruta del estado. | Se crea el directorio padre si falta. |
| `SYSTEMS_CONFIG` | `config/systems.yaml` | Archivo **o directorio** de catálogo. | Error al arrancar. |
| `APP_ENV` | `development` | Etiqueta informativa. | Sin efecto funcional. |
| `APP_NAME` | `Universal API Orchestrator` | Título en OpenAPI. | — |
| `LOG_LEVEL` | `INFO` | Nivel declarado. | — |

Las tres primeras claves las genera `scripts/bootstrap.py` y **nunca las reemplaza** si ya tienen valor. La comprobación de longitud mínima de 24 caracteres evita que una clave de prueba corta pase por buena.

### Límites de la petición

| Variable | Por defecto | Rango | Qué hace |
|---|---|---|---|
| `REQUEST_TIMEOUT_SECONDS` | 20 | > 0 y ≤ 120 | Tiempo por petición de salida, salvo que la operación declare el suyo. |
| `MAX_CONCURRENCY` | 8 | 1–100 | Semáforo de operaciones simultáneas. |
| `MAX_REQUEST_BYTES` | 2.000.000 | — | Cuerpo máximo de entrada; al superarlo, 413. |
| `MAX_RESPONSE_BYTES` | 4.000.000 | — | Respuesta máxima del proveedor; se corta durante la lectura. |

El límite de 512 kB de adjuntos y media decodificados **no es configurable**: está en los constructores, porque es una decisión de contrato, no de capacidad.

### Red de salida

| Variable | Por defecto | Qué hace |
|---|---|---|
| `ALLOW_PRIVATE_NETWORKS` | `false` | Permite HTTP sin TLS y direcciones no globales. Necesario para un endpoint local de IA o un gRPC interno. |

Activarla desactiva dos controles a la vez: TLS obligatorio y bloqueo de red privada. Con ella puesta, la allowlist de hosts es la única defensa que queda contra SSRF. No la active en una instancia expuesta.

### Pool HTTP

| Variable | Por defecto | Rango |
|---|---|---|
| `HTTP_MAX_CONNECTIONS` | 50 | 1–1000 |
| `HTTP_MAX_KEEPALIVE_CONNECTIONS` | 20 | 0–1000 |
| `HTTP_KEEPALIVE_EXPIRY_SECONDS` | 30 | > 0 y ≤ 600 |

Afectan al rendimiento, no al contrato. Si el proveedor cierra conexiones agresivamente, bajar el tiempo de keepalive evita reutilizar una conexión muerta.

### Control de carga

| Variable | Por defecto | Rango | Qué hace |
|---|---|---|---|
| `RATE_LIMIT_PER_MINUTE` | 120 | 0–100000 | Peticiones por minuto por identidad. **0 desactiva el control.** |
| `RATE_LIMIT_BURST` | 30 | 1–10000 | Reserva de ráfaga. |

`/health` queda fuera. El contador vive en memoria del proceso: ni se comparte entre réplicas ni sobrevive a un reinicio. Si un cliente legítimo recibe 429 de forma sostenida, suba el límite o reparta el tráfico; poner 0 oculta el problema en lugar de resolverlo.

### Retención

| Variable | Por defecto | Rango | Qué hace |
|---|---|---|---|
| `EVENTS_RETENTION_DAYS` | 30 | 1–3650 | Valor por defecto de `uao prune-events`. |
| `REQUESTS_RETENTION_DAYS` | 90 | 1–3650 | Valor por defecto de `uao prune-requests`. |

Son **valores por defecto de un comando manual**, no una purga automática. Nada se borra sin que alguien lo pida, y las purgas nunca tocan eventos sin reconocer ni reservas pendientes.

### Síntesis con modelo

| Variable | Por defecto | Qué hace |
|---|---|---|
| `AI_MODE` | `off` | `off` o `openai_compatible`. |
| `AI_ALLOW_SENSITIVE_DATA` | `false` | Permite enviar a un modelo datos de sistemas marcados `sensitive`. |
| `AI_MAX_INPUT_CHARS` | 24000 | Tamaño máximo de la evidencia enviada. |
| `OPENAI_COMPATIBLE_BASE_URL` | `https://api.openai.com` | Endpoint compatible con Chat Completions. |
| `OPENAI_COMPATIBLE_MODEL` | vacío | Modelo. Sin él, advertencia `AI_MODEL_NOT_CONFIGURED`. |
| `OPENAI_COMPATIBLE_API_KEY` | vacío | Credencial del endpoint. |
| `AI_ALLOWED_HOST` | `api.openai.com` | Allowlist del endpoint de IA. |

Los tres primeros son la frontera que importa. Con `AI_MODE=off` no sale nada. Con el modo activo pero `AI_ALLOW_SENSITIVE_DATA=false`, los 13 proveedores quedan bloqueados (todos son `sensitive`) y la respuesta sale determinista con `AI_SENSITIVE_DATA_BLOCKED`. Poner `true` es una decisión con implicaciones de privacidad: los cuerpos de correo salen hacia el endpoint configurado.

`AI_ALLOWED_HOST` debe coincidir con el host de la URL base: la defensa de salida se aplica también a la llamada al modelo.

### Credenciales de proveedor

El catálogo las referencia como `${VARIABLE}` y el inventario completo está en [`.env.example`](../../.env.example). No se declaran en `config.py`: se leen del entorno en el momento de expandir el sistema, lo que permite arrancar sin tenerlas.

| Proveedor | Variables |
|---|---|
| WhatsApp | `WHATSAPP_GRAPH_VERSION`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` |
| Microsoft | `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID` |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` |
| Slack | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` |
| Discord | `DISCORD_BOT_TOKEN` |
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |
| SendGrid | `SENDGRID_API_KEY` |
| Resend | `RESEND_API_KEY` |
| GitHub | `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET` |

Gmail, Calendar y Drive no usan variables: su token se obtiene con `uao auth-google` y se guarda cifrado en el estado. Una variable **vacía** cuenta como ausente: el catálogo lo rechaza a propósito, porque un prefijo `Bearer` sin valor detrás produciría un error del proveedor mucho más difícil de diagnosticar.

### Compose

`LOCAL_UID` y `LOCAL_GID` los escribe `bootstrap.py` en sistemas POSIX y los usa `docker-compose.yml` para que el contenedor escriba en `data/` con el propietario correcto.

## Configuración del catálogo

Los campos admitidos están en el [capítulo 05](05-technical-reference.md) y el procedimiento para añadir un sistema en [ADDING_CONNECTOR](../ADDING_CONNECTOR.md). Tres reglas:

1. **Un sistema nuevo nace `enabled: false`.** También lo hace el importador de OpenAPI.
2. **`allowed_hosts` es obligatorio.** `verify_repository.py` falla si falta.
3. **`effect` debe ser `read` o `write`,** y el verificador lo comprueba en cada operación.

`SYSTEMS_CONFIG` puede ser un directorio: se cargan todos los `*.yaml` por orden alfabético y un sistema duplicado es un error. Sirve para separar su catálogo propio del que trae el repositorio.

## Precedencia y verificación

Entorno del proceso sobre `.env`; `.env` sobre los valores por defecto de `config.py`. Dentro de una operación: parámetros del cliente sobre `defaults` del catálogo.

```bash
uao doctor      # versión, claves configuradas, política, y estado de cada sistema
uao stats       # política vigente y recuentos del estado
uao catalog     # qué sistemas y operaciones ve el proceso
```

`uao doctor` dice si una clave está configurada, **nunca su valor**. `config_ready_credentials_not_verified` significa que el entorno está completo, no que la cuenta funcione.

## Qué no se debe hacer

No ponga claves en el repositorio: `.gitignore` excluye `.env`, `.env.*` (salvo el ejemplo), `data/`, `secrets/`, `*.sqlite*` y los nombres habituales de credenciales. No comparta `.env` ni capturas con tokens. No rote `STATE_KEY` con estado existente. No active `ALLOW_PRIVATE_NETWORKS` ni `AI_ALLOW_SENSITIVE_DATA` "para probar" en una instancia que toca datos reales. No ponga `RATE_LIMIT_PER_MINUTE=0` para silenciar un bucle de cliente.

## Fuentes de este capítulo

`src/universal_api_orchestrator/config.py`, `.env.example`, `config/systems.yaml`, `scripts/bootstrap.py`, `src/universal_api_orchestrator/registry.py`, `cli.py`, `docker-compose.yml`, `.gitignore`.
