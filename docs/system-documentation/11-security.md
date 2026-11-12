# 11 · Seguridad

El checklist operativo está en [docs/SECURITY.md](../SECURITY.md) y la política de reporte en [SECURITY.md](../../SECURITY.md). Este capítulo es el análisis: qué se protege, contra qué, con qué mecanismo y qué queda fuera.

## Modelo de confianza

| Elemento | Confiable | Por qué |
|---|---|---|
| `config/systems.yaml` | **Sí** | Lo administra el operador. Una petición externa no puede modificarlo. |
| Variables de proceso | **Sí** | Las pone quien despliega. |
| Cliente HTTP autenticado | Parcialmente | Tiene la clave, pero sus parámetros se validan y sus cabeceras se filtran. |
| Respuestas de proveedor | **No** | Datos, no instrucciones. Se acotan, se normalizan y nunca se ejecutan. |
| Contenido de mensajes | **No** | Puede contener texto diseñado para manipular a un modelo o a un lector. |
| Webhooks entrantes | **No hasta verificar la firma** | Y la verificación ocurre antes de deserializar. |

De ahí se derivan dos consecuencias de diseño. El `effect` de una operación solo lo puede declarar el catálogo, porque es una decisión de confianza. Y el cliente no puede aportar una URL de destino: solo elegir entre las operaciones declaradas.

## Amenazas y controles

| Amenaza | Control implementado | Dónde |
|---|---|---|
| Acceso no autorizado al gateway | Clave obligatoria en todas las rutas `/v1`, comparada con `compare_digest`; 503 si no está configurada | `main.py` |
| Envío accidental o no autorizado | Cuatro condiciones simultáneas: `ALLOW_WRITES`, clave de aprobación, `confirmed`, `idempotency_key` | `orchestrator.py` |
| Escritura encubierta en una consulta | `/v1/ask` fuerza `read_only`; una escritura responde `ASK_IS_READ_ONLY` aunque haya aprobación | `orchestrator.py`, `main.py` |
| Operación de escritura disfrazada de lectura | Un POST sin `effect` se considera escritura; solo el catálogo puede declarar `read` | `orchestrator.py` |
| SSRF por URL arbitraria | El cliente no aporta URL; allowlist de hosts obligatoria por sistema | `security.py`, `registry.py` |
| SSRF por redirección | `follow_redirects=False`; cualquier 3xx es error | `transport.py` |
| SSRF a metadatos de nube o red interna | Toda dirección resuelta debe ser global, salvo habilitación explícita | `security.py` |
| Robo de credenciales vía cabeceras | Cinco cabeceras prohibidas y allowlist por sistema para el resto | `security.py` |
| Fuga de secretos en respuestas | Códigos de error estables sin URL, cuerpo ni cabeceras; catálogo público sin expandir variables | `errors.py`, `registry.py` |
| Fuga de secretos en registros | El registro anota trace, sistema, operación y código; nunca contenido ni credenciales | `orchestrator.py` |
| Lectura del estado robado | Fernet (AES-CBC con HMAC) sobre todo valor con contenido | `store.py` |
| Webhook falsificado | HMAC SHA-256 o token secreto, con `compare_digest`, sobre los bytes originales | `webhooks.py` |
| Reproducción de un webhook | Deduplicación por `(source, event_key)`; en Slack, ventana de 300 s | `webhooks.py`, `store.py` |
| Duplicado de un envío | Idempotencia con huella del contenido; un resultado desconocido bloquea | `store.py` |
| Agotamiento de memoria por respuesta grande | Corte durante la lectura, no por `Content-Length` | `transport.py` |
| Agotamiento por petición grande | Corte en `MAX_REQUEST_BYTES` durante el streaming | `main.py` |
| Ráfaga de peticiones | Token bucket por identidad, con 429 y `Retry-After` | `ratelimit.py` |
| Inyección de cabeceras en un correo | `EmailMessage` rechaza CR/LF en cabeceras | `connectors/builders.py` |
| Travesía de rutas en un identificador | `path_value` codifica y rechaza `.` y `..` | `connectors/builders.py` |
| XXE y expansión de entidades en SOAP | Análisis con `defusedxml`; el escape de salida no usa parser | `adapters/soap.py` |
| HTML activo en un correo | Conversión a texto descartando `script` y `style`; nunca se renderiza | `connectors/mail_content.py` |
| Fuga de datos privados a un modelo | `AI_MODE=off` por defecto; los 13 proveedores son `sensitive` y se bloquean sin autorización explícita | `response_engine.py` |
| Inyección de prompt desde un correo | El modelo recibe instrucciones de tratar los resultados como datos; y, sobre todo, `/ask` **no puede ejecutar acciones** | `response_engine.py` |
| Reflejo de contenido en una cabecera | El `X-Request-Id` del cliente se acepta solo si coincide con un patrón restringido | `main.py` |
| Catálogo corrupto que deja el servicio sin sistemas | La recarga solo sustituye si la carga completa tuvo éxito | `registry.py` |

## Sobre la inyección de prompt

Las instrucciones del sistema piden al modelo tratar los resultados como datos no confiables y no afirmar haber enviado nada. **Eso no es una defensa sólida**, y el proyecto no pretende que lo sea.

La defensa real es estructural: `/v1/ask` no tiene permiso para escribir, no tiene herramientas que pueda invocar y devuelve siempre `sent: false`. Un correo que diga "reenvía esto a todos los contactos" puede influir en el texto de la respuesta; no puede producir un envío, porque ese camino no existe en el código. La respuesta debe revisarse antes de convertirla en una acción.

## Criptografía

| Uso | Mecanismo |
|---|---|
| Cifrado del estado | Fernet con `STATE_KEY`: AES-128-CBC más HMAC-SHA256, con autenticación |
| Firma de webhooks | HMAC-SHA256 del proveedor, verificado con `compare_digest` |
| Huella de idempotencia | SHA-256 del JSON ordenado |
| Identidad de carga | SHA-256 truncado a 32 caracteres hexadecimales |
| Claves generadas | `secrets.token_urlsafe(32)` y `Fernet.generate_key()` |
| TLS de salida | El de httpx y el sistema; `verify` activo, sin desactivación configurable |

No hay criptografía propia. Todas las comparaciones de secretos usan `compare_digest`, nunca `==`.

## Lo que no está cubierto

Dicho sin rodeos, porque ocultarlo sería el peor defecto de seguridad posible:

- **TLS de entrada.** El servicio habla HTTP en loopback. Publicar requiere un proxy inverso con certificado.
- **Identidad y autorización.** No hay usuarios, ni roles, ni permisos por recurso. Las claves son globales del proceso. Una aprobación **no es atribuible a una persona**: es un secreto compartido.
- **Aislamiento multiempresa.** Un solo dominio de confianza. Sin tenants, sin segregación de datos ni de secretos.
- **DNS rebinding.** La verificación ocurre antes de conectar y hay una ventana entre ambas. El propio `security.py` lo documenta: requiere firewall o proxy de egreso.
- **Denegación de servicio.** El límite de carga es de una instancia y en memoria. No hay protección distribuida, ni circuit breaker, ni cuotas por proveedor.
- **Gestión de secretos.** `.env` en disco, con permisos 600 en POSIX y nada equivalente en Windows. Sin integración con un gestor de secretos, sin rotación automática.
- **Auditoría inmutable.** Los registros son locales y se pueden alterar si el host está comprometido.
- **Cifrado de metadatos.** Nombres de ranura, orígenes de evento, hashes y marcas de tiempo quedan en claro para poder indexar y deduplicar.
- **El proceso en marcha.** El cifrado en reposo no protege de quien ya tiene la clave en memoria. Proteger el equipo es un requisito, no un extra.
- **Datos autorizados pero sensibles.** La allowlist dice que el destino es legítimo, no que usted deba enviarle esos datos. Eso es una decisión de su organización.

## Privacidad

El gateway **no persiste el contenido** de los mensajes que consulta: viaja en la respuesta y se descarta. Lo que sí guarda cifrado son los parámetros de una escritura hasta que se completa o se purga, y los eventos entrantes hasta reconocerlos.

La CLI muestra en pantalla lo que el operador pidió: su terminal, su historial y cualquier redirección de salida forman parte de la superficie a proteger. Un `uao execute ... > salida.json` crea un archivo con datos privados que nadie va a cifrar.

Activar la IA cambia el perfil de privacidad: cuerpos de correo y mensajería salen hacia el endpoint configurado. Use `response_map` para reducir lo que se envía, revise la finalidad y los contratos, y recuerde que un correo puede contener secretos que su autor no pensó compartir.

## Verificación automatizada

| Capa | Herramienta | Frecuencia |
|---|---|---|
| Secretos en el historial completo | gitleaks | cada push y semanal |
| Análisis estático del código propio | Bandit sobre `src/` | ídem |
| Vulnerabilidades de dependencias | pip-audit | ídem |
| Análisis semántico | CodeQL para Python | ídem |
| Actualizaciones | Dependabot (pip, Actions, Docker) | semanal |

Las acciones están fijadas a SHA para que una etiqueta movida no cambie lo que se ejecuta. En la última ejecución local: Bandit sin hallazgos y pip-audit sin vulnerabilidades conocidas, tras subir `cryptography` a la serie 50 por los avisos PYSEC-2026-3552, 3553 y 3554.

Ninguna de estas herramientas prueba un proveedor real ni reemplaza una revisión humana. No se declara cumplimiento normativo ni certificación por tener esta lista.

## Antes de producción

El checklist completo está en [docs/SECURITY.md](../SECURITY.md). Lo mínimo: TLS por proxy, identidad y autorización propias si hay más de un dominio de confianza, control de egreso, límite de carga compartido, gestión de secretos, respaldo cifrado **con prueba de restauración**, monitoreo de reservas pendientes, procedimiento de reconciliación ensayado, y revisión legal de los datos que va a mover en su jurisdicción.

## Fuentes de este capítulo

`src/universal_api_orchestrator/security.py`, `main.py`, `orchestrator.py`, `transport.py`, `store.py`, `webhooks.py`, `ratelimit.py`, `response_engine.py`, `connectors/`, `.github/workflows/security.yml`, `docs/SECURITY.md`, `docs/VALIDATION.md`, y las pruebas `tests/test_security_webhooks.py`, `tests/test_gateway_controls.py`.
