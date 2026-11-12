# Índice de documentación

Toda la documentación está en español y distingue cuatro estados: **implementado** (existe código ejecutable), **probado offline** (validado con entradas controladas, no con una cuenta externa), **guía** (instrucciones para configurar o desplegar) y **pendiente** (no implementado). La escala se explica en [START_HERE](START_HERE.md).

## Empezar

| Documento | Para qué |
|---|---|
| [START_HERE](START_HERE.md) | Qué ruta seguir según si va a operar, desarrollar o implementar para un cliente. |
| [INSTALL](../INSTALL.md) | Requisitos, instalación en cada sistema, contenedor y verificación. |
| [ENVIRONMENTS](ENVIRONMENTS.md) | Windows, macOS, Linux, Docker, Dev Container y dónde vive el estado. |
| [WORK_SCENARIOS](WORK_SCENARIOS.md) | Soporte, oficina, comercio, educación y desarrollo: qué ya es ejecutable y qué falta. |

## Usar

| Documento | Para qué |
|---|---|
| [API_GUIDE](API_GUIDE.md) | Contrato HTTP, sobre unificado, escrituras, batch, ask, límites y errores. |
| [CLI](CLI.md) | Todos los comandos de `uao`, con lo que hace y lo que no hace cada uno. |
| [AUTHENTICATION](AUTHENTICATION.md) | API key, bearer, basic, OAuth con refresh y MSAL delegado. |
| [WEBHOOKS](WEBHOOKS.md) | Verificación de firma, challenge, deduplicación e inbox. |
| [RECONCILIATION](RECONCILIATION.md) | Qué hacer cuando una escritura queda en duda. Ningún reintento es automático. |
| [RUNBOOK](RUNBOOK.md) | Operación diaria: arranque, purga, límites de carga e incidentes. |
| [CONNECTOR_MATRIX](CONNECTOR_MATRIX.md) | Las 69 operaciones, sus parámetros y si leen o modifican datos. |

## Proveedores

| Documento | Cubre |
|---|---|
| [GMAIL](providers/GMAIL.md) | Gmail y Google Workspace: consentimiento, scopes, MIME y envío. |
| [WHATSAPP](providers/WHATSAPP.md) | WhatsApp Cloud API: plantillas, ventana de atención, medios y estados. |
| [MICROSOFT](providers/MICROSOFT.md) | Outlook, Graph y Teams con identidad delegada. |
| [MESSAGING](providers/MESSAGING.md) | Telegram, Slack, Discord, Twilio, SendGrid y Resend. |
| [WORKSPACE_AND_GITHUB](providers/WORKSPACE_AND_GITHUB.md) | Calendar, Drive y GitHub. |

## Construir y extender

| Documento | Para qué |
|---|---|
| [ARCHITECTURE](ARCHITECTURE.md) | Diseño, recorrido del código y límites de escala. |
| [ADDING_CONNECTOR](ADDING_CONNECTOR.md) | Añadir una operación o un sistema por catálogo declarativo. |
| [GLOSSARY](GLOSSARY.md) | Términos del proyecto con el significado exacto que tienen aquí. |
| [system-documentation](system-documentation/README.md) | El proyecto completo en 19 capítulos, de la visión general a la trazabilidad. |

## Seguridad, calidad y evidencia

| Documento | Para qué |
|---|---|
| [SECURITY](SECURITY.md) | Modelo de amenazas, controles implementados y checklist antes de producción. |
| [Política de reporte](../SECURITY.md) | Cómo reportar una vulnerabilidad y qué está dentro del alcance. |
| [VALIDATION](VALIDATION.md) | Qué se ejecutó realmente, con qué resultado y qué no se probó. |
| [TROUBLESHOOTING](TROUBLESHOOTING.md) | Cada código de error con su causa y su salida. |
| [SOURCES](SOURCES.md) | Documentación oficial consultada, con fecha. |
| [AUDIT_0_1](AUDIT_0_1.md) | Auditoría de la base recibida y qué se corrigió. |

## Cambios y versiones

| Documento | Para qué |
|---|---|
| [CHANGELOG](../CHANGELOG.md) | Qué cambió en cada versión, incluido lo que no cambió a propósito. |
| [MIGRATION_0_2_TO_0_3](MIGRATION_0_2_TO_0_3.md) | Subir de 0.2 a 0.3. Cambios aditivos. |
| [MIGRATION_0_1_TO_0_2](MIGRATION_0_1_TO_0_2.md) | Subir de 0.1 a 0.2. Incluye cambios de ruptura. |
| [STATUS](../STATUS.md) | Foto verificable del repositorio: recuentos, cobertura y lo no verificado. |
| [ROADMAP](../ROADMAP.md) | Qué sigue, qué requiere otra arquitectura y qué está fuera del alcance. |
| [history](history/README_v0.1.md) | Documentación conservada de la versión 0.1. |

## Participar

[CONTRIBUTING](../CONTRIBUTING.md) para enviar cambios, [CODE_OF_CONDUCT](../CODE_OF_CONDUCT.md) para la convivencia, [SUPPORT](../SUPPORT.md) para pedir ayuda y [AGENTS](../AGENTS.md) si quien edita el repositorio es un asistente de código.
