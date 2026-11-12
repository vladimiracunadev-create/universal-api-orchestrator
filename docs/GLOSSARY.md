# Glosario

Términos con el significado exacto que tienen **en este proyecto**. Varios se usan en la industria con sentidos más amplios; aquí la definición es la que está implementada en el código.

## Contrato y ejecución

**Sistema.** Entrada del catálogo (`config/systems.yaml`) que describe un servicio: protocolo, URL base, hosts permitidos, autenticación y operaciones. Un sistema puede ser un proveedor concreto (`gmail`) o un servicio genérico sobre un protocolo (`jsonplaceholder`). Hay 18 sistemas, de los cuales 13 son conectores de proveedor.

**Operación.** Acción nombrada dentro de un sistema, con su método, ruta, esquema de parámetros y efecto. Son 69 operaciones de proveedor. Una operación no es un endpoint libre: no se pueden pasar URL arbitrarias.

**Efecto (`effect`).** `read` o `write`. Determina si la operación pasa por las condiciones de aprobación. Se declara en el catálogo; si falta, se deduce del método HTTP, y un POST se considera `write` por defecto. Un POST de consulta (GraphQL, por ejemplo) debe declarar `read` explícitamente en una configuración confiable.

**Sobre unificado (`UnifiedResponse`).** Estructura de respuesta igual para todos los sistemas: `ok`, `system`, `operation`, `protocol`, `status_code`, `data`, `error` y `meta`. Permite cambiar de proveedor sin cambiar el parseo del cliente.

**Dos niveles de estado.** El HTTP del gateway y el `ok` de la operación son cosas distintas. `HTTP 200` con `ok:false` significa que el gateway procesó la petición y la operación falló. Revise siempre `ok`.

**Adaptador.** Implementación de un protocolo de transporte: REST, GraphQL, JSON-RPC, SOAP, gRPC o `provider`. Traduce la operación a una petición HTTP y normaliza el resultado mínimo.

**Constructor (`builder`).** Código que convierte parámetros normalizados en el cuerpo concreto que espera un proveedor: un MIME de Gmail, un `messaging_product` de WhatsApp, un `toRecipients` de Graph.

**Normalización (`response_map`).** Selección de campos con JMESPath sobre la respuesta del proveedor. No ejecuta código del cliente y es opcional: sin mapa, `data` conserva el formato original.

**`_content`.** Campo que Gmail añade cuando la respuesta trae MIME real: asunto, remitente, destinatario, fecha, texto decodificado y referencias a adjuntos. Un listado de IDs **no** lo trae: no se inventan cuerpos a partir de identificadores.

**Batch.** Hasta 20 operaciones independientes en una llamada, con alias únicos. No es una transacción ni un grafo de dependencias: el resultado de una no alimenta a la siguiente, y un fallo no deshace lo ya escrito.

**Ask.** Composición de una respuesta a partir de varias consultas **solo de lectura**, con fuentes y errores visibles. Rechaza toda escritura aunque el llamante tenga la clave de aprobación. Devuelve siempre `sent: false`.

**Modo determinista.** Composición sin modelo: presenta los datos obtenidos y la plantilla, si la hay. No interpreta intenciones ni decide qué APIs llamar. El cliente elige las operaciones.

## Permisos y seguridad

**Clave del gateway (`GATEWAY_API_KEY`).** Autentica a la aplicación cliente en `X-API-Key`. No es la credencial del proveedor: esa se resuelve en el backend y nunca sale.

**Clave de aprobación (`APPROVAL_API_KEY`).** Secreto separado, en `X-Approval-Key`, necesario para escribir, reconocer eventos, liberar reservas y recargar el catálogo. Es un secreto compartido, **no** la firma de una persona concreta: para atribución real hace falta identidad por usuario, que esta versión no implementa.

**Las cuatro condiciones.** Para que salga una escritura deben cumplirse a la vez: `ALLOW_WRITES=true` en el servidor, clave de aprobación válida, `confirmed: true` en la petición y una `idempotency_key` sin conflicto. Ninguna sustituye a otra.

**`confirmed`.** Campo de la petición que afirma que un humano revisó destinatario y contenido. Los ejemplos del repositorio lo traen en `false` a propósito, y `--approve` de la CLI **no** lo cambia.

**Allowlist de hosts.** Lista de nombres de host que una operación puede contactar. Lo que no está en la lista se rechaza con `HOST_NOT_ALLOWED`, antes de resolver DNS.

**Defensa de salida.** Conjunto de controles antes de cada petición: allowlist, exigencia de TLS, prohibición de redirecciones, bloqueo de direcciones no globales y filtrado de cabeceras del llamante. Mitiga SSRF; no sustituye un firewall de egreso contra DNS rebinding.

**Cabeceras prohibidas.** `Authorization`, `Host`, `Cookie`, `Proxy-Authorization` y `X-API-Key` nunca pueden venir del llamante. Las demás solo pasan si el sistema las declara en su allowlist.

**Datos sensibles (`sensitive`).** Marca de sistema que indica que sus datos son correo o mensajería personal. Con `AI_ALLOW_SENSITIVE_DATA=false`, un resultado sensible no se envía a un modelo: la respuesta sale en modo determinista con la advertencia `AI_SENSITIVE_DATA_BLOCKED`.

**`STATE_KEY`.** Clave Fernet que cifra tokens, reservas e inbox en SQLite. No se rota con estado existente: una clave distinta deja el estado ilegible.

## Escrituras y estado

**Idempotencia local.** Mecanismo que evita repetir la misma escritura: la clave se guarda con la huella SHA-256 del contenido (sistema, operación, parámetros y cabeceras). Misma clave y mismo contenido devuelve el resultado guardado sin reenviar; misma clave con otro contenido da `IDEMPOTENCY_CONFLICT`. Es **local**: no garantiza entrega exactamente una vez ni sustituye la idempotencia del proveedor.

**Reserva.** Fila que ocupa una clave de idempotencia antes de enviar. Nace `pending` y pasa a `complete` cuando se conoce el resultado.

**`reservation_id`.** SHA-256 de `sistema:idempotency_key`. Identifica una reserva para reconciliarla sin exponer la clave original.

**Reconciliación.** Procedimiento humano para cerrar una escritura cuyo resultado real se desconoce: comprobarlo en el proveedor y declararlo. Descrito en [RECONCILIATION](RECONCILIATION.md). Ningún reintento ocurre automáticamente.

**`requires_reconciliation`.** Campo de `meta` que indica que la escritura falló **después** de reservar su clave, de modo que el resultado es ambiguo.

**`delivery: provider_accepted_not_delivery_receipt`.** El proveedor aceptó la petición. No significa entregado, ni leído, ni recibido por el destinatario. La distinción es deliberada.

**Inbox.** Bandeja persistente y cifrada de eventos recibidos por webhook, deduplicados por sistema y clave de evento. No es una cola distribuida ni un motor de respuesta automática.

**`ack`.** Reconocimiento **local** de que un consumidor procesó un evento. No responde nada al proveedor.

## Operación

**Identidad de llamada.** Resumen SHA-256 de la clave del gateway o, si no hay, de la dirección del cliente. Sirve para contar peticiones en el límite de carga sin almacenar la clave.

**Token bucket.** Algoritmo del límite de carga: una reserva de `RATE_LIMIT_BURST` peticiones que se recarga a `RATE_LIMIT_PER_MINUTE/60` por segundo. Vive en memoria de un proceso y no se comparte entre réplicas.

**`X-Request-Id`.** Identificador de la petición HTTP presente en toda respuesta. Si el cliente envía uno con formato seguro, se reutiliza para correlacionar registros.

**`trace_id`.** Identificador por operación dentro de `meta`. Aparece en los registros de auditoría junto al sistema, la operación y el código de error, nunca con el contenido.

**Recarga en caliente.** `POST /v1/admin/reload` relee el catálogo sin reiniciar el proceso. Un catálogo inválido deja el anterior en uso. Las variables de entorno **no** se recargan.

## Estados de una función

**Implementada.** Existe un camino de código ejecutable. **Probada offline.** Validada con entradas controladas y transporte simulado, no con una cuenta externa. **Guía.** Hay instrucciones para configurar o desplegar, sin ejecución verificada aquí. **Pendiente.** No está implementada. No son categorías equivalentes y el proyecto no las mezcla.
