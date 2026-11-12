# Historial de cambios

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es [SemVer](https://semver.org/lang/es/).

## 0.3.0 — 2026-11-12

Versión de operación y robustez. No añade proveedores: siguen siendo 13 servicios y 69 operaciones. Todos los cambios del contrato HTTP son **aditivos**; las rutas de v0.2 responden igual. Consulte [migración](docs/MIGRATION_0_2_TO_0_3.md).

### Añadido

- Reconciliación explícita de escrituras en duda: `GET /v1/reconciliation` muestra qué reserva quedó pendiente y `POST /v1/reconciliation/{id}/release` la libera solo con clave de aprobación, `confirmed:true` y un resultado comprobado. `delivered_do_not_retry` conserva la reserva a propósito. Procedimiento en [RECONCILIATION](docs/RECONCILIATION.md).
- Control de carga local por clave de llamada (token bucket en memoria): responde `429` con `Retry-After` y `X-RateLimit-Remaining`. `RATE_LIMIT_PER_MINUTE=0` lo desactiva. `/health` queda fuera para no romper sondas de contenedor.
- `X-Request-Id` en todas las respuestas, reutilizando el del cliente cuando tiene formato seguro, más `Referrer-Policy: no-referrer`.
- `GET /v1/systems/{system}` con la ficha de un sistema y `GET /v1/stats` con recuentos del estado local y la política vigente.
- `POST /v1/admin/reload` y `uao reload` releen el catálogo sin reiniciar el proceso; un catálogo inválido deja el anterior en uso.
- `timeout_seconds` por operación en el catálogo, acotado entre 0,5 y 120 segundos en todos los adaptadores.
- Comandos de CLI: `health`, `stats`, `pending`, `release`, `reload` y `prune-requests`.
- Pruebas nuevas de reconciliación, límite de carga, identidad de petición, errores de catálogo y recarga: de 147 a 162.
- Documentación: [CLI](docs/CLI.md), [RECONCILIATION](docs/RECONCILIATION.md), [RUNBOOK](docs/RUNBOOK.md), [GLOSSARY](docs/GLOSSARY.md), [índice de docs](docs/README.md), [documentación de sistema](docs/system-documentation/README.md), [INSTALL](INSTALL.md), [STATUS](STATUS.md), [SECURITY](SECURITY.md), [SUPPORT](SUPPORT.md), [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) y [AGENTS](AGENTS.md).
- Plantillas de incidencia y pull request, `CODEOWNERS`, Dependabot y workflow de seguridad (gitleaks, Bandit, pip-audit, CodeQL) con acciones fijadas a SHA.

### Cambiado

- El cliente HTTP se comparte en todo el proceso con pool de conexiones configurable y se cierra en el apagado: se elimina un handshake TLS por operación. Antes se creaba un `AsyncClient` por petición.
- Errores de catálogo precisos en lugar de un único código genérico: `SYSTEM_NOT_FOUND` (404), `SYSTEM_DISABLED` (409), `OPERATION_NOT_FOUND` (404) y `SYSTEM_CONFIGURATION_INCOMPLETE` (503).
- Una escritura fallida tras reservar devuelve `meta.reservation_id` para poder reconciliarla sin adivinar.
- SQLite usa WAL, `synchronous=NORMAL`, `busy_timeout` de 15 s e índices en el inbox y en las reservas: leer eventos ya no espera a una escritura en curso.
- `reserve()` guarda cifrado el sistema y la operación intentados, de modo que una reserva pendiente sea inspeccionable.
- `/v1/systems` y la ficha de sistema declaran `sensitive`.
- `cryptography` pasa a `>=50,<51`: las versiones admitidas antes arrastraban avisos publicados (PYSEC-2026-3552/3553/3554).
- El SOAP escapa valores con una función propia; se retira la importación de `xml.sax.saxutils`, señalada por Bandit.
- `pyproject.toml` declara la licencia como expresión SPDX con `license-files`, URLs del proyecto, clasificadores y un conjunto mayor de reglas de lint (`W`, `I`, `UP`, `B`, `C4`, `RUF`).
- `verify_repository.py` comprueba además coherencia de versión y recuentos entre manifiestos, catálogo y README, codificación de los Markdown, y que ningún archivo enlazado desde la documentación quede excluido por `.gitignore`: un enlace puede existir en el equipo y no en el repositorio publicado.
- `uao doctor` informa versión, modo de IA, límite de carga y si se permiten redes privadas.

### Corregido

- Un catálogo YAML malformado (`systems` como lista, o un sistema que no es un mapa) producía `AttributeError`; ahora falla con un error de configuración legible y, al recargar, conserva el catálogo anterior.
- La versión del servicio estaba escrita a mano en dos puntos de `main.py`; ahora proviene de `__version__`.
- `prune` solo expiraba eventos reconocidos y las reservas completadas crecían sin límite; `prune-requests` las expira sin tocar las pendientes.

### Sin cambios deliberados

Las cuatro condiciones para escribir, la ausencia de reintento automático de escrituras, el bloqueo de redes privadas, la verificación de firma de webhooks antes de deserializar, el modo de IA apagado y el arranque sin llamadas externas.

## 0.2.0 — 2026-09-20

Ampliación multicanal con 13 servicios/69 operaciones y manuales en español. Se añadieron configuración diferida, JSON Schema, MIME Gmail bidireccional, builders de mensajería, OAuth Google y MSAL, refresh, cifrado de valores, inbox, firmas webhook, idempotencia, aprobación separada y controles de red/transporte.

Se mantuvieron los protocolos originales y las rutas principales. Se cambiaron intencionalmente autenticación obligatoria, política de escrituras, seguridad de webhooks, comportamiento gRPC y permisos de IA. Consulte [migración](docs/MIGRATION_0_1_TO_0_2.md).

Se incorporaron CLI, ejemplos de varios lenguajes, Postman, flujo Gmail de consulta, scripts de arranque/validación/release, Compose, Dev Container y matriz CI. La validación real efectuada se registra en [VALIDATION](docs/VALIDATION.md), separada de configuraciones no ejecutadas.

## 0.1.0 — base recibida

Adaptadores de protocolos genéricos, catálogo inicial, ejecución/batch/composición, normalización JMESPath, importador inicial OpenAPI y pruebas básicas. Historial documental conservado en `docs/history/`.
