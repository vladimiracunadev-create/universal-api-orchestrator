# 13 · Despliegue y operación

Los procedimientos del día a día están en el [RUNBOOK](../RUNBOOK.md). Este capítulo explica las **topologías** posibles, qué garantiza cada una y qué hay que añadir.

## Topologías

### 1. Proceso local, un desarrollador

```text
aplicación ──> uvicorn 127.0.0.1:8080 ──> proveedores
                     └── data/state.sqlite3
```

Lo que trae el repositorio. Sirve para desarrollar, probar y para una automatización personal. No recibe webhooks: un proveedor externo no puede conectarse a su loopback.

### 2. Contenedor en un servidor propio

```text
internet ──> proxy inverso con TLS ──> contenedor 8080 ──> proveedores
                                            └── volumen data/
```

La topología mínima para algo real. El proxy aporta lo que el servicio no hace: TLS, nombre público, límite de carga compartido y restricción de rutas. `docker-compose.yml` publica el puerto **solo en loopback** a propósito: el proxy es el único que debe alcanzarlo.

Qué hay que añadir: certificado y renovación; reglas que expongan `/v1/webhooks/*` al proveedor pero no `/v1/admin/*` ni `/docs` a internet; respaldo del volumen con su `STATE_KEY` aparte; y monitoreo del recuento de reservas pendientes.

### 3. Varias réplicas

**No es una topología soportada.** Si la monta de todos modos, sepa exactamente qué se rompe:

| Elemento | Qué pasa con dos réplicas |
|---|---|
| Reservas de idempotencia | Se comparten **solo** si ambas montan el mismo archivo SQLite. En volúmenes distintos, cada una puede enviar el mismo mensaje. |
| Locks de refresco OAuth | Están en memoria. Dos réplicas pueden refrescar el mismo token a la vez; el último en escribir gana. |
| Límite de carga | Cada réplica cuenta por separado: el límite efectivo se multiplica por el número de réplicas. |
| Caché de tokens | Independiente por proceso. Más llamadas al endpoint de token, no incorrectas. |
| Inbox | Se comparte si se comparte el archivo. SQLite con WAL sobre un volumen de red es una mala idea. |

La solución correcta no es más procesos: es un almacén transaccional compartido, descrito en el [capítulo 15](15-risks-and-technical-debt.md) y en el [ROADMAP](../../ROADMAP.md).

## Webhooks

Para recibir eventos hace falta una URL HTTPS pública que llegue a `/v1/webhooks/{sistema}`. Tres requisitos de los que depende la verificación de firma:

1. **El cuerpo debe llegar intacto.** La firma se calcula sobre los bytes exactos; un proxy que reserialice el JSON la invalida.
2. **El secreto del proveedor debe estar en el entorno del proceso**, con el nombre que declare el catálogo.
3. **El sistema debe estar habilitado.** Un webhook a un sistema apagado responde `404 WEBHOOK_NOT_CONFIGURED`.

El límite de carga se aplica también a los webhooks, y como no traen clave, la identidad es la dirección de origen. Con un volumen alto desde una sola IP de proveedor, ajuste `RATE_LIMIT_PER_MINUTE` o excluya esa ruta en el proxy.

## Puesta en marcha

```bash
git clone <repositorio> && cd universal-api-orchestrator
python -m pip install -e ".[auth]"
python scripts/bootstrap.py
python -m pytest -q                 # con el extra dev
uao doctor
```

Luego, en este orden: arrancar con `ALLOW_WRITES=false`, habilitar **un** proveedor con permisos de solo lectura, ejecutar una consulta pequeña y revisar `ok`, `data`, `error` y `meta`. Solo después, si hace falta enviar, habilitar escrituras y ensayar el procedimiento de reconciliación **antes** de necesitarlo.

Habilitar escrituras en una instancia que solo consulta es el error más común y el más caro.

## Mantenimiento periódico

| Cuándo | Qué | Comando |
|---|---|---|
| Cada día | Estado del proceso y recuentos | `uao health`, `uao stats` |
| Cada día | Reservas pendientes de reconciliación | `uao pending` |
| Cada semana | Purga del inbox reconocido | `uao prune-events --days 30` |
| Cada mes | Purga de reservas completadas | `uao prune-requests --days 90` |
| Cada mes | Respaldo con prueba de restauración | copiar `data/` con el proceso detenido |
| Al actualizar | Suite, lint y verificador | ver [RUNBOOK](../RUNBOOK.md) |
| Cuando cambie el catálogo | Recarga | `uao enable X && uao reload` |

Nada de esto ocurre solo. No hay tarea programada, no hay purga automática y no hay reintento de nada.

## Respaldo y restauración

Qué respaldar: `data/` (el estado cifrado) y, **en un lugar distinto**, la `STATE_KEY`. El archivo sin la clave es ilegible; la clave sin el archivo no sirve.

Cómo: detenga el proceso y copie el directorio. En caliente, incluya los archivos `-wal` y `-shm` que crea WAL, o la copia puede quedar inconsistente.

Restauración: coloque el archivo, restaure la **misma** `STATE_KEY`, arranque y compruebe con `uao stats` que los recuentos son los esperados. Si `uao pending` muestra `decode_warning: UNREADABLE_WITH_CURRENT_STATE_KEY`, la clave no es la correcta: pare y busque la original antes de tocar nada.

Un respaldo que nunca se restauró no es un respaldo. Ensáyelo.

## Qué pasa en un apagado

`SIGTERM` hace que el ciclo de vida cierre el pool HTTP y devuelva las conexiones. Lo que **no** ocurre: no se reintenta nada pendiente, no se vacía el estado y no se avisa a ningún proveedor.

Si el proceso muere **durante** una escritura, la reserva queda `pending` y al arrancar aparecerá en `uao pending`. Eso es correcto: el gateway no sabe si el mensaje salió, y alguien tiene que comprobarlo.

## Actualizar sin perder estado

```bash
git pull
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py      # conserva las claves
python -m pytest -q
python scripts/verify_repository.py
```

Reglas: lea el [CHANGELOG](../../CHANGELOG.md) y la guía de migración antes; **no** borre `data/`; **no** rote `STATE_KEY`; y reconcilie lo pendiente antes de una actualización que cambie el comportamiento de escritura. De 0.2 a 0.3 los cambios son aditivos y el esquema de SQLite es compatible: los índices nuevos se crean al abrir.

## Rotación de claves

| Clave | Procedimiento | Consecuencia |
|---|---|---|
| `GATEWAY_API_KEY` | Nueva en `.env`, actualizar clientes, reiniciar | Los clientes viejos reciben 401 |
| `APPROVAL_API_KEY` | Ídem | Escrituras y reconciliación bloqueadas hasta actualizar |
| `STATE_KEY` | **No se rota** con estado existente | Perderla inutiliza tokens y reservas |
| Token de proveedor | Revocar en el proveedor y repetir `uao auth-*` | Revocar remotamente no borra la copia local |

## Observabilidad disponible

Lo que hay: `GET /health` para la sonda; `GET /v1/stats` con política y cinco recuentos; `X-Request-Id` en toda respuesta; `meta.trace_id` por operación; y el registro `uao.audit` con una línea por operación (trace, sistema, operación, código) **sin** contenido ni credenciales.

Lo que no hay: métricas en formato de scraping, trazas distribuidas, registro estructurado en JSON y alertas. Si su plataforma las exige, están en el [ROADMAP](../../ROADMAP.md) y hay que construirlas.

Qué vigilar, en orden de importancia: `requests_pending_reconciliation` creciendo (escrituras en duda sin atender), `events_pending` creciendo sin consumidor, y `429` sostenidos en un cliente legítimo.

## Qué no está resuelto

TLS de entrada, alta disponibilidad, respaldo automatizado, rotación programada de secretos, gestión de secretos integrada, autoescalado y despliegue sin interrupción. Son responsabilidad de su infraestructura y están declarados como tales, no implementados en silencio a medias.

## Fuentes de este capítulo

`Dockerfile`, `docker-compose.yml`, `.devcontainer/devcontainer.json`, `scripts/start.sh`, `scripts/start.ps1`, `src/universal_api_orchestrator/main.py` (`lifespan`), `store.py`, `cli.py`, `docs/ENVIRONMENTS.md`, `docs/RUNBOOK.md`, `.github/workflows/ci.yml`.
