# 18 · Guía para desarrollador nuevo

Qué leer, en qué orden, y los errores que va a cometer antes de que los cometa.

## Primera hora

```bash
git clone <repositorio> && cd universal-api-orchestrator
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\activate
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py
python -m pytest -q
```

Si ve `162 passed`, tiene el proyecto funcionando. **No necesita ninguna cuenta externa** para desarrollar: las pruebas simulan el transporte y el estado se crea en directorios temporales.

Arranque el servidor y mire la documentación interactiva:

```bash
uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
# en otra terminal, con el mismo entorno:
uao doctor
uao catalog | head -40
```

Abra `http://127.0.0.1:8080/docs`. Las 13 rutas están ahí, y `/v1/systems` necesita la clave que `bootstrap.py` puso en su `.env`.

## Primer día: qué leer

En este orden, y nada más:

1. **[Capítulo 01](01-system-overview.md)**, 10 minutos: qué es y qué no hace.
2. **`src/universal_api_orchestrator/main.py`**, 175 líneas: todo el borde HTTP cabe en una lectura.
3. **`src/universal_api_orchestrator/orchestrator.py`**, 109 líneas: el corazón. Lea `execute` dos veces.
4. **[Capítulo 03](03-architecture.md)**: por qué están separadas las capas.
5. **`config/systems.yaml`**, la entrada `gmail`: así se ve un conector real.
6. **`tests/test_orchestrator_api.py`**: las pruebas son la especificación ejecutable de las políticas.

Deje para después: `connectors/builders.py` (solo si va a tocar un proveedor), `auth.py` (solo si toca OAuth) y el [capítulo 06](06-deep-code-explanation.md), que es una referencia, no una lectura lineal.

## El modelo mental en cinco frases

1. Un **catálogo** YAML declara qué sistemas y operaciones existen. Es confiable: lo administra el operador.
2. El **orquestador** valida, decide si puede escribir, obtiene credenciales y llama a un **adaptador**.
3. El adaptador habla el **protocolo**; un **constructor** traduce al contrato concreto del proveedor cuando hace falta.
4. Todo vuelve en el mismo **sobre**: `ok`, `data`, `error`, `meta`.
5. Leer y escribir son caminos distintos. Escribir exige cuatro condiciones a la vez.

## Los siete errores que va a cometer

### 1. Mirar solo el código HTTP

`HTTP 200` con `ok:false` es normal. El gateway procesó la petición; la operación falló. Revise `ok` siempre.

### 2. Pensar que `--approve` confirma

`--approve` añade la cabecera de aprobación. **No** cambia `confirmed` en el JSON. Son dos decisiones independientes, y hacen falta las cuatro condiciones.

### 3. Esperar que `uao enable` tenga efecto inmediato

Escribe en el YAML. El proceso en marcha sigue con el catálogo que cargó. Ejecute `uao reload`.

### 4. Esperar que `uao reload` recargue `.env`

No. Recarga el **catálogo**. Las variables se leen al iniciar: reinicie el proceso.

### 5. Marcar como `read` una operación que escribe

Un POST sin `effect` se considera escritura, a propósito. Si lo declara `read` para "simplificar", se salta las cuatro condiciones y alguien enviará un mensaje sin querer. Solo un POST de consulta real (GraphQL) debe declararlo.

### 6. Añadir un reintento "porque falló"

Las escrituras **no** se reintentan. Si ve `NETWORK_OUTCOME_UNKNOWN`, el sistema no sabe si el mensaje salió, y reintentar puede duplicarlo. El camino correcto es la [reconciliación](../RECONCILIATION.md).

### 7. Cambiar la `idempotency_key` para desbloquear

Un `OUTCOME_PENDING_OR_UNKNOWN_RECONCILE` significa que hay una escritura en duda. Cambiar la clave es la forma de enviar dos veces el mismo mensaje. Compruebe en el proveedor y libere la reserva.

## Su primera tarea: añadir una operación de lectura

El caso más común y el que no necesita código. En `config/systems.yaml`:

```yaml
  mi_servicio:
    enabled: false
    protocol: rest
    base_url: https://api.ejemplo.test
    allowed_hosts: [api.ejemplo.test]
    sensitive: true
    auth:
      type: bearer
      token_env: MI_SERVICIO_TOKEN
    operations:
      get_item:
        method: GET
        path: /items/{id}
        effect: read
        description: Consultar un elemento por identificador.
        timeout_seconds: 10
        input_schema:
          type: object
          properties:
            id: {type: string, minLength: 1, maxLength: 200}
          required: [id]
          additionalProperties: false
        response_map:
          id: id
          name: attributes.name
```

Después:

```bash
python scripts/verify_repository.py   # valida esquema, allowed_hosts y effect
uao catalog                           # ¿aparece?
uao enable mi_servicio && uao reload
```

Cuatro cosas que el verificador le exigirá y conviene saber de antemano: `allowed_hosts` es obligatorio; `effect` debe ser `read` o `write`; el `input_schema` debe ser un JSON Schema válido; y un sistema nuevo nace deshabilitado.

Para un proveedor con contrato propio (MIME, multipart, envelope), necesitará un constructor: siga [ADDING_CONNECTOR](../ADDING_CONNECTOR.md) y mire `builders.gmail` como referencia.

## Cómo escribir una prueba aquí

```python
async def test_la_escritura_no_sale_sin_aprobacion(store, registry, monkeypatch):
    calls = []
    async def execute(*args):
        calls.append(args)
        return 200, {"id": "1"}
    monkeypatch.setattr("universal_api_orchestrator.adapters.rest.RestAdapter.execute", execute)
    monkeypatch.setattr(settings, "allow_writes", False)
    r = await Orchestrator(registry, store).execute(
        "test", "write", {}, confirmed=True, idempotency_key="key-1", approved=True)
    assert not r.ok and not calls      # lo importante: no se llamó al proveedor
```

Tres convenciones: `asyncio_mode=auto`, así que las corrutinas no necesitan decorador; el estado va en `tmp_path` con claves efímeras (fixtures `store` y `app_settings`); y en un rechazo se afirma **que no se llamó al proveedor**, no solo que `ok` es falso.

Un arreglo de defecto llega con una prueba que falla antes del cambio. Una capacidad nueva, con el camino correcto y el rechazo.

## Antes de abrir un pull request

```bash
python -m pytest -q
python -m ruff check src tests tools scripts
python scripts/verify_repository.py
```

Los tres deben pasar, y en la plantilla del pull request se pide **pegar la salida**, no afirmar que pasaron. Actualice en el mismo cambio: documentación del proveedor, esquema, matriz, recuentos de `config/catalog.json` y el `CHANGELOG`. Si cambió el comportamiento sin documentarlo, el cambio está incompleto.

Lo que no se acepta: `# noqa` para silenciar un hallazgo, pruebas desactivadas, credenciales en fixtures, un reformateo masivo mezclado con un cambio funcional, o debilitar la frontera entre leer y escribir. Está en [CONTRIBUTING](../../CONTRIBUTING.md) y [AGENTS](../../AGENTS.md).

## Codificación: una trampa real en Windows

Todos los archivos son UTF-8 sin BOM y la documentación está acentuada. `Set-Content` y `Out-File` de PowerShell pueden reescribir un archivo en la codificación del sistema y convertir `ñ` en `Ã±`. Pasó en este repositorio. `verify_repository.py` detecta ese daño, así que ejecútelo si edita documentación desde PowerShell.

## Dónde buscar cada cosa

| Pregunta | Dónde |
|---|---|
| ¿Qué hace este archivo? | [Capítulo 04](04-code-map.md) |
| ¿Por qué está escrito así? | [Capítulo 06](06-deep-code-explanation.md) |
| ¿Qué devuelve este endpoint? | [Capítulo 05](05-technical-reference.md) o `/docs` |
| ¿Qué significa este error? | [Capítulo 14](14-troubleshooting.md) |
| ¿Qué guarda la base de datos? | [Capítulo 07](07-database.md) |
| ¿Qué variable controla esto? | [Capítulo 10](10-configuration.md) |
| ¿Qué falta por hacer? | [Capítulo 15](15-risks-and-technical-debt.md) |
| ¿Qué significa este término? | [Capítulo 16](16-glossary.md) |

## Una advertencia final

Este proyecto puede enviar mensajes a personas reales. Al tocar `orchestrator.py`, `store.py` o `builders.py`, pregúntese qué pasa si su cambio se equivoca **hacia el lado de enviar**. Las cuatro condiciones, la ausencia de reintento y la reconciliación manual no son burocracia: son las tres cosas que impiden que un error de código se convierta en un mensaje que alguien recibe dos veces.

## Fuentes de este capítulo

`CONTRIBUTING.md`, `AGENTS.md`, `docs/ADDING_CONNECTOR.md`, `tests/conftest.py`, `tests/test_orchestrator_api.py`, `config/systems.yaml`, `scripts/verify_repository.py`, `.github/pull_request_template.md`.
