# 12 · Pruebas y calidad

## Qué hay

**162 casos de prueba en 67 funciones, repartidos en 13 archivos.** Todos se ejecutan sin red, sin credenciales y sin contactar a ningún proveedor. Cobertura de líneas del paquete: **76,4 %**.

```bash
python -m pytest -q                              # 162 pasaron
python -m pytest --cov=universal_api_orchestrator # con cobertura
python -m ruff check src tests tools scripts     # sin hallazgos
python scripts/verify_repository.py              # ok: true
python scripts/demo_offline.py                   # suite simulada
```

## Mapa de pruebas

| Archivo | Casos | Qué fija |
|---|---:|---|
| `test_connectors.py` | 92 | Constructores de cada operación del catálogo y validación de los 18 ejemplos JSON contra su esquema, ambos parametrizados; MIME de Gmail de ida y rechazo de inyección en cabeceras. |
| `test_security_webhooks.py` | 17 | Rechazo de endpoints inseguros (cinco casos), bloqueo de direcciones no globales (cinco), cabeceras prohibidas, firmas de Meta y GitHub, ventana de Slack y token de Telegram. |
| `test_orchestrator_api.py` | 8 | Las cuatro condiciones de escritura, repetición idempotente, `ask` sin escritura, alias únicos, salud, autenticación, límite de tamaño, ida y vuelta HTTP, OpenAPI, webhook firmado con duplicado y reconocimiento, y bloqueo de datos sensibles hacia un modelo. |
| `test_gateway_controls.py` | 8 | Token bucket y su desalojo, identidad que no guarda la clave, 429 con `Retry-After`, `/health` exento, identidad de petición saneada, errores de catálogo precisos, ficha de sistema, stats y recarga que conserva el catálogo anterior. |
| `test_transport.py` | 7 | Reintento de lectura con `Retry-After`, ausencia de reintento en escritura, rechazo de redirección, límite de respuesta, timeout por operación acotado y reutilización y cierre del pool. |
| `test_storage_auth.py` | 7 | Cifrado del estado, conflicto de idempotencia, deduplicación del inbox, purga, refresco OAuth con caché y bloqueo, y credenciales ausentes. |
| `test_adapters_extended.py` | 7 | GraphQL con `errors`, envelope de JSON-RPC, `Fault` de SOAP, `ok:false` de Slack y Telegram, y gRPC sin el extra instalado. |
| `test_mail_content.py` | 6 | Árbol MIME, `raw`, charset declarado, HTML a texto, truncado y reducción de evidencia para un modelo. |
| `test_reconciliation.py` | 5 | Reserva inspeccionable, liberación que permite reintento, reservas completadas intocables, exigencia de aprobación y de resultado declarado, y purga que preserva lo pendiente. |
| `test_repository_tools.py` | 3 | Bootstrap idempotente que no imprime claves, negativa a reemplazar una clave con base existente, e importador de OpenAPI deshabilitado. |
| `test_registry.py` | 1 | Carga del catálogo y listado público. |
| `test_normalizer.py` | 1 | Selección con JMESPath. |
| `conftest.py` | — | Fixtures `store` y `app_settings` con claves efímeras y estado en `tmp_path`. |

## Cómo se prueba sin red

Tres mecanismos:

1. **`httpx.MockTransport`.** Se instala un cliente simulado en el pool compartido (`transport._client`) y se retira al terminar la prueba. El manejador decide la respuesta, lo que permite probar reintentos, redirecciones y respuestas enormes de forma determinista.
2. **Monkeypatch del adaptador.** Para probar política e idempotencia se sustituye `RestAdapter.execute` por una función que cuenta llamadas. Así una prueba puede afirmar *no se llamó al proveedor*, que es lo que importa en un rechazo.
3. **Parcheo explícito de la defensa de salida.** `assert_safe_endpoint` se neutraliza **solo** en las pruebas de transporte, donde el destino simulado no resuelve. Las pruebas de seguridad la ejercitan de verdad.

Las claves y la base de datos son efímeras: `Fernet.generate_key()` y `tmp_path` por prueba. Ninguna prueba deja estado.

## Qué se prueba de verdad

Los recuentos de la tabla son casos recogidos por pytest, no funciones: `test_connectors.py` tiene siete funciones y 92 casos porque recorre el catálogo y los ejemplos con `parametrize`.

Las pruebas no se limitan al camino correcto. Una parte grande de los casos comprueba un **rechazo**: que una escritura sin aprobación no llame al proveedor, que una redirección sea un error, que un webhook con firma inválida no toque la base, que una cabecera prohibida se rechace, que un dato sensible no salga hacia un modelo.

En un gateway que puede enviar mensajes, esa es la parte que importa. Dos ejemplos:

```python
r = await engine.execute("test", "write", {}, confirmed=True, idempotency_key="key-1", approved=True)
assert not r.ok and not calls          # allow_writes era False: no se llamó al proveedor
```

```python
r = await engine.execute("test", "write", ..., read_only=True)
assert r.error == "ASK_IS_READ_ONLY"   # con aprobación válida, igual se rechaza
```

## Comprobación del servicio en ejecución

Además de la suite, en esta entrega se arrancó **uvicorn real en loopback** con claves efímeras y 23 comprobaciones de contrato y política: cabeceras de seguridad, catálogo sin clave, errores de catálogo, política de escritura, rechazo en `ask`, reconciliación y recarga con y sin aprobación, y el límite de carga disparando 429. Evidencia en [runtime-smoke.json](../validation-results/runtime-smoke.json). Ese smoke test está diseñado para no salir de loopback.

## El verificador del repositorio

`scripts/verify_repository.py` es una prueba de coherencia, no de código. Comprueba:

- Sintaxis de todo `.py`, `.json`, `.yml` y `.yaml`.
- `allowed_hosts` presente en cada sistema y `effect` válido en cada operación.
- Que cada `input_schema` sea un JSON Schema válido.
- Que cada ejemplo de `examples/requests` valide contra el esquema de su operación, y que las escrituras de ejemplo lleven `confirmed:false`.
- Que todos los enlaces Markdown relativos apunten a archivos existentes.
- Que la versión coincida en `pyproject.toml`, `__init__.py`, `config/catalog.json` y el título del README; y que los recuentos de proveedores y operaciones del catálogo coincidan con `catalog.json`.
- Que ningún Markdown tenga señales de UTF-8 leído como ANSI, excluyendo el código entre comillas invertidas.
- Que ningún archivo enlazado desde la documentación esté excluido por `.gitignore`. Sin git disponible, la comprobación se omite.

Tres de esas comprobaciones existen porque el fallo ocurrió: los recuentos se desincronizaron de la implementación, un archivo se corrompió al editarlo con PowerShell, y un archivo de evidencia enlazado desde `VALIDATION.md` quedó fuera del repositorio por un patrón de `.gitignore` demasiado amplio. Ese último lo encontró la CI en la primera publicación, cuando el verificador aún solo miraba el disco.

## Integración continua

| Job | Qué hace |
|---|---|
| `test` | Matriz de 9 combinaciones: Linux, Windows y macOS por Python 3.11, 3.12 y 3.13. Lint, suite con cobertura y verificador; sube los resultados como artefactos. |
| `package` | Construye las distribuciones, instala el wheel en un directorio limpio y ejecuta `uao catalog` y `uao doctor` sin credenciales. |
| `docs` | markdownlint-cli2 sobre los 59 documentos, con la configuración del repositorio. |
| `container` | Construye la imagen, la arranca con claves efímeras y comprueba `/health` dentro del contenedor. |
| `secrets` | gitleaks sobre el historial completo. |
| `python-security` | Bandit sobre `src/` y pip-audit sobre las dependencias. |
| `codeql` | Análisis semántico de Python. |

Las acciones están fijadas a SHA con la versión en un comentario. `fail-fast: false` en la matriz: un fallo en una combinación no oculta el resto.

## Qué no está cubierto

El 23,6 % de líneas sin ejecutar no es azar; se concentra en lo que no se puede probar sin credenciales ni servicios reales:

| Área | Por qué |
|---|---|
| Consentimiento OAuth interactivo | Abre un navegador y requiere una cuenta real. |
| Device code flow de Microsoft | Ídem, con un código que alguien debe pegar. |
| gRPC contra un servicio real | Requiere el extra y stubs generados de un contrato concreto. |
| Caminos de MSAL con varias cuentas | Dependen del estado de una caché real. |
| Condiciones de carrera reales en SQLite | Se prueba la lógica de `reserve`, no una carrera bajo carga. |
| Comportamiento real de cada proveedor | Formato aceptado, cuotas, plantillas aprobadas, estados de entrega. |

Y lo que ninguna prueba de este repositorio puede afirmar: **que un mensaje llegue a su destinatario**. Eso se verifica con una cuenta autorizada, y la ficha para registrarlo está en [VALIDATION](../VALIDATION.md).

## Añadir una prueba

Convenciones del proyecto: `pytest` con `asyncio_mode=auto` (las corrutinas no necesitan decorador); nombres descriptivos en español que digan qué se garantiza (`test_write_requires_all_gates_and_replay`); estado en `tmp_path` y claves efímeras; `parametrize` para familias de casos; y, en un arreglo de defecto, **una prueba que falle antes del cambio**.

Lo que no se acepta: pruebas que necesiten red, que usen cuentas reales, que incluyan correos privados en un snapshot, o que se desactiven para ocultar un fallo. Está en [CONTRIBUTING](../../CONTRIBUTING.md) y en [AGENTS](../../AGENTS.md).

## Fuentes de este capítulo

Los 13 archivos de `tests/`, `pyproject.toml` (configuración de pytest y ruff), `scripts/verify_repository.py`, `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `docs/validation-results/`.
