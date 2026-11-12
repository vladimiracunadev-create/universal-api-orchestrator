# Universal API Orchestrator · v0.3.0

**Un backend para conectar correo, mensajería, colaboración y sistemas de negocio; consultar sus datos y preparar respuestas con fuentes.**

[![CI](https://github.com/vladimiracunadev-create/universal-api-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/vladimiracunadev-create/universal-api-orchestrator/actions/workflows/ci.yml)
[![Security](https://github.com/vladimiracunadev-create/universal-api-orchestrator/actions/workflows/security.yml/badge.svg)](https://github.com/vladimiracunadev-create/universal-api-orchestrator/actions/workflows/security.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Python · FastAPI · REST · GraphQL · JSON-RPC · SOAP · gRPC opcional · OAuth · Webhooks · MIT

Reúne **13 servicios y 69 operaciones de proveedor**, además de los adaptadores de protocolo genéricos. No son enlaces de referencia vacíos: existen constructores HTTP, validación de parámetros, autorización, políticas de envío, persistencia cifrada y pruebas. Cada servicio empieza deshabilitado y requiere una cuenta autorizada.

> **Estado verificable:** 162 pruebas automatizadas con transporte simulado; no se han utilizado cuentas reales ni enviado mensajes. Consulte [VALIDATION](docs/VALIDATION.md) para los resultados y límites de la ejecución, y [STATUS](STATUS.md) para la foto del repositorio. Docker, Windows y macOS tienen configuraciones y guías, no una certificación de despliegue realizada en esos equipos.

## Qué puede conectar

| Servicio | Operaciones | Cobertura implementada |
|---|---:|---|
| Gmail / Google Workspace | 15 | Buscar y leer mensajes/hilos, MIME y adjuntos, enviar, responder, borradores, etiquetas, historial y watch. |
| WhatsApp Cloud API | 9 | Texto, plantillas, multimedia, interacción, recibo de lectura, subida de medios, metadatos y perfil. |
| Outlook / Microsoft Graph | 9 | Correo, carpetas, adjuntos, borradores y respuestas con OAuth delegado. |
| Telegram Bot API | 7 | Bot, mensajes, fotos, actualizaciones y registro de webhook. |
| Slack | 6 | Canales, historial, hilos, envío y edición; verificación de Events API. |
| Discord | 4 | Bot, historial de canal, envío y edición por REST. |
| Twilio | 3 | Crear, consultar y listar mensajes. SMS y direcciones WhatsApp según la cuenta. |
| SendGrid | 1 | Envío de correo transaccional. |
| Resend | 2 | Envío de correo y consulta por identificador. |
| Google Calendar | 3 | Consultar y crear eventos. |
| Google Drive | 3 | Listar archivos, metadatos y exportación de documentos a texto. |
| Microsoft Teams | 4 | Equipos, canales, mensajes y publicación con identidad delegada. |
| GitHub | 3 | Repositorios, issues y creación de issues; webhook firmado. |

La [matriz completa](docs/CONNECTOR_MATRIX.md) enumera cada operación, parámetros requeridos y si lee o modifica datos. **La cobertura es esta matriz, no la totalidad de endpoints de cada plataforma.** SMTP/IMAP, pagos, CRM específicos, bases de datos, Kafka y otros transportes no están implementados como conectores especializados en esta versión.

## Empezar en macOS o Linux

Con Python 3.11 o superior, desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py
uao doctor
uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

En otra terminal, active el mismo entorno y abra `http://127.0.0.1:8080/docs`. No es necesario configurar todos los proveedores para iniciar. No se hace ninguna llamada externa durante el arranque.

## Empezar en Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[auth,dev]"
.\.venv\Scripts\python.exe scripts\bootstrap.py
.\.venv\Scripts\uao.exe doctor
.\.venv\Scripts\python.exe -m uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

Estos comandos no requieren cambiar la política de ejecución de PowerShell. También existen [scripts de arranque](scripts/start.ps1), [Compose](docker-compose.yml) y [Dev Container](.devcontainer/devcontainer.json). La guía completa de instalación está en [INSTALL](INSTALL.md); los detalles de permisos de volúmenes y OAuth, en [ENTORNOS](docs/ENVIRONMENTS.md).

## Activar Gmail y realizar una consulta real

Primero registre una aplicación OAuth de escritorio en su proyecto Google, habilite Gmail API y guarde el archivo de cliente en `secrets/google-client.json`. No es la contraseña de su correo. Luego:

```bash
uao auth-google --client secrets/google-client.json --token-key google --scopes https://www.googleapis.com/auth/gmail.readonly
uao enable gmail
uao reload
```

`uao reload` relee el catálogo sin reiniciar el proceso. En otra terminal:

```bash
uao execute examples/requests/gmail-search.json
python examples/workflows/gmail_brief.py --query "is:unread" --limit 3
```

El segundo ejemplo busca IDs y después obtiene los mensajes completos. `_content` contiene texto MIME decodificado; no se inventan cuerpos a partir de IDs. El modo predeterminado compone datos de forma determinista: **no es un resumen inteligente ni un chatbot autónomo**. La síntesis con modelo es opcional, está apagada y exige autorización explícita para datos sensibles.

Guías: [Gmail](docs/providers/GMAIL.md) · [WhatsApp](docs/providers/WHATSAPP.md) · [Microsoft](docs/providers/MICROSOFT.md) · [otras mensajerías](docs/providers/MESSAGING.md) · [Workspace y GitHub](docs/providers/WORKSPACE_AND_GITHUB.md).

## Una interfaz para todos los proveedores

```json
{
  "system": "gmail",
  "operation": "list_messages",
  "params": {"q": "is:unread", "maxResults": 5}
}
```

Ese contrato se envía a `POST /v1/execute` con `X-API-Key`. Cambiar de sistema no cambia la estructura general: cada operación sí tiene sus propios parámetros y permisos. `POST /v1/batch` ejecuta hasta 20 consultas/acciones independientes, y `POST /v1/ask` agrega consultas **solo de lectura**.

| Endpoint | Uso |
|---|---|
| `GET /health` | Estado del proceso, no verifica credenciales externas. |
| `GET /v1/systems` | Catálogo sin credenciales y esquemas de entrada. |
| `GET /v1/systems/{system}` | Ficha de un sistema: operaciones, efecto y esquema. |
| `POST /v1/execute` | Una operación. |
| `POST /v1/batch` | Operaciones independientes, con política por cada una. |
| `POST /v1/ask` | Componer una respuesta con fuentes y errores; nunca enviar. |
| `GET /v1/events` | Bandeja de eventos recibidos y pendientes de reconocimiento. |
| `POST /v1/events/{id}/ack` | Reconocer procesamiento local, no responder al proveedor. |
| `GET /v1/reconciliation` | Escrituras cuyo resultado real se desconoce. |
| `POST /v1/reconciliation/{id}/release` | Liberar una reserva tras comprobarla a mano. |
| `GET /v1/stats` | Recuentos del estado local y política vigente. |
| `POST /v1/admin/reload` | Releer el catálogo sin reiniciar; requiere aprobación. |
| `GET/POST /v1/webhooks/{system}` | Verificación y recepción según proveedor. |

Cada respuesta lleva `X-Request-Id` —propio o el que usted envíe— para correlacionar sus registros con los del gateway. El contrato completo está en [API_GUIDE](docs/API_GUIDE.md) y los comandos en [CLI](docs/CLI.md).

## Consultar no equivale a enviar

Una escritura necesita cuatro condiciones simultáneas: `ALLOW_WRITES=true`, una clave de aprobación válida, `confirmed=true` y una `idempotency_key` no conflictiva. Además necesita la clave normal del gateway y permisos del proveedor.

Los JSON de ejemplo de escritura llevan `confirmed=false`. Cambiar una variable o importar Postman no manda mensajes automáticamente. Revise destinatario y contenido, complete el consentimiento que corresponda y después apruebe la operación conscientemente. [Política de escritura e idempotencia](docs/API_GUIDE.md).

Las respuestas aceptadas por el proveedor **no se presentan como entregadas al destinatario**. WhatsApp dispone de eventos de estado; otros canales requieren sus mecanismos correspondientes. Un fallo ambiguo en una escritura bloquea el reintento local hasta reconciliarlo, para reducir duplicados: el procedimiento está en [RECONCILIATION](docs/RECONCILIATION.md) y ningún reintento ocurre por su cuenta.

## Entornos y situaciones de trabajo

Está preparado para ejecutar el servicio como backend local, contenedor o proceso en un servidor con estado persistente. Incluye clientes [Python](examples/clients/python_client.py), [Node.js](examples/clients/node_client.mjs), [PHP](examples/clients/php_client.php), [PowerShell](examples/clients/powershell_client.ps1), cURL y [Postman](examples/postman/collection.json).

Los [escenarios](docs/WORK_SCENARIOS.md) describen atención al cliente, oficina, comercio, educación y desarrollo, separando los pasos ejecutables de las integraciones de negocio todavía necesarias. Un navegador o móvil debe comunicarse con su backend; nunca recibir los tokens de Gmail, Meta ni la clave de aprobación.

La operación diaria —arranque, purga del estado, límites de carga y qué hacer ante un incidente— está en el [RUNBOOK](docs/RUNBOOK.md).

## Estructura y documentación

```text
config/                 Catálogo declarativo y esquemas de parámetros
src/.../adapters/       Transportes REST, GraphQL, JSON-RPC, SOAP, gRPC
src/.../connectors/     Constructores específicos y decodificación MIME
src/.../auth.py         Tokens, refresh OAuth y caché MSAL
src/.../ratelimit.py    Control de carga local por clave de llamada
src/.../store.py        SQLite con valores sensibles cifrados
src/.../webhooks.py     Verificación y bandeja persistente de eventos
examples/               JSON, clientes, Postman y flujo Gmail de lectura
scripts/                Arranque, validación y empaquetado seguro
docs/                   Manuales técnicos, de uso, seguridad y despliegue
tests/                  Pruebas unitarias y de integración simulada
.github/workflows/      Matriz de CI, contenedor y análisis de seguridad
```

Empiece por [START_HERE](docs/START_HERE.md) y use el [índice de documentación](docs/README.md) para el resto: [arquitectura](docs/ARCHITECTURE.md), [API](docs/API_GUIDE.md), [CLI](docs/CLI.md), [autenticación](docs/AUTHENTICATION.md), [webhooks](docs/WEBHOOKS.md), [seguridad](docs/SECURITY.md), [reconciliación](docs/RECONCILIATION.md), [extensión](docs/ADDING_CONNECTOR.md), [problemas frecuentes](docs/TROUBLESHOOTING.md), [glosario](docs/GLOSSARY.md) y [fuentes oficiales](docs/SOURCES.md). La [documentación de sistema](docs/system-documentation/README.md) recorre el proyecto completo en 19 capítulos.

## Verificar el código

```bash
python -m pytest -q
python scripts/verify_repository.py
python scripts/demo_offline.py
```

`verify_repository.py` también comprueba coherencia: versión declarada en `pyproject.toml`, `__init__.py`, `config/catalog.json` y el título de este README; recuento real de proveedores y operaciones; enlaces Markdown locales; y codificación de los documentos. La demostración offline ejecuta pruebas simuladas identificadas como tales; no reemplaza una prueba con una cuenta autorizada.

## Alcance de producción y evolución

Esta entrega es una base ejecutable de integración **de una instancia y un dominio de confianza**, no un SaaS multiempresa listo para exposición pública. Antes de producción agregue las medidas del [checklist de seguridad](docs/SECURITY.md): TLS, autorización por usuario/cliente, protección de red, controles de carga compartidos, recuperación de estado, observabilidad y pruebas reales por proveedor. El límite de peticiones incluido vive en memoria de este proceso y no se comparte entre réplicas. No incorpora SSO, RBAC, aislamiento multitenant, workers distribuidos ni un motor visual de automatizaciones.

Si viene de v0.1, lea [migración a 0.2](docs/MIGRATION_0_1_TO_0_2.md); si viene de v0.2, [migración a 0.3](docs/MIGRATION_0_2_TO_0_3.md): las rutas centrales continúan y los cambios son aditivos. [Cambios](CHANGELOG.md) · [Auditoría](docs/AUDIT_0_1.md) · [Roadmap](ROADMAP.md) · [Cómo contribuir](CONTRIBUTING.md) · [Seguridad](SECURITY.md) · [Soporte](SUPPORT.md).

Código bajo [MIT](LICENSE). Las marcas, APIs, bibliotecas, mensajes y datos de terceros conservan sus condiciones. No se concede acceso a cuentas, créditos ni permisos de redistribución de datos. Autor original: Vladimir Acuña.
