# 04 · Mapa del código

27 archivos y 1.630 líneas en `src/universal_api_orchestrator/`. Este capítulo dice qué hace cada uno, a quién llama y qué **no** le corresponde.

```text
src/universal_api_orchestrator/
├── __init__.py              versión del paquete
├── main.py                  aplicación FastAPI, middleware y rutas
├── models.py                contratos de entrada y salida
├── config.py                variables de proceso
├── errors.py                error público estable
├── registry.py              catálogo y sus errores tipados
├── orchestrator.py          política y ejecución
├── auth.py                  credenciales de proveedor
├── transport.py             pool HTTP y límites
├── security.py              defensa de salida
├── ratelimit.py             control de carga
├── store.py                 estado cifrado en SQLite
├── webhooks.py              eventos entrantes
├── response_engine.py       composición con fuentes
├── normalizer.py            selección de campos
├── cli.py                   herramienta local
├── adapters/
│   ├── base.py              interfaz del adaptador
│   ├── rest.py              REST genérico
│   ├── graphql.py           query y variables
│   ├── jsonrpc.py           envelope 2.0 validado
│   ├── soap.py              sobre interpolado y parser defensivo
│   ├── grpc_adapter.py      unary binario opcional
│   └── provider.py          contratos con particularidades
└── connectors/
    ├── builders.py          parámetros al contrato de cada proveedor
    └── mail_content.py      MIME de Gmail a texto legible
```

## Borde HTTP

### `main.py` · 175 líneas

Construye la aplicación con `create_app()`. Contiene:

- `lifespan`: crea registro, almacén, orquestador y limitador; al salir cierra el pool HTTP.
- `body_limit` (middleware): calcula o acepta el `X-Request-Id`, acumula el cuerpo cortando en `MAX_REQUEST_BYTES` (413), aplica el límite de carga (429 con `Retry-After`) y añade `Cache-Control`, `X-Content-Type-Options`, `Referrer-Policy` y `X-Request-Id` a la respuesta.
- `authorize`: compara la clave con `hmac.compare_digest`; 503 si no está configurada, 401 si no coincide.
- `approved` y `require_approval`: la clave de aprobación, como función y como dependencia reutilizable.
- 13 rutas: health, catálogo, ficha de sistema, execute, batch, ask, eventos, ack, reconciliación, liberación, stats, reload y el router de webhooks.

No contiene lógica de negocio: delega en el orquestador y el almacén.

### `models.py` · 59 líneas

`ExecuteRequest` con `extra="forbid"` (un campo desconocido se rechaza, no se ignora), `system` restringido por patrón, `idempotency_key` de 8 a 128 caracteres. `BatchItem` añade alias; `BatchRequest` limita a 20 elementos y valida alias únicos; `AskRequest` añade pregunta y plantilla. `ReleaseRequest` exige `confirmed` y `verified_outcome`. `UnifiedResponse` es el sobre. `Protocol` es un `StrEnum` documental.

### `config.py` · 43 líneas

Un único `Settings` de pydantic-settings con `extra="ignore"`, leído de `.env` y del entorno. Los campos numéricos llevan cotas (`Field(..., ge=, le=)`) para que un valor absurdo falle al arrancar y no en producción. Detalle en el [capítulo 10](10-configuration.md).

### `errors.py` · 5 líneas

`IntegrationError(code, status)`. Pequeño a propósito: es la frontera entre lo que el gateway sabe y lo que publica.

## Catálogo y política

### `registry.py` · 99 líneas

Carga uno o varios YAML (acepta un archivo o un directorio), rechaza sistemas duplicados y definiciones que no sean mapas, y guarda la configuración **sin expandir**. La expansión de `${VARIABLE}` ocurre en `get_system`, por petición: así el proceso arranca sin tener todos los secretos y una variable ausente falla solo en el sistema que la necesita.

Expone `has`, `get_system`, `list_public`, `public_system` y `reload`. Define `SystemDisabled` y `MissingConfiguration`, ambas subclases de `ValueError` para no romper a quien ya capturaba `ValueError`. `reload` reemplaza el catálogo solo si la carga completa tuvo éxito.

### `orchestrator.py` · 109 líneas

El corazón. `resolve` traduce fallos de catálogo a códigos estables. `execute` hace, en orden: resolver, mezclar valores por defecto, validar JSON Schema, calcular el efecto, filtrar cabeceras del llamante, evaluar la política de escritura, tomar el semáforo, obtener credenciales, reservar idempotencia, ejecutar el adaptador, normalizar y armar el sobre. El manejo de errores clasifica en cinco familias y, si ya se había reservado, añade `requires_reconciliation` y `reservation_id`.

`batch` ejecuta en paralelo bajo semáforo, o secuencialmente con `fail_fast`.

## Autorización y transporte

### `auth.py` · 95 líneas

`headers()` despacha por tipo: `none`, `bearer`, `api_key`, `basic`, `oauth2`, `client_credentials` y `msal`. `oauth()` usa un lock por nombre de token y una caché en memoria con margen de 60 segundos, consulta el almacén y solo pide un token nuevo cuando hace falta; persiste el resultado cifrado en el caso `oauth2`. `microsoft()` ejecuta MSAL en un hilo (la biblioteca es síncrona) y guarda la caché serializada si cambió. Un secreto ausente produce `MISSING_CREDENTIALS`, nunca un rastro con el valor.

### `transport.py` · 98 líneas

`get_client()` crea el `AsyncClient` compartido bajo lock, con límites de pool; `close_client()` lo cierra de forma idempotente. `bounded_timeout()` acota cualquier valor a [0,5 ; 120] y cae al valor por defecto si no es numérico. `request()` verifica el endpoint en un hilo, reintenta solo GET y HEAD ante 429/502/503/504 respetando `Retry-After` acotado a 10 segundos, rechaza cualquier respuesta 3xx (no sigue redirecciones), corta la lectura al superar `MAX_RESPONSE_BYTES` y distingue `NETWORK_ERROR` de `NETWORK_OUTCOME_UNKNOWN` según si la operación era reintentable.

### `security.py` · 34 líneas

`assert_safe_endpoint()` rechaza URL con usuario, contraseña o fragmento, esquemas distintos de https/http/tcp, hosts fuera de la allowlist, HTTP sin TLS salvo habilitación explícita, fallos de DNS y cualquier dirección resuelta que no sea global. `safe_caller_headers()` rechaza las cinco cabeceras prohibidas y cualquiera que el sistema no declare.

### `ratelimit.py` · 47 líneas

Token bucket por identidad. `identity()` devuelve el resumen SHA-256 truncado de la clave, o de la dirección del cliente si no hay clave. `check()` recarga, decide y devuelve los tokens restantes y la espera sugerida. `_evict()` descarta buckets ya recargados para que el diccionario no crezca sin límite.

## Estado y eventos

### `store.py` · 180 líneas

Tres tablas y cifrado Fernet para todo valor con contenido. Cada conexión activa WAL, `synchronous=NORMAL` y `busy_timeout`. `reserve()` abre una transacción inmediata, distingue conflicto de pendiente y guarda cifrado qué se intentó. `complete()` cierra la reserva con el sobre. `pending()`, `release()`, `prune()`, `prune_requests()` y `stats()` sirven a la operación. Detalle en el [capítulo 07](07-database.md).

### `webhooks.py` · 83 líneas

`verify_signature()` implementa cuatro esquemas: token secreto de Telegram, firma con marca de tiempo de Slack (ventana de 300 segundos) y HMAC SHA-256 sobre el cuerpo para Meta y GitHub. Todas con `hmac.compare_digest`. `extract_events()` separa los mensajes y estados que WhatsApp agrupa en un envelope y elige una clave de deduplicación por proveedor. La verificación ocurre **sobre los bytes originales y antes** de deserializar.

## Composición

### `response_engine.py` · 53 líneas

`compose_answer()` separa resultados correctos de fallidos, construye la lista de fuentes con alias, sistema, operación y trace, y reduce la evidencia con `evidence_for_ai`. En modo determinista presenta los datos o aplica la plantilla. Con IA activada comprueba, en orden: datos sensibles permitidos, modelo configurado y tamaño de entrada; cualquier fallo del modelo vuelve a determinista con advertencia. Siempre devuelve `sent: false`.

### `normalizer.py` · 9 líneas

Aplica el `response_map` con JMESPath. Sin mapa, devuelve el payload tal cual.

## Adaptadores

`base.py` define la interfaz abstracta. `rest.py` arma la petición con `generic()`. `graphql.py` exige que la respuesta no traiga `errors`. `jsonrpc.py` valida que el `id` y la versión del envelope coincidan con lo enviado. `soap.py` escapa valores con una función propia, interpola la plantilla, analiza con `defusedxml` y detecta `Fault`. `grpc_adapter.py` hace una llamada unary binaria con TLS salvo habilitación explícita de red privada. `provider.py` usa el constructor del proveedor, detecta el `ok:false` de Slack y Telegram, y normaliza el MIME de Gmail.

## Conectores

`builders.py` traduce parámetros al contrato concreto: rutas con valores codificados, plantillas de query, cuerpo o formulario, MIME con `EmailMessage` (que rechaza inyección CR/LF en cabeceras), envelope de WhatsApp, destinatarios y adjuntos de Graph, y el límite de 512 kB de carga decodificada.

`mail_content.py` recorre el árbol MIME o el `raw`, decodifica con el charset declarado, convierte HTML a texto descartando `script` y `style`, lista adjuntos sin descargarlos y trunca a 100.000 caracteres marcando `truncated`. `evidence_for_ai` reduce un mensaje a identificador, hilo, extracto y `_content` para no duplicar cuerpos codificados hacia un modelo.

## Herramienta local

`cli.py` · 146 líneas. 18 comandos en tres familias: configuración local, consentimiento OAuth y llamadas al servidor. Nunca imprime credenciales; ante un error devuelve un mensaje genérico y código 1, y código 2 cuando el servidor respondió pero la operación falló.

## Scripts y herramientas

`scripts/bootstrap.py` prepara claves y carpetas sin reemplazar nada. `scripts/verify_repository.py` comprueba sintaxis, catálogo, esquemas, ejemplos, enlaces, versión y codificación. `scripts/release.py` empaqueta un ZIP reproducible sin estado ni secretos, con su SHA-256. `scripts/demo_offline.py` ejecuta una suite simulada e identificada como tal. `tools/import_openapi.py` genera un fragmento de catálogo desde un OpenAPI, **deshabilitado** y clasificando el efecto por método.

## Dependencias entre módulos

```text
main ──> orchestrator ──> adapters ──> transport ──> security
  │           │               └──────> connectors
  │           ├──> registry
  │           ├──> auth ──────────────> transport
  │           └──> store
  ├──> ratelimit
  ├──> response_engine ──> transport, connectors.mail_content
  └──> webhooks ──> store, registry
```

Nadie importa `main`, y `config` y `errors` son hojas que todos pueden usar. No hay ciclos: `transport` no conoce adaptadores y `store` no conoce HTTP.

## Fuentes de este capítulo

Lectura directa de los 27 archivos de `src/universal_api_orchestrator/`, más `scripts/` y `tools/`.
