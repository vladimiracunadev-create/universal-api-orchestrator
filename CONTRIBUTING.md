# Contribuir

Revise la [arquitectura](docs/ARCHITECTURE.md) y la [matriz de conectores](docs/CONNECTOR_MATRIX.md) antes de añadir un proveedor. Mantenga contratos claros y cambios pequeños, documentados y con pruebas. No elimine funcionalidades ni renombre operaciones sin guía de migración. El idioma del proyecto es el español, en código, comentarios y documentos.

## Antes de abrir un pull request

```bash
python -m pytest -q
python -m ruff check src tests tools scripts
python scripts/verify_repository.py
```

Los tres deben pasar. `verify_repository.py` comprueba sintaxis de Python, JSON y YAML; `allowed_hosts` y `effect` de cada operación; validez de los JSON Schema; que cada ejemplo de petición valide contra su esquema y que las escrituras de ejemplo lleven `confirmed:false`; enlaces Markdown locales; coherencia de versión y recuentos entre `pyproject.toml`, `__init__.py`, `config/catalog.json` y el README; y codificación de los documentos.

Las reglas de lint activas (`E4`, `E9`, `F`, `W`, `I`, `UP`, `B`, `C4`, `RUF`) priorizan errores reales, orden de importaciones y modernización; el proyecto **no** declara una auditoría completa de estilo ni de tipos. No desactive pruebas ni añada `# noqa` para ocultar un fallo: si una regla no corresponde, discútalo en el pull request.

## Pruebas

No incluya credenciales ni datos de producción en fixtures. Los tests ordinarios no deben requerir red ni enviar mensajes: el transporte se simula con `httpx.MockTransport` y el estado se crea en `tmp_path`. Una prueba contra un proveedor real debe ser opt-in, usar una cuenta de prueba autorizada y registrar costos y efectos. Evite snapshots con correos privados.

Un arreglo de defecto llega con una prueba que falla antes del cambio. Una capacidad nueva llega con pruebas del camino correcto y del rechazo: en este proyecto importa tanto lo que se permite como lo que se niega.

## Añadir o cambiar un conector

Siga [ADDING_CONNECTOR](docs/ADDING_CONNECTOR.md). En el mismo cambio actualice la guía del proveedor, el esquema de parámetros, la matriz, el recuento de `config/catalog.json` y el [CHANGELOG](CHANGELOG.md). Compruebe la fuente oficial y anote la fecha en [SOURCES](docs/SOURCES.md): un JSON con el formato correcto no demuestra que el proveedor lo acepte. Registre limitaciones de scopes, tamaño, eventos y paginación en lugar de omitirlas.

Una operación de escritura declara `effect: write` de forma explícita. Nunca marque como `read` algo que modifica datos en el proveedor para saltarse las condiciones de aprobación.

## Documentación

Un cambio de comportamiento sin documentación está incompleto, y una afirmación incorrecta en los documentos se trata como un defecto. Distinga siempre **implementado**, **probado offline**, **guía** y **pendiente**, según la escala de [START_HERE](docs/START_HERE.md). No describa como entregado algo que no se ejecutó.

Mantenga los archivos en UTF-8 sin BOM. En Windows, `Set-Content` de PowerShell puede reescribir un archivo en la codificación del sistema y romper los acentos: edite con un editor configurado en UTF-8 y confirme con `python scripts/verify_repository.py`, que detecta ese daño.

## Commits y ramas

Trabaje en una rama por cambio y describa en el mensaje qué cambia el comportamiento observable, no solo qué archivos tocó. Un commit que mezcla un arreglo, un formateo masivo y una capacidad nueva es difícil de revisar y de revertir.

## Empaquetar

Para generar un ZIP sin estado ni claves: `python scripts/release.py ../universal-api-orchestrator-v0.3.0.zip`. El empaquetador excluye patrones sensibles comunes y escribe un `.sha256` junto al archivo, pero revise el contenido antes de compartirlo: no puede detectar cualquier secreto que alguien haya escrito dentro de un archivo de código.

## Conducta y licencia

Participar implica aceptar el [código de conducta](CODE_OF_CONDUCT.md). Las vulnerabilidades no van a incidencias públicas: siga [SECURITY](SECURITY.md). Sus aportes se publican bajo [MIT](LICENSE); respete las licencias de las dependencias y las condiciones de los servicios de terceros.
