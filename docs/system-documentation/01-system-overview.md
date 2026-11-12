# 01 · Visión general del sistema

## Qué es

Universal API Orchestrator es un **backend intermedio**: un proceso que su aplicación llama con un contrato único y que traduce esa llamada al contrato concreto de 13 servicios de correo, mensajería y colaboración, además de cuatro protocolos genéricos. Es una biblioteca ejecutable con una API HTTP, no un producto con interfaz de usuario ni un servicio alojado.

Se ejecuta como un proceso FastAPI sobre Uvicorn, guarda su estado en un SQLite local cifrado y no necesita ninguna infraestructura externa: ni base de datos, ni cola, ni Redis, ni cuenta en la nube.

## Qué problema resuelve

Integrar varios proveedores de mensajería suele producir cuatro problemas concretos:

1. **Un cliente distinto por API.** Gmail usa MIME en base64url, Microsoft Graph usa `toRecipients`, WhatsApp exige `messaging_product`, Slack responde `ok:false` con HTTP 200. Cada integración acaba con su propio código, su propio manejo de errores y su propio formato de respuesta.
2. **Credenciales repartidas.** Tokens de proveedor en el frontend, en variables sueltas, en el repositorio o en el móvil del usuario.
3. **Envíos accidentales.** Un `ALLOW_SEND=true` olvidado, un script de prueba apuntando a producción, un reintento automático que duplica un mensaje.
4. **Estados ambiguos que nadie cierra.** Una petición de envío que no devolvió respuesta: nadie sabe si salió, y el sistema decide por su cuenta reintentar o abandonar.

Este proyecto responde con un catálogo declarativo (el primero), secretos resueltos solo en el backend (el segundo), cuatro condiciones simultáneas para escribir (el tercero) y una reconciliación humana explícita (el cuarto).

## Para quién

| Perfil | Qué obtiene |
|---|---|
| Desarrollador que integra varios canales | Un solo contrato HTTP y un sobre de respuesta igual para todos. |
| Equipo de soporte o de oficina | Consultas compuestas con fuentes, sin exponer credenciales a la aplicación cliente. |
| Responsable técnico | Políticas explícitas de escritura, idempotencia y defensa de salida, auditables en el código. |
| Quien mantiene sistemas heredados | Adaptadores SOAP y JSON-RPC junto a los REST modernos, bajo el mismo contrato. |

No está dirigido a quien necesite un SaaS multiempresa listo para usar, ni a quien quiera un motor visual de automatizaciones.

## Capacidades

- **13 conectores de proveedor con 69 operaciones**: Gmail, WhatsApp Cloud API, Outlook/Graph, Telegram, Slack, Discord, Twilio, SendGrid, Resend, Google Calendar, Google Drive, Microsoft Teams y GitHub. La [matriz](../CONNECTOR_MATRIX.md) enumera cada una.
- **Cinco protocolos de transporte**: REST, GraphQL, JSON-RPC, SOAP y gRPC opcional, más el adaptador `provider` para contratos con particularidades.
- **Autorización de proveedor**: API key, bearer, basic, OAuth 2 con refresco, client credentials y MSAL delegado, con el material cifrado en reposo.
- **Composición de respuestas** a partir de varias consultas de solo lectura, con fuentes y errores visibles, de forma determinista; con un modelo de lenguaje solo si se activa a propósito.
- **Eventos entrantes** por webhook con verificación de firma, deduplicación y bandeja persistente.
- **Políticas de envío**: cuatro condiciones simultáneas, idempotencia con huella del contenido y reconciliación explícita de resultados desconocidos.
- **Defensa de salida**: allowlist de hosts, TLS obligatorio, sin redirecciones, bloqueo de direcciones no globales y filtrado de cabeceras del llamante.
- **Operación**: control de carga local, identidad de petición, recuentos del estado, recarga de catálogo en caliente y purga selectiva.

## Qué **no** hace

No es un chatbot ni decide qué API llamar a partir de una frase: el cliente elige las operaciones. No garantiza entrega al destinatario: distingue "el proveedor aceptó" de "llegó". No reintenta escrituras. No implementa SSO, RBAC ni aislamiento entre empresas. No coordina varias réplicas: el estado, los locks y el contador de carga son de una instancia. No incluye SMTP/IMAP, pagos, CRM específicos, bases de datos ni streaming como conectores. No descarga ni ejecuta modelos de lenguaje. No crea cuentas, no aprueba plantillas y no paga consumos de API: eso ocurre en el proveedor.

## Principio de diseño

**Consultar no equivale a enviar.** Toda la arquitectura se ordena alrededor de esa frase: la política se evalúa antes del transporte, `/v1/ask` no puede escribir aunque el llamante tenga la clave de aprobación, los ejemplos del repositorio vienen con `confirmed:false`, y un resultado desconocido bloquea en lugar de adivinar.

El segundo principio es **no afirmar más de lo verificado**. Por eso existen [VALIDATION](../VALIDATION.md) y [STATUS](../../STATUS.md), y por eso la documentación distingue implementado, probado offline, guía y pendiente.

## Estado actual

Versión 0.3.0. 162 pruebas automatizadas sin red, 76,4 % de cobertura de líneas, lint y análisis estático sin hallazgos, dependencias sin vulnerabilidades conocidas. **Ninguna operación se ha ejecutado contra una cuenta real en esta entrega.** El detalle está en [VALIDATION](../VALIDATION.md).

## Tecnología

Python 3.11 o superior; FastAPI y Uvicorn; httpx para la salida; Pydantic para los contratos; PyYAML para el catálogo; jsonschema para los parámetros; JMESPath para la normalización; `cryptography` (Fernet) para el cifrado del estado; defusedxml para SOAP; opcionalmente `google-auth-oauthlib`, `msal` y `grpcio`. Sin dependencias de sistema operativo y sin servicios externos obligatorios.

## Fuentes de este capítulo

`README.md`, `config/systems.yaml`, `config/catalog.json`, `src/universal_api_orchestrator/`, `docs/CONNECTOR_MATRIX.md`, `docs/VALIDATION.md`, `STATUS.md`.
