# Validación de v0.3.0

Fecha de ejecución: **12 de noviembre de 2026**. Entorno: **Windows 11 (10.0.26300)**, Python **3.12.9**. Las versiones exactas de cada dependencia están en [environment.json](validation-results/environment.json).

Este documento registra **lo que se ejecutó realmente** en esta entrega, con su resultado, y enumera de forma explícita lo que no se ejecutó. No es una certificación de seguridad ni una prueba de integración con cuentas reales.

## Resultado observado

**162 pruebas pasaron**, sin fallos, con transporte y credenciales simulados. Cobertura de líneas del paquete: **76,4 %**. No es una medición de cobertura de las APIs del proveedor.

| Comprobación | Herramienta | Resultado |
|---|---|---|
| Pruebas unitarias y de contrato | `pytest` 9.2.0 | 162 pasaron, 0 fallos |
| Cobertura de líneas | `pytest-cov` 7.1.0 | 76,4 % (1277 líneas, 302 sin ejecutar) |
| Lint | `ruff` 0.17.5 sobre `src tests tools scripts` | Sin hallazgos |
| Análisis estático de seguridad | `bandit` 1.9.4 sobre `src` | Sin hallazgos |
| Vulnerabilidades de dependencias | `pip-audit` 2.10.1 | Sin vulnerabilidades conocidas |
| Coherencia del repositorio | `scripts/verify_repository.py` | `ok: true`; 13 proveedores, 69 operaciones, 18 ejemplos |
| Servicio HTTP en ejecución | uvicorn real en loopback | Ver abajo |

Se verificaron los constructores de las 69 operaciones, los esquemas de los 18 ejemplos JSON, MIME de entrada y salida, Unicode y adjuntos, refresco OAuth simulado, cifrado del estado, idempotencia y conflictos, reconciliación y liberación de reservas, firmas de webhook, control de carga, identidad de petición, errores de catálogo, recarga en caliente, los controles de aprobación, el rechazo de escrituras desde `ask`, el transporte y sus límites. Se probaron además bootstrap, el importador y la síntesis con un modelo simulado.

## Comprobación del servicio en ejecución

El servidor Uvicorn se inició **como proceso real en loopback**, con claves efímeras y una base de datos temporal, y **sin contactar a ningún proveedor externo**. Evidencia completa en [runtime-smoke.json](validation-results/runtime-smoke.json).

| Comprobación | Resultado |
|---|---|
| `GET /health` | 200, versión `0.3.0` |
| Cabeceras de respuesta | `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Request-Id` presente |
| Identificador del cliente | Un `X-Request-Id` con formato seguro se devuelve tal cual |
| Catálogo sin clave | 401 |
| Catálogo autorizado | 19 sistemas (los 18 del repositorio más uno de prueba) y **sin** variables ni secretos en la respuesta |
| Ficha de sistema | 200 para `gmail`, 404 para un nombre inexistente |
| Sistema deshabilitado | `SYSTEM_DISABLED`, sin llamada externa |
| Sistema inexistente | `SYSTEM_NOT_FOUND` |
| Operación inexistente | `OPERATION_NOT_FOUND` |
| Escritura con aprobación pero `ALLOW_WRITES=false` | `WRITE_APPROVAL_REQUIRED` |
| Escritura desde `/v1/ask` con clave de aprobación | `ASK_IS_READ_ONLY` |
| `/v1/reconciliation/{id}/release` sin aprobación | 403 |
| `/v1/admin/reload` sin aprobación | 403; con aprobación, recarga los 19 sistemas |
| Webhook sin firma a un sistema deshabilitado | 404 `WEBHOOK_NOT_CONFIGURED` |
| Límite de carga con ráfaga de 2 | Devuelve 429 cuando se agota, y `/health` sigue respondiendo 200 |
| OpenAPI | 13 rutas publicadas, incluida `/v1/ask` |

El sistema `demo_write` de esa comprobación existe solo en el catálogo temporal del smoke test: es la única forma de probar la política de escritura sin habilitar un proveedor real.

## Qué NO se ejecutó

No se conectaron Gmail, WhatsApp, Outlook, Teams, Slack, Discord, Telegram, Twilio, SendGrid, Resend, Calendar, Drive ni GitHub con cuentas reales. **No se enviaron mensajes, correos ni eventos externos**, y ninguna comprobación de esta entrega contactó a un proveedor: el smoke test se diseñó para no salir de loopback.

No se probó el consentimiento OAuth interactivo real. `google-auth-oauthlib` y `msal` están instalados, pero los flujos de navegador y de device code no se ejecutaron: el refresco de tokens se probó con respuestas simuladas.

No se ejecutaron Docker, Linux, macOS, WSL, Dev Containers ni despliegues en nube **en esta sesión**. Hay configuraciones y guías para esos entornos, y la CI está definida para tres sistemas operativos y Python 3.11, 3.12 y 3.13, incluido un job que construye la imagen y comprueba `/health` dentro del contenedor. Su resultado debe leerse en la pestaña Actions del repositorio, no en este documento.

El adaptador gRPC no se ejercitó contra un servicio real: requiere el extra `grpc` y stubs generados. Quedan sin ejecución real los flujos de OAuth interactivo, MSAL y parte de los caminos de protocolo y de escalado, lo que explica el 23,6 % de líneas no cubiertas.

Las pruebas no reemplazan pruebas de contrato en las cuentas habilitadas ni una revisión de seguridad independiente.

## Evidencia incluida

[Salida de pytest](validation-results/test-output.txt) · [JUnit XML](validation-results/test-results.xml) · [Cobertura JSON](validation-results/coverage.json) · [Versiones del entorno](validation-results/environment.json) · [Smoke test HTTP](validation-results/runtime-smoke.json).

Estos reportes no contienen credenciales: las claves del smoke test se generaron en memoria para esa ejecución y se descartaron con el proceso. Las dependencias descritas corresponden a este entorno, no a un lock para producción.

## Repetir en su equipo

```bash
python -m pip install -e ".[auth,dev]"
python -m pytest -q --cov=universal_api_orchestrator
python -m ruff check src tests tools scripts
python scripts/verify_repository.py
python scripts/demo_offline.py
```

El script offline ejecuta una selección de integración simulada; no inicia sesión en ningún servicio. La matriz de CI repite la suite, el lint y el verificador en los entornos configurados, y tiene jobs separados para el paquete y para el contenedor.

## Aceptación real por proveedor

Complete esta ficha en un archivo privado, nunca con secretos:

| Campo | Registrar por el operador |
|---|---|
| Servicio y entorno | Aplicación/cuenta de prueba y versión del contrato. |
| Identidad autorizada | Usuario o recurso, sin token. |
| Permisos | Scopes, roles y aprobaciones concedidas. |
| Consulta real | Operación, fecha y resultado verificado. |
| Escritura consentida | Destinatario autorizado, clave de correlación y resultado. |
| Entrega | Estado del proveedor; distinguir aceptación de entrega. |
| Repetición idempotente | Comprobar ausencia de duplicado en el caso probado. |
| Reserva en duda | Ensayar un corte de red y completar el procedimiento de [reconciliación](RECONCILIATION.md). |
| Evento entrante | Firma, deduplicación, procesamiento y reconocimiento. |
| Recuperación | Ensayo de token revocado, timeout, cuota y respaldo. |
| Aprobación final | Responsable, restricciones pendientes y fecha. |

No habilite un canal de producción basándose solo en una celda completada con datos simulados.
