# Runbook de operación

Procedimientos para quien mantiene la instancia en marcha. Todo lo de aquí se ejecuta sin contactar a ningún proveedor, salvo donde se indique.

## Arrancar y parar

```bash
uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --workers 1 --no-access-log
```

Un solo worker. El estado vive en SQLite local y los locks de OAuth están en memoria del proceso: varios workers sobre el mismo archivo comparten las reservas pero no los locks, y el límite de carga pasa a contar por separado en cada uno. Para parar, señal `TERM`; el ciclo de vida cierra el pool HTTP y devuelve las conexiones.

Con Compose:

```bash
docker compose up -d
docker compose logs -f api
docker compose down
```

## Comprobación diaria

```bash
uao health    # el proceso responde
uao doctor    # claves, política y sistemas con entorno completo
uao stats     # recuentos del estado local
```

```json
{
  "version": "0.3.0",
  "allow_writes": false,
  "ai_mode": "off",
  "rate_limit_per_minute": 120,
  "systems": 18,
  "state": {
    "events_pending": 0,
    "events_acked": 0,
    "requests_complete": 0,
    "requests_pending_reconciliation": 0,
    "tokens_stored": 0
  }
}
```

Qué vigilar:

| Señal | Qué significa | Qué hacer |
|---|---|---|
| `requests_pending_reconciliation` crece | Escrituras con resultado desconocido acumuladas. | [Reconciliar](RECONCILIATION.md). No reintente a ciegas. |
| `events_pending` crece y nadie consume | El inbox se llena porque ningún proceso lee ni reconoce. | Revise el consumidor; el inbox no se autolimpia sin `ack`. |
| `allow_writes: true` sin necesidad | La instancia puede enviar. | Déjelo en `false` si solo consulta. |
| `ai_mode` distinto de `off` sin decisión | Hay datos saliendo hacia un modelo. | Revise `AI_ALLOW_SENSITIVE_DATA`. |
| `tokens_stored` en 0 pero espera consultar | No hay consentimiento guardado. | `uao auth-google` o `uao auth-microsoft`. |

## Cambiar el catálogo sin reiniciar

```bash
uao enable gmail
uao reload
```

`reload` requiere la clave de aprobación y es atómico desde el punto de vista del servicio: si el YAML queda inválido responde `422 INVALID_CATALOG_PREVIOUS_KEPT` y el catálogo anterior sigue en uso. Compruebe el resultado con `uao catalog` o `GET /v1/systems/<sistema>`.

Un cambio de **variables de entorno** no se recarga: `.env` se lee al iniciar el proceso. Para eso sí hace falta reiniciar.

## Límite de carga

Predeterminado: 120 peticiones por minuto con ráfaga de 30, por identidad de llamada. La identidad es el resumen SHA-256 de la `X-API-Key` o, si no hay clave, de la dirección del cliente (caso de los webhooks). Al superarlo: `429` con `Retry-After` y `X-RateLimit-Remaining: 0`.

```dotenv
RATE_LIMIT_PER_MINUTE=120   # 0 desactiva el control
RATE_LIMIT_BURST=30
```

`/health` queda fuera para no romper la sonda del contenedor. El contador vive en memoria: reiniciar el proceso lo reinicia, y cada réplica cuenta por su cuenta. Si necesita un límite compartido o protección frente a abuso real, póngalo en el proxy inverso.

Si un cliente legítimo recibe 429 de forma sostenida, suba el límite o reparta el tráfico en claves distintas; no es un error que convenga silenciar poniendo 0.

## Purgar el estado

```bash
uao prune-events --days 30     # solo eventos ya reconocidos
uao prune-requests --days 90   # solo reservas completadas
```

Ninguno de los dos borra lo que importa: eventos sin reconocer y reservas pendientes sobreviven siempre. Para respaldar, detenga el proceso y copie `data/` **junto con** la `STATE_KEY`: el archivo sin la clave es ilegible, y la clave sin el archivo no sirve de nada. Guárdelos en sitios distintos.

Nunca rote `STATE_KEY` con una base existente. Si la pierde, pierde los tokens guardados (habrá que repetir el consentimiento) y las reservas de idempotencia (habrá que reconciliar a mano lo que estuviera en duda).

## Correlacionar un problema

Toda respuesta trae `X-Request-Id`; si envía el suyo con formato seguro (8 a 64 caracteres de letras, dígitos, `.`, `_`, `:` o `-`), se reutiliza. Las operaciones traen además `meta.trace_id`. Los registros del gateway (`uao.audit`) anotan `trace`, `system`, `operation` y el código de error, nunca el contenido ni las credenciales.

Para investigar un envío concreto: tome el `trace_id`, busque la hora, y cruce con el registro del proveedor. El gateway no guarda el cuerpo de los mensajes.

## Incidentes frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| Todo `/v1` responde 503 `GATEWAY_KEY_NOT_CONFIGURED` | Falta `GATEWAY_API_KEY` o tiene menos de 24 caracteres. | `python scripts/bootstrap.py` y reiniciar. |
| 401 `INVALID_API_KEY` | La clave del cliente no coincide con la del servidor. | Compare con `.env`; no la pegue en registros. |
| 403 `WRITE_APPROVAL_REQUIRED` | Falta alguna de las cuatro condiciones. | Revise `ALLOW_WRITES`, cabecera, `confirmed` y clave de idempotencia. |
| 409 `OUTCOME_PENDING_OR_UNKNOWN_RECONCILE` | Hay una reserva en duda con esa clave. | [Reconciliar](RECONCILIATION.md). |
| 409 `IDEMPOTENCY_CONFLICT` | Reutilizó una clave con contenido distinto. | Use una clave nueva para una acción lógica nueva. |
| 503 `SYSTEM_CONFIGURATION_INCOMPLETE` | El catálogo pide una variable que no existe. | `uao doctor` indica qué sistema está incompleto. |
| 409 `SYSTEM_DISABLED` | El sistema está apagado. | `uao enable <sistema> && uao reload`. |
| 413 `REQUEST_TOO_LARGE` | Supera `MAX_REQUEST_BYTES` (2 MB). | Reduzca adjuntos; el límite de carga decodificada es de 512 kB. |
| `UPSTREAM_RESPONSE_TOO_LARGE` | La respuesta del proveedor supera 4 MB. | Use `response_map` o pagine. |
| `HOST_NOT_ALLOWED` / `TLS_REQUIRED` / `PRIVATE_NETWORK_BLOCKED` | Defensa de salida actuando. | Corrija el catálogo; no desactive el bloqueo para producción. |

El catálogo completo de códigos está en [TROUBLESHOOTING](TROUBLESHOOTING.md).

## Rotar claves

| Clave | Cómo | Efecto |
|---|---|---|
| `GATEWAY_API_KEY` | Genere una nueva, actualice los clientes, reinicie. | Los clientes con la clave vieja reciben 401. |
| `APPROVAL_API_KEY` | Igual. | Las escrituras y la reconciliación quedan bloqueadas hasta actualizar. |
| `STATE_KEY` | **No se rota** con estado existente. Requiere consentimiento nuevo y reconciliación previa. | Perder esta clave inutiliza el estado cifrado. |
| Tokens de proveedor | En el panel del proveedor, y vuelva a ejecutar el comando de consentimiento. | Revocar en el proveedor no borra la copia local: borre también el estado o repita `auth-*`. |

## Actualizar la versión

```bash
git pull
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py      # conserva claves
python -m pytest -q
python scripts/verify_repository.py
```

Lea el [CHANGELOG](../CHANGELOG.md) antes. Las migraciones están documentadas una por una; de 0.2 a 0.3 los cambios son aditivos y no requieren tocar los clientes.

## Qué este runbook no cubre

TLS y certificados, proxy inverso, alta disponibilidad, respaldo automatizado, rotación programada de secretos, métricas en formato de scraping y alertas. Son responsabilidad de su infraestructura y están listados como pendientes en el [ROADMAP](../ROADMAP.md) y en el checklist de [SECURITY](SECURITY.md).
