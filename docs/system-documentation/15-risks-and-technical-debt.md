# 15 · Riesgos y deuda técnica

Lista honesta de lo que puede fallar y lo que falta. Un riesgo declarado se puede gestionar; uno oculto se descubre en producción.

## Riesgos de arquitectura

### R1 · Una sola instancia, sin coordinación

**Severidad: alta si se intenta escalar.** SQLite local, locks de OAuth en memoria y un contador de carga por proceso. Dos réplicas con volúmenes distintos pueden enviar el mismo mensaje dos veces, porque cada una tiene sus propias reservas.

*Mitigación actual:* está documentado en cada capítulo que toca el tema, y la topología de varias réplicas se declara **no soportada**.
*Lo que falta:* almacén transaccional compartido, locks distribuidos y límite de carga compartido. No se arregla con más workers.

### R2 · La clave de aprobación no identifica a nadie

**Severidad: alta en un entorno con varias personas.** Es un secreto compartido: cualquier proceso que la tenga puede aprobar un envío, liberar una reserva o recargar el catálogo. Una liberación queda registrada como hecha, no como hecha *por alguien*.

*Mitigación actual:* está separada de la clave del gateway, y la documentación insiste en que no es una firma personal.
*Lo que falta:* identidad, autorización por usuario y aprobaciones atribuibles. Sin eso, la instancia debe permanecer en un único dominio de confianza.

### R3 · DNS rebinding

**Severidad: media.** `assert_safe_endpoint` resuelve y valida antes de conectar; entre la validación y la conexión hay una ventana en la que el DNS puede cambiar.

*Mitigación actual:* allowlist de hosts, prohibición de redirecciones y el propio código documentando el límite.
*Lo que falta:* un firewall o proxy de egreso con destinos fijos. Es responsabilidad de la infraestructura y está dicho así.

### R4 · Pérdida de `STATE_KEY`

**Severidad: alta, probabilidad baja.** Sin esa clave, los tokens son irrecuperables y las reservas de idempotencia ilegibles: hay que repetir cada consentimiento y reconciliar a mano lo que estuviera en duda.

*Mitigación actual:* `bootstrap.py` se niega a generar una clave nueva si ya hay base de datos, y `pending()` marca las filas ilegibles en lugar de fallar.
*Lo que falta:* integración con un gestor de secretos y un procedimiento de recuperación ensayado por el operador.

### R5 · El límite de carga no protege de un abuso real

**Severidad: media.** Es un token bucket en memoria, por instancia. No defiende de una denegación de servicio distribuida ni de un cliente que ya tiene la clave.

*Mitigación actual:* límites de tamaño de entrada y de respuesta, semáforo de concurrencia, y la declaración explícita de que el control es local.
*Lo que falta:* límite compartido, cuotas por proveedor y circuit breaker. La capa correcta es el proxy inverso.

### R6 · Dependencia del contrato de terceros

**Severidad: media, probabilidad alta con el tiempo.** Trece proveedores pueden cambiar su API sin avisar. Una operación puede dejar de funcionar sin que este repositorio cambie.

*Mitigación actual:* [SOURCES](../SOURCES.md) con fechas, pruebas de constructor que detectan un cambio de forma en el código propio, y errores estables que no esconden el fallo.
*Lo que falta:* pruebas de contrato opt-in contra cuentas de prueba, ejecutadas de forma periódica y no en la CI general.

## Deuda técnica

### D1 · Ninguna integración verificada con cuentas reales

**El riesgo más importante de la entrega.** 162 pruebas con transporte simulado dicen que el código hace lo que cree hacer; no dicen que el proveedor acepte ese cuerpo, que la plantilla esté aprobada o que la cuota alcance.

*Qué hay:* la ficha de aceptación por proveedor en [VALIDATION](../VALIDATION.md), para que quien lo despliegue registre lo que sí comprobó.
*Qué falta:* esa verificación, proveedor por proveedor. Sin ella, cada integración es "implementada y probada offline", nunca "probada".

### D2 · Paginación sin consumidor genérico

Los esquemas admiten cursores (`pageToken`, `cursor`, `offset`) pero el gateway **no recorre páginas** ni sigue un `nextLink` recibido. Quien necesite recorrer debe mapear el cursor en su `response_map` e iterar desde su cliente.

Decisión deliberada: seguir automáticamente un enlace que viene en la respuesta de un tercero es la puerta de entrada a una petición no prevista. Un consumidor seguro debe validar que el cursor pertenece al mismo host permitido.

### D3 · Eventos solo de cuatro proveedores

Hay webhooks verificados para Meta, Telegram, Slack y GitHub. **Faltan** el consumidor de Pub/Sub de Gmail (la operación `watch` registra la suscripción, pero las notificaciones no llegan al inbox), las suscripciones de Microsoft Graph y los eventos de entrega de Twilio, SendGrid y Resend.

Consecuencia práctica: WhatsApp es el único canal donde se puede seguir la entrega real. En los demás, "aceptado" es todo lo que se sabe.

### D4 · gRPC genérico y poco útil

El adaptador hace una llamada unary con bytes. Sin stubs generados de un contrato concreto, serializar y deserializar queda del lado del cliente. No hay streaming ni reflexión.

Es honesto en su alcance (está declarado), pero en la práctica sirve para poco más que demostrar que el transporte existe.

### D5 · Cobertura concentrada en lo simulable

76,4 %. El 23,6 % restante es casi todo lo que necesita credenciales o servicios reales: OAuth interactivo, device code, caminos de MSAL con varias cuentas, gRPC real. Subir la cifra parcheando con *mocks* de más no mejoraría la confianza: la mejora real es D1.

### D6 · Estilo heterogéneo del código

Los módulos de 0.2 están escritos en un estilo muy denso (sin espacios tras las comas, varias sentencias por línea); los de 0.3 siguen un estilo más convencional. Las reglas de lint activas excluyen `E7` precisamente para no pelear con esa decisión.

Reformatear todo en un cambio funcional haría el diff irrevisable, así que la convención es no mezclarlo. Es deuda real, de las baratas.

### D7 · Observabilidad mínima

Hay `/health`, `/v1/stats`, `X-Request-Id`, `trace_id` y un registro de auditoría de una línea por operación. **No** hay métricas en formato de scraping, ni registro estructurado en JSON, ni trazas distribuidas, ni alertas.

Para una instancia que alguien vigila a mano es suficiente; para un servicio con guardia, no.

### D8 · Reconciliación manual de principio a fin

Hoy el operador comprueba en el proveedor y declara el resultado. Varios proveedores permiten consultar el estado de un mensaje por su identificador, de modo que una reconciliación **asistida** sería posible: el gateway propone lo que encontró y el humano confirma.

La decisión seguiría siendo humana —ese es el principio—, pero el trabajo de buscar lo podría hacer la máquina.

### D9 · Un solo catálogo, una sola forma de habilitar

`uao enable` escribe en el YAML del repositorio. En un despliegue donde el catálogo venga de la imagen, ese archivo puede ser de solo lectura. La alternativa existe (apuntar `SYSTEMS_CONFIG` a un directorio propio), pero no está presentada como la forma recomendada en un contenedor.

## Lo que está fuera del alcance a propósito

No son deuda: son decisiones. Un motor visual de automatizaciones. Un panel de administración multiempresa. Reenvío automático de escrituras en duda. Cualquier afirmación de entrega sin un recibo del proveedor. Interpretar una frase del usuario para elegir qué API llamar. Si algo de esto se añadiera, sería con su documentación y sus límites, no como efecto lateral.

## Prioridad sugerida

| Orden | Qué | Por qué primero |
|---|---|---|
| 1 | D1: verificar un proveedor real de punta a punta | Convierte "implementado" en "probado". Nada más importa tanto |
| 2 | D3 parcial: eventos de entrega de un canal transaccional | Cierra el hueco entre aceptado y entregado |
| 3 | D7: registro estructurado y métricas | Hace operable lo que ya existe |
| 4 | R2: identidad y aprobaciones atribuibles | Es el requisito para más de una persona |
| 5 | R1: almacén compartido | Es el requisito para más de una instancia |
| 6 | D8: reconciliación asistida | Reduce el trabajo manual sin quitar la decisión |

Los detalles de cada capa están en el [ROADMAP](../../ROADMAP.md). No hay fechas comprometidas.

## Fuentes de este capítulo

Lectura del código con sus comentarios de límite (`security.py`, `store.py`, `transport.py`, `orchestrator.py`), `docs/SECURITY.md`, `docs/VALIDATION.md`, `docs/API_GUIDE.md`, `ROADMAP.md`, y la cobertura real de `docs/validation-results/coverage.json`.
