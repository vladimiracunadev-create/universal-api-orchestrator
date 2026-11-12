# Roadmap después de v0.3.0

## Entregado hasta aquí

13 conectores de servicio con 69 operaciones, protocolos genéricos (REST, GraphQL, JSON-RPC, SOAP y gRPC opcional), OAuth local con refresh y MSAL, esquema de parámetros por operación, las cuatro condiciones de escritura, idempotencia local con reconciliación explícita, cifrado de valores en SQLite con WAL, webhooks verificados para cuatro proveedores, inbox deduplicado, composición con fuentes y modelo opcional, pool HTTP compartido, control de carga local, identidad de petición, recarga de catálogo en caliente, clientes HTTP en cuatro lenguajes, guías de entorno y 162 pruebas offline.

Que el código esté entregado no significa que se hayan activado cuentas ni probado endpoints de producción. Consulte [VALIDATION](docs/VALIDATION.md) y [STATUS](STATUS.md).

## Siguiente capa: operación confiable

Consumidor autenticado de Pub/Sub para Gmail, renovación de `watch` y del cursor de historia, suscripciones de Microsoft Graph, firmas y eventos de entrega de Twilio, SendGrid y Resend, paginación segura por proveedor y reglas de consentimiento y ventana de WhatsApp. Añadir pruebas de aceptación opt-in, nunca envíos automáticos desde la CI general.

En esta capa también entra lo que v0.3.0 dejó a medio camino a propósito: métricas en formato de scraping, registro estructurado en JSON con el identificador de petición, y una reconciliación asistida que consulte el estado en el proveedor en lugar de pedir al operador que lo compruebe a mano.

## Plataforma para varias instancias

Almacén transaccional externo, tokens protegidos por un gestor de secretos, cola durable con leases y dead-letter queue, idempotencia distribuida, límite de carga compartido entre réplicas, límites de cuota y costo por proveedor, circuit breaker y observabilidad. No se resuelve escalando el SQLite actual a más workers, y el token bucket en memoria de esta versión no es el límite definitivo: es un control de una sola instancia.

## Plataforma para varios clientes

Identidad, SSO/OIDC, autorización por tenant, recurso y operación, aprobaciones atribuibles a una persona en lugar de a una clave compartida, OAuth multiusuario con callbacks web, segregación de secretos y auditoría consultable. Sin esos componentes la instancia debe permanecer en un único dominio de confianza.

## Más sistemas

SMTP/IMAP con autenticación moderna, CRM y ERP específicos, medios de pago, almacenamiento de objetos, SFTP, bases de datos, colas y transporte streaming. Cada uno requiere contratos, documentación y pruebas, no solo una entrada con nombre comercial en el catálogo.

## Composición avanzada

Motor de workflows con dependencias, compensaciones y programación; interfaz de revisión humana; herramientas para agentes con autorización estricta; modelos locales y otros contratos de IA. No hay fechas comprometidas ni tareas que se ejecuten solas después de clonar el repositorio.

## Fuera del alcance previsto

Un motor visual de automatizaciones, un panel de administración multiempresa, reenvío automático de escrituras en duda y cualquier función que afirme entrega al destinatario sin un recibo del proveedor. Si alguna se añade, se hará con su documentación y sus límites declarados, no como efecto lateral de otra cosa.
