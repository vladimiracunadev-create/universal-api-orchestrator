# 06 · Explicación profunda del código

Este capítulo explica las decisiones que no se entienden leyendo la firma de una función: por qué el orden importa, qué pasaría si se cambiara, y qué error real previene cada línea rara.

## El orden en `orchestrator.execute`

```python
system, operation = self.resolve(system_name, operation_name)
params = {**operation.get("defaults", {}), **params}
validate(params, operation.get("input_schema", {"type": "object"}))
effect = operation.get("effect", "read" if operation.get("method", "POST") in {"GET","HEAD"} else "write")
outgoing = {**system.get("headers", {}), **operation.get("headers", {}),
            **safe_caller_headers(headers or {}, system.get("allowed_request_headers", []))}
if effect != "read":
    ...   # política
async with self.semaphore:
    outgoing.update(await self.auth.headers(system.get("auth", {})))
    if effect != "read":
        replay = self.store.reserve(...)
    status, payload = await adapter.execute(...)
```

Cinco decisiones de orden, todas deliberadas:

**1. Los valores por defecto se mezclan antes de validar.** Si se validara primero, un esquema con `required` fallaría por un campo que el catálogo iba a rellenar. Y los del cliente ganan a los del catálogo, porque los `defaults` son una comodidad, no una restricción.

**2. El efecto se calcula con un sesgo hacia `write`.** Si la operación no declara `effect`, un POST se considera escritura. Equivocarse hacia "esto podría enviar algo" es barato; equivocarse al contrario manda un mensaje. Un POST de consulta —GraphQL, por ejemplo— tiene que declarar `read` explícitamente, y solo puede hacerlo el catálogo, que es confiable.

**3. Las cabeceras del llamante se filtran en la misma expresión que las construye.** `safe_caller_headers` lanza si hay algo prohibido, así que no existe un punto intermedio donde `outgoing` contenga una cabecera no validada. Y el orden de la mezcla importa: las del llamante van al final porque ya pasaron el filtro, de modo que `allowed_request_headers` es la única puerta.

**4. La política se evalúa antes de tomar el semáforo.** Un cliente que intente escribir sin aprobación no consume una ranura de concurrencia: el rechazo es inmediato y no afecta al tráfico legítimo.

**5. Las credenciales se obtienen antes de reservar la clave de idempotencia.** Este es el más sutil. Si se reservara primero y el token faltara, la clave quedaría bloqueada por un problema de configuración que no tiene nada que ver con el envío; el operador tendría que reconciliar algo que nunca salió. El comentario del código lo dice: *credenciales ausentes no bloquean una clave*.

## Por qué `execute` nunca lanza

El método termina siempre en un `UnifiedResponse`. Cinco familias de error:

```python
except IntegrationError as exc:   code, status = exc.code, exc.status
except ValidationError:           code, status = "INVALID_INPUT_SCHEMA", 422
except (KeyError, ValueError):    code, status = "INVALID_OPERATION_CONFIGURATION_OR_INPUT", 400
except Exception:                 code, status = "INTEGRATION_FAILURE", None
```

El `except Exception` final es intencional y, en un gateway, es la decisión correcta: un fallo inesperado no debe convertirse en un trazado de pila con URL, cabeceras o fragmentos de correo en la respuesta HTTP. El cliente recibe `INTEGRATION_FAILURE` y el `trace_id`; el detalle se busca cruzando con el registro del proveedor.

El motivo adicional es `batch`: un elemento que lanzara excepción tumbaría el `asyncio.gather` y con él las demás operaciones, algunas ya ejecutadas. Devolver un sobre con `ok:false` mantiene el contrato.

## La reserva de idempotencia, línea a línea

```python
def reserve(self, key, request):
    fingerprint = self.digest(json.dumps(request, sort_keys=True))
    key = self.digest(key)
    with self.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM requests WHERE key=?", (key,)).fetchone()
        if row:
            if row["fingerprint"] != fingerprint:
                raise IntegrationError("IDEMPOTENCY_CONFLICT", 409)
            if row["status"] != "complete":
                raise IntegrationError("OUTCOME_PENDING_OR_UNKNOWN_RECONCILE", 409)
            return self.decode(row["payload"])
        db.execute("INSERT INTO requests VALUES (?,?,'pending',?,?)",
                   (key, fingerprint, self.encode({"attempt": request}), time.time()))
    return None
```

- `sort_keys=True` hace la huella estable: el mismo contenido en otro orden de claves no cuenta como una petición distinta.
- La clave se **hashea** antes de guardarse. No es un secreto, pero tampoco hay motivo para almacenarla en claro, y el hash da un identificador de longitud fija que sirve como `reservation_id`.
- `BEGIN IMMEDIATE` toma el bloqueo de escritura al empezar. Sin eso, dos peticiones concurrentes con la misma clave podrían leer "no existe" las dos y enviar las dos.
- Tres resultados posibles: conflicto (otro contenido), pendiente (resultado desconocido) o repetición servida desde la reserva. El cuarto caso, reservar, devuelve `None` y el llamante sabe que debe ejecutar.
- Desde 0.3.0 la fila pendiente guarda `{"attempt": request}` cifrado. Antes el `payload` era nulo y una reserva en duda no se podía inspeccionar: el operador veía un hash y nada más. Ahora `pending()` puede decir qué sistema y qué operación quedaron abiertos, sin exponer el contenido del mensaje.

## Por qué liberar una reserva es tan incómodo

Liberar exige, a la vez: clave de aprobación, `confirmed:true`, un `verified_outcome` de una lista cerrada, y que ese resultado no sea `delivered_do_not_retry`. Cuatro obstáculos para una operación que borra una fila.

La incomodidad es el punto. La reserva existe porque alguien no sabe si se envió un mensaje; quitarla sin comprobarlo convierte el mecanismo en decoración. El campo `verified_outcome` obliga a escribir qué se comprobó, y `delivered_do_not_retry` existe para el caso en que la respuesta correcta es *no toques nada*: responde 409 y el bloqueo se queda.

Lo que el código **no** hace, y es tan importante como lo que hace: no consulta al proveedor, no cancela nada y no reintenta. `retry_is_manual: true` en la respuesta lo dice literalmente.

## `transport.request`: cuatro detalles

```python
attempts = 3 if method.upper() in {"GET", "HEAD"} else 1
```

El número de intentos depende solo del método, no de la configuración. Un POST no se reintenta nunca, y por eso su fallo de red se llama `NETWORK_OUTCOME_UNKNOWN` y no `NETWORK_ERROR`: con un solo intento, un error de transporte no permite concluir que la petición no llegó.

```python
if res.status_code >= 300:
    raise IntegrationError(f"UPSTREAM_HTTP_{res.status_code}", res.status_code)
```

Con `follow_redirects=False`, un 302 es un error. Esto es defensa de salida: una redirección es una forma cómoda de llevar la petición —con sus credenciales— a un host que no está en la allowlist, por ejemplo a `169.254.169.254`. Hay una prueba exactamente para ese caso.

```python
async for part in res.aiter_bytes():
    length += len(part)
    if length > settings.max_response_bytes:
        raise IntegrationError("UPSTREAM_RESPONSE_TOO_LARGE")
```

El límite se aplica **durante** la lectura, no después: un `Content-Length` mentiroso o ausente no sirve para agotar la memoria del proceso.

```python
return max(0, min(seconds, 10))
```

`retry_delay` acota el `Retry-After`. Un proveedor que pida esperar una hora no debe poder dejar colgada una petición del gateway; también acepta el formato de fecha HTTP y cae a un retroceso exponencial si el valor no se entiende.

## El pool compartido y su lock

```python
if _client is None or _client.is_closed:
    async with _client_lock:
        if _client is None or _client.is_closed:
            _client = httpx.AsyncClient(...)
```

Doble comprobación: la primera evita tomar el lock en el caso normal; la segunda evita que dos corrutinas creen dos clientes al arrancar. Se comprueba `is_closed` además de `None` porque `close_client()` puede haberse ejecutado en el apagado y el proceso todavía atender una petición en vuelo.

`close_client()` intercambia la referencia por `None` antes de cerrar (`client, _client = _client, None`), de modo que una llamada concurrente no espere sobre un cliente que ya se está cerrando.

## El token bucket y su desalojo

```python
tokens, updated = self.buckets.get(identity, (float(self.burst), now))
tokens = min(self.burst, tokens + (now - updated) * self.rate)
```

Sin temporizadores ni tareas de fondo: el saldo se calcula al consultarlo, a partir del tiempo transcurrido. Un bucket nuevo empieza lleno, así que un cliente que llega por primera vez no sufre el límite.

El diccionario es un riesgo de memoria: cada identidad distinta crea una entrada, y la identidad de un webhook es la dirección del cliente. `_evict()` descarta primero los buckets ya recargados al máximo —son equivalentes a no existir— y solo si no hay ninguno recorta una fracción arbitraria. Es una heurística, no un LRU, y está declarada como tal.

`identity()` guarda un resumen SHA-256 truncado, nunca la clave: un volcado de memoria del limitador no revela credenciales.

## Verificación de webhooks: por qué sobre los bytes

```python
raw = await request.body()
if not verify_signature(cfg["type"], os.getenv(cfg["secret_env"], ""), raw, request.headers):
    raise HTTPException(401, "INVALID_WEBHOOK_SIGNATURE")
payload = json.loads(raw)
```

La firma se calcula sobre `raw`, el cuerpo exacto recibido, y se comprueba **antes** de deserializar. Si se verificara sobre el JSON reserializado, cualquier diferencia de espaciado o de orden rompería la firma; y deserializar antes de verificar significa procesar entrada no autenticada.

De ahí se deriva una consecuencia operativa: un proxy que reescriba el cuerpo invalida la firma. Está documentado en [WEBHOOKS](../WEBHOOKS.md).

En Slack se comprueba además la marca de tiempo con una ventana de 300 segundos, para que una petición capturada no se pueda reproducir indefinidamente. Todas las comparaciones usan `hmac.compare_digest`: un `==` sobre una firma filtra información por el tiempo que tarda en fallar.

La clave de deduplicación se elige por proveedor, y en GitHub hay un detalle: no se usa solo la cabecera `X-GitHub-Delivery`, sino la cabecera **más** el hash del cuerpo firmado. Una cabecera no firmada no debe ser la única identidad de un evento. El comentario del código lo dice.

## WhatsApp agrupa; el inbox separa

```python
for entry in payload.get("entry", []):
    for change in entry.get("changes", []):
        value = change.get("value", {})
        for message in value.get("messages", []): ...
        for status in value.get("statuses", []): ...
```

Un solo envelope de Meta puede traer varios mensajes y varios cambios de estado. Si se guardara como un evento, reconocer uno reconocería todos. Se extraen individualmente, con su clave propia; la de un estado incluye el identificador, el estado y la marca de tiempo, porque el mismo mensaje pasa por `sent`, `delivered` y `read`, y los tres son eventos distintos.

## `mail_content`: el campo que no se inventa

El recorrido del árbol MIME usa una pila explícita en lugar de recursión, lee el charset de cada parte (y no asume UTF-8), prefiere texto plano y solo convierte HTML si no hay alternativa, descartando `script` y `style`. Los adjuntos se **listan** con su identificador: no se descargan.

El detalle más importante está en `evidence_for_ai`:

```python
if "_content" in value:
    return {k: value[k] for k in ["id", "threadId", "snippet", "_content"] if k in value}
```

Y su docstring: *no duplicar cuerpos codificados; no convertir IDs de listados en textos ficticios*. Un listado de Gmail devuelve identificadores, no cuerpos. Si el motor de composición rellenara ese hueco, produciría correos que nadie escribió. Por eso `_content` existe solo cuando hubo MIME real, y `body_available` dice si había cuerpo.

## Expansión diferida de variables

```python
def get_system(self, name):
    cfg = deepcopy(self._systems[name])
    if cfg.get("enabled", True) is False:
        raise SystemDisabled(...)
    return self._expand_env(cfg)
```

El catálogo se guarda sin expandir y se expande por petición, sobre una copia profunda. Tres consecuencias: el proceso arranca sin tener todos los secretos; una variable ausente falla solo en el sistema que la necesita (`SYSTEM_CONFIGURATION_INCOMPLETE`); y `list_public()` nunca puede filtrar un valor expandido, porque trabaja sobre la versión sin expandir. Hay una prueba que comprueba que el catálogo no contiene `WHATSAPP_ACCESS_TOKEN` ni `${`.

La expansión exige que la variable **no esté vacía**: una cadena vacía se trata como ausente, porque una cabecera `Authorization` con el prefijo `Bearer` y nada detrás produciría un error del proveedor mucho más difícil de diagnosticar.

## El `X-Request-Id` que el cliente propone

```python
incoming = request.headers.get("x-request-id", "")
request_id = incoming if SAFE_REQUEST_ID.match(incoming) else str(uuid.uuid4())
```

Reutilizar el identificador del cliente es útil para correlacionar, pero una cabecera que se refleja es una vía de inyección: caracteres de control, longitudes absurdas o contenido que acabe en un registro mal escapado. El patrón acepta de 8 a 64 caracteres de un conjunto reducido; cualquier otra cosa se descarta en silencio y se genera uno propio.

## `EmailMessage` como defensa, no como comodidad

```python
msg[header] = p[param]  # EmailMessage rechaza inyección CR/LF en cabeceras.
```

Construir un correo concatenando cadenas permite que un asunto con `\r\n` añada cabeceras: un `Bcc` que el usuario no pidió. `EmailMessage` de la biblioteca estándar valida eso, así que se usa precisamente por el rechazo. Hay una prueba dedicada.

El límite de adjuntos se acumula **mientras** se decodifica, no al final: así una lista de adjuntos enorme no se materializa completa en memoria antes de rechazarse.

## El escape de SOAP sin parser

Hasta 0.2 se usaba `xml.sax.saxutils.escape`, que solo escapa texto y nunca analiza nada; aun así, Bandit marcaba la importación del módulo `xml.sax` (B406). En 0.3 el escape es una función propia de cinco reemplazos, con un orden que importa: `&` primero, porque si fuera el último convertiría las entidades ya generadas en `&amp;lt;`.

El análisis de la **respuesta** sí usa `defusedxml`, que es donde el riesgo real existe: entidades externas y expansión recursiva.

## La recarga que no puede dejar el catálogo vacío

```python
def reload(self):
    loaded = self._load()
    self._systems = loaded
    return len(loaded)
```

Dos líneas con una propiedad importante: si `_load()` lanza, la asignación no ocurre y el catálogo anterior sigue en uso. La alternativa —vaciar y recargar— dejaría el servicio sin sistemas ante un YAML mal editado. La ruta HTTP convierte esa excepción en `422 INVALID_CATALOG_PREVIOUS_KEPT`, y hay una prueba que lo verifica rompiendo el archivo a propósito.

El endurecimiento de `_load` llegó por un fallo real encontrado al escribir esa prueba: un `systems:` que fuera una lista producía `AttributeError`, no un error de configuración.

## Fuentes de este capítulo

Lectura línea a línea de `orchestrator.py`, `store.py`, `transport.py`, `security.py`, `ratelimit.py`, `webhooks.py`, `registry.py`, `connectors/builders.py`, `connectors/mail_content.py`, `adapters/soap.py` y `main.py`, con las pruebas que fijan cada comportamiento en `tests/`.
