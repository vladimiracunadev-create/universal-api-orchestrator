# 02 · Instalación y ejecución

La guía corta para un usuario está en [INSTALL](../../INSTALL.md). Este capítulo explica **qué ocurre** en cada paso y cómo se comporta el proceso en cada entorno.

## Requisitos reales

| Requisito | Detalle | Por qué |
|---|---|---|
| Python 3.11+ | Probado en 3.11, 3.12 y 3.13 | Usa `StrEnum`, uniones con `None` al estilo moderno y `zip(strict=True)` |
| Dependencias | 11 obligatorias, 3 grupos de extras | `pyproject.toml` las fija con rangos superiores cerrados |
| Espacio | Decenas de MB | Entorno virtual más SQLite local |
| Red de salida | HTTPS a los proveedores activados | Sin proveedores activos no hay tráfico externo |
| Puerto | 8080 en loopback | Configurable al arrancar |
| Privilegios | Ninguno especial | No instala servicios ni toca el sistema |

Los extras: `auth` añade `google-auth-oauthlib` y `msal`; `grpc` añade `grpcio` y `protobuf`; `dev` añade pytest, pytest-asyncio, pytest-cov y ruff. Sin `auth` instalado, los flujos de Google y Microsoft fallan con `INSTALL_AUTH_EXTRA` en lugar de un error de importación.

## Instalación paso a paso

```bash
python3 -m venv .venv
source .venv/bin/activate              # Windows: .\.venv\Scripts\activate
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py
```

### Qué hace exactamente `bootstrap.py`

1. Lee `.env` si existe; si no, parte de `.env.example`.
2. Genera `GATEWAY_API_KEY` y `APPROVAL_API_KEY` con `secrets.token_urlsafe(32)`, y `STATE_KEY` con `Fernet.generate_key()`, **solo para las que estén vacías**. Una clave existente nunca se reemplaza.
3. Si falta `STATE_KEY` pero ya hay un archivo de base de datos en `data/`, **aborta** con un mensaje pidiendo restaurar la clave: generar otra dejaría el estado cifrado ilegible.
4. Añade `ALLOW_WRITES=false` si no está declarada.
5. En sistemas POSIX escribe `LOCAL_UID` y `LOCAL_GID` (los usa Compose) y pone `.env` en modo 600.
6. Crea `data/` y `secrets/`.
7. Imprime una confirmación **sin** mostrar ninguna clave.

Es idempotente: ejecutarlo dos veces deja el mismo archivo. Hay pruebas que lo comprueban, incluida la negativa a reemplazar una clave con base existente (`tests/test_repository_tools.py`).

## Arranque

```bash
uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --workers 1 --no-access-log
```

Al arrancar, el ciclo de vida (`lifespan` en `main.py`) construye cuatro objetos y nada más: el registro leyendo el catálogo, el almacén abriendo o creando SQLite, el orquestador y el limitador de carga. **No se contacta a ningún proveedor, no se valida ninguna credencial y no se lee ningún buzón.** Si `STATE_KEY` falta o es inválida, el proceso no arranca: es deliberado, porque sin ella no puede leer su propio estado.

Al apagarse cierra el pool HTTP compartido y devuelve las conexiones. No vacía el estado ni reintenta nada pendiente.

### Por qué un solo worker

El estado está en SQLite local y los locks de refresco OAuth viven en memoria del proceso. Con varios workers sobre el mismo archivo, las reservas de idempotencia se comparten (están en la base) pero los locks no, y el contador de carga pasa a contar por separado en cada uno. Para más capacidad, la respuesta correcta es la del [capítulo 15](15-risks-and-technical-debt.md): un almacén compartido, no más procesos.

## Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[auth,dev]"
.\.venv\Scripts\python.exe scripts\bootstrap.py
.\.venv\Scripts\uao.exe doctor
.\.venv\Scripts\python.exe -m uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

Invocar los ejecutables por ruta completa evita cambiar la política de ejecución de PowerShell. Dos diferencias de comportamiento reales: `bootstrap.py` no aplica permisos 600 a `.env` y `Store` no aplica `chmod 600` a la base de datos, porque `os.chmod` no tiene el mismo significado en Windows. Protéjalos con permisos NTFS de la carpeta.

Cuidado con `Set-Content` y `Out-File` de PowerShell: pueden reescribir un archivo en la codificación del sistema y romper los acentos de la documentación. `verify_repository.py` detecta ese daño.

## Contenedor

```bash
docker compose up --build
```

La imagen parte de `python:3.12-slim`, instala el paquete con el extra `auth`, crea el usuario 10001 y le entrega `/app`. Copia `pyproject.toml`, `README.md`, `LICENSE`, `src` y `config`; **no** copia `data`, `secrets` ni `.env`. Define un `HEALTHCHECK` que pide `/health` con `urllib` cada 30 segundos.

Compose añade `no-new-privileges`, elimina todas las capacidades, publica el puerto solo en `127.0.0.1`, monta `config/` en solo lectura y `data/` en escritura. El punto que suele fallar es el UID: si el usuario del contenedor no coincide con el propietario de `data/` en el host, SQLite no puede escribir. Para eso `bootstrap.py` escribe `LOCAL_UID`/`LOCAL_GID` y Compose los usa en `user:`.

El job `container` de la CI construye la imagen, la arranca con claves efímeras y comprueba `/health` dentro del contenedor.

## Dev Container

`.devcontainer/devcontainer.json` prepara el entorno con los extras instalados para VS Code o Codespaces. Las credenciales de proveedor siguen siendo del usuario: no se incluyen en la imagen ni se heredan del repositorio.

## Comprobar que funciona

```bash
python -m pytest -q                   # 162 pruebas, sin red
python -m ruff check src tests tools scripts
python scripts/verify_repository.py   # coherencia de catálogo, ejemplos, enlaces y versión
python scripts/demo_offline.py        # integración simulada, identificada como simulada
uao doctor                            # claves, política y estado de cada sistema
uao health                            # el proceso responde
```

Qué significa cada resultado:

- `uao doctor` con `config_ready_credentials_not_verified` en un sistema: el entorno está completo. **No** significa que la cuenta funcione; no hay autenticación remota en ese comando.
- `missing_environment`: el catálogo pide una variable que no está en el proceso.
- `disabled`: el sistema está apagado en el catálogo.
- `verify_repository.py` con `ok: true`: catálogo, esquemas, ejemplos, enlaces, versión y codificación coinciden.

## Activar un proveedor

```bash
uao auth-google --client secrets/google-client.json --token-key google \
  --scopes https://www.googleapis.com/auth/gmail.readonly
uao enable gmail
uao reload
uao execute examples/requests/gmail-search.json
```

Empiece siempre por un scope de solo lectura. `enable` modifica el catálogo pero el proceso en marcha sigue con el anterior hasta `uao reload` (o un reinicio). Un cambio en `.env`, en cambio, **sí** requiere reiniciar: las variables se leen al iniciar.

## Actualizar y desinstalar

```bash
git pull
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py     # conserva las claves existentes
python -m pytest -q
```

No borre `data/` ni rote `STATE_KEY` al actualizar. Para desinstalar, detenga el proceso, elimine el entorno virtual y borre `data/`, `secrets/` y `.env` si no desea conservar el estado; después **revoque los permisos OAuth en el proveedor**, porque eliminar el estado local no revoca un consentimiento remoto.

## Fuentes de este capítulo

`INSTALL.md`, `scripts/bootstrap.py`, `scripts/verify_repository.py`, `scripts/demo_offline.py`, `src/universal_api_orchestrator/main.py` (`lifespan`), `src/universal_api_orchestrator/store.py`, `Dockerfile`, `docker-compose.yml`, `.devcontainer/devcontainer.json`, `.github/workflows/ci.yml`, `tests/test_repository_tools.py`.
