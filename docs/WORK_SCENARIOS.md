# Aplicación en distintos entornos de trabajo

El mismo gateway puede ser componente de soluciones distintas. **Los recorridos de esta guía son diseños de integración**, salvo los ejemplos ejecutables expresamente enlazados. No se vende como implementado un ERP, CRM o bot de negocio que no está en el código.

## Atención al cliente: WhatsApp, pedido y respuesta revisada

El mensaje entrante llega al webhook Meta y se guarda tras verificar firma. Un consumidor interno lee el inbox. La empresa registra un conector REST de consulta para su sistema de pedidos: cliente, pedido, estado y compromisos. El consumidor hace esas consultas y prepara la respuesta con datos reales. Un operador revisa identidad, consentimiento, contenido y ventana del canal; entonces autoriza un `send_text` o `send_template` con clave idempotente por acción.

Implementado aquí: webhook, inbox, cliente REST extensible, `ask`, envío y controles. Por implementar para la empresa: conector de pedidos con su contrato, correlación de identidad, políticas del negocio, interfaz de operador, consumidor durable y registro de consentimiento. No se infiere que un teléfono que pregunta sea dueño de cualquier pedido.

## Oficina: correos pendientes y agenda

Primero se buscan mensajes y luego se leen cuerpos concretos. Se consulta Calendar con rango explícito. `/ask` compone fuentes y fallos. Sin IA se obtiene una estructura reproducible; con un modelo aprobado puede redactarse un resumen revisable. La respuesta no se envía por correo ni se convierte automáticamente en eventos.

Ejecutable: [gmail_brief.py](../examples/workflows/gmail_brief.py) para Gmail, y [ask-multisource.json](../examples/requests/ask-multisource.json) para listado/agenda. Este último usa listado de IDs, no cuerpos: sirve para agregación, no para atribuir contenido a mensajes no leídos.

Para crear un borrador use `gmail/create_draft` con aprobación. Para reservar una reunión use `google_calendar/create_event` tras revisión. No hay planificador autónomo ni agenda de tareas programadas implementada.

## Comercio: notificación de pedido

La aplicación de comercio produce un identificador estable de pedido. Consulta estado e inventario mediante operaciones REST configuradas y prepara una notificación por correo transaccional o WhatsApp. Se registra una clave idempotente como combinación de pedido, tipo de notificación y versión del estado. La aprobación se otorga desde un proceso de confianza, no desde el navegador del comprador.

Implementado: transportes, SendGrid/Resend, WhatsApp e idempotencia local. Pendiente: API del comercio, reglas de transacciones, conciliación, plantillas aprobadas, protección de datos, límites de gasto y monitoreo de entrega donde el conector no incluye webhook.

El gateway no ejecuta pagos ni valida obligaciones tributarias; agregar esos proveedores requiere conectores y controles propios. Tampoco convierte una confirmación del gateway en comprobante de pago o entrega.

## Desarrollo y soporte técnico

GitHub notifica un issue/evento al inbox. El equipo consulta el repositorio y publica un aviso aprobado en Slack o Teams. Para responder a un incidente, conserve el evento original, los resultados consultados, el contenido revisado y la clave de la acción. Los logs técnicos no contienen el cuerpo del mensaje por defecto, por lo que el registro de negocio debe vivir en un almacén protegido definido por el equipo.

No hay workflow automático que enlace eventos GitHub a Slack al instalar; la separación evita activaciones accidentales y deja explícitas las políticas a implementar.

## Educación y organizaciones

Calendar y correo pueden apoyar coordinación, consultas documentales o recordatorios. Antes de tratar datos de estudiantes, familias o personal, determine finalidad, permisos, minimización y acceso. Nunca envíe un buzón completo a un modelo solo porque la integración permite hacerlo técnicamente.

El repositorio no sustituye la plataforma escolar, autorización institucional ni evaluación de requisitos legales. Sirve como componente técnico, no como evidencia de cumplimiento.

## Sistemas heredados y stacks diferentes

Un backend PHP puede llamar al gateway con cURL sin implementar OAuth Google o MIME otra vez. Node/TypeScript puede usar fetch, Python HTTPX y PowerShell Invoke-RestMethod. La aplicación cliente conserva sus reglas de negocio; el gateway concentra conectividad y controles.

El mismo contrato puede consumirse desde Java/.NET, una app móvil o un ERP que permita HTTP. Solo se incluyen clientes ejecutables de Python, Node.js, PHP, PowerShell y cURL; no se entregan aplicaciones nativas de escritorio o móvil. No ponga la clave de aprobación dentro de un APK, JavaScript público o macro distribuida.

## Entrega a un cliente

Acordar alcance concreto de operaciones, cuenta/propiedad de datos, entornos, permisos, costos y soporte. Probar contratos offline, luego lecturas reales pequeñas, luego una escritura consentida y su resultado. Documentar quién aprueba y quién administra tokens, respaldo y revocación. La [matriz](CONNECTOR_MATRIX.md) y [VALIDATION](VALIDATION.md) permiten separar entregable técnico de activación/aceptación comercial.
