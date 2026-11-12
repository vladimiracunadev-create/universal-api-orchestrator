# 17 · Resumen ejecutivo

Una página, sin jerga, para quien decide si esto sirve.

## Qué es

Un **componente de software** que su equipo instala en su propio servidor y que unifica el acceso a 13 servicios de correo y mensajería: Gmail, Outlook, WhatsApp, Teams, Slack, Discord, Telegram, Twilio, SendGrid, Resend, Calendar, Drive y GitHub. Su aplicación le habla con un solo formato y él traduce a cada proveedor.

No es un servicio contratado, no es una plataforma con panel de administración y no requiere una cuenta en este proyecto. Es código abierto con licencia MIT que usted ejecuta y controla.

## Qué problema resuelve

Cuando una organización conecta varios canales, aparecen cuatro costos previsibles: un desarrollo distinto por cada proveedor, credenciales repartidas donde no deberían estar, envíos accidentales a clientes reales, y mensajes de los que nadie sabe si salieron.

Este componente responde a los cuatro: un solo contrato técnico, las credenciales solo en el servidor, cuatro condiciones simultáneas para que algo se envíe, y un procedimiento explícito para cerrar los casos dudosos.

## El principio que lo ordena

**Consultar no es lo mismo que enviar.** Leer datos y enviar mensajes son dos caminos separados en el código, con permisos distintos. Enviar exige cuatro condiciones a la vez: que la instancia tenga el envío habilitado, que se presente una clave de aprobación separada, que la petición confirme explícitamente, y que traiga una clave que impida duplicados. Olvidar una variable de configuración no basta para que salga un mensaje.

El segundo principio es **no afirmar más de lo verificado**. La documentación distingue en todo momento lo implementado, lo probado sin cuentas reales, lo que es solo una guía y lo que falta.

## Qué se obtiene hoy

| Capacidad | Estado |
|---|---|
| 13 servicios, 69 operaciones, con un contrato único | Implementado y probado sin cuentas reales |
| Credenciales cifradas en el servidor, nunca en la aplicación cliente | Implementado |
| Cuatro condiciones para enviar, y protección contra duplicados | Implementado |
| Procedimiento para cerrar un envío de resultado desconocido | Implementado |
| Recepción de eventos con verificación de origen (4 proveedores) | Implementado |
| Respuestas compuestas con sus fuentes, sin inventar contenido | Implementado |
| Uso de un modelo de lenguaje | Opcional, apagado, con bloqueo de datos sensibles |
| Funcionamiento en Windows, Linux, macOS y contenedor | Guías y configuración; probado en Windows en esta entrega |

## Qué **no** se obtiene

- **No garantiza la entrega al destinatario.** Distingue "el proveedor aceptó" de "llegó", y solo el primero es verificable desde aquí.
- **No es multiempresa.** Sin usuarios, sin roles, sin separación entre clientes. Una instalación sirve a un único ámbito de confianza.
- **No está probado con cuentas reales.** Ninguna de las 13 integraciones se ejecutó contra una cuenta de producción en esta entrega. Es el trabajo que debe hacer quien lo despliegue, y hay una ficha para registrarlo.
- **No escala a varias copias.** El estado es local a un proceso.
- **No decide por sí mismo.** No interpreta instrucciones ni elige qué hacer: su aplicación manda.
- **No incluye cuentas, consumos ni aprobaciones de los proveedores.** Esos trámites y costos son de su organización.

## Calidad comprobable

| Indicador | Valor |
|---|---|
| Pruebas automatizadas, sin red ni credenciales | 162, todas pasan |
| Cobertura de líneas del código | 76,4 % |
| Análisis de estilo y de seguridad del código | sin hallazgos |
| Vulnerabilidades conocidas en dependencias | ninguna |
| Documentación | 61 documentos, incluidos 19 capítulos técnicos |
| Verificación de coherencia | automatizada: la documentación no puede desincronizarse de las cifras sin que falle |

Cualquiera puede reproducir esos números con cinco comandos y sin ninguna cuenta externa. Están en [VALIDATION](../VALIDATION.md) y [STATUS](../../STATUS.md).

## Qué hace falta para ponerlo en producción

| Necesidad | Quién la cubre |
|---|---|
| Un servidor y un certificado HTTPS con proxy inverso | Su infraestructura |
| Cuentas y permisos en cada proveedor que vaya a usar | Su organización |
| Verificar cada integración con una cuenta de prueba | Su equipo técnico, con la ficha incluida |
| Identidad y permisos propios, si hay varias personas aprobando | Desarrollo adicional |
| Respaldo del estado y de su clave, con prueba de restauración | Su operación |
| Revisión legal de los datos que va a mover | Su asesoría |

El checklist completo está en el documento de seguridad. Tenerlo escrito no equivale a estar certificado, y el proyecto no afirma lo contrario.

## Para quién tiene sentido

**Sí**, si necesita conectar varios canales desde un backend propio, quiere las credenciales fuera de la aplicación cliente y valora que enviar un mensaje requiera una decisión explícita.

**No**, si busca un servicio alojado sin administración, necesita aislamiento entre varias empresas desde el primer día, o espera que el sistema decida solo qué mensajes enviar.

## Costo y licencia

El código es gratuito, licencia MIT: puede usarlo, modificarlo y distribuirlo, incluso comercialmente. Lo que **no** es gratuito son las cuentas, el consumo de las APIs, los números de teléfono, el servidor y, si lo activa, el modelo de lenguaje. Este proyecto no fija ni intermedia esas tarifas: consúltelas con cada proveedor.

El esfuerzo real está en la verificación por proveedor y en la infraestructura de producción, no en instalar el componente.

## En una frase

Un intermediario que unifica 13 canales de mensajería con un solo contrato, mantiene las credenciales en su servidor y trata el envío de un mensaje como una decisión que alguien debe tomar, no como un efecto secundario de una configuración.

## Fuentes de este capítulo

`README.md`, `STATUS.md`, `docs/VALIDATION.md`, `docs/SECURITY.md`, `docs/CONNECTOR_MATRIX.md`, `ROADMAP.md`, `LICENSE`.
