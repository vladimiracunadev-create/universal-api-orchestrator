# Instalación

Una instalación correcta termina con tres hechos comprobables: `uao doctor` responde, `GET /health` devuelve `ok` y `python -m pytest -q` pasa. Nada de eso prueba que un proveedor esté conectado: eso se verifica proveedor por proveedor con su guía.

## Requisitos

| Requisito | Detalle |
|---|---|
| Python | 3.11, 3.12 o 3.13. El proyecto se prueba en esas tres versiones y en Linux, Windows y macOS. |
| Espacio | Decenas de MB para el entorno virtual y el estado local cifrado. |
| Red de salida | HTTPS hacia los proveedores que active. Sin proveedores activos no hace ninguna llamada externa. |
| Puerto | 8080 en loopback de forma predeterminada. |
| Extras | `auth` para OAuth de Google y Microsoft; `grpc` solo si usará el adaptador gRPC; `dev` para pruebas y lint. |

No se requiere base de datos externa, Redis, cola de mensajes ni cuenta en la nube. No se requiere privilegio de administrador.

## Linux y macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py
uao doctor
```

`bootstrap.py` crea `.env` a partir de `.env.example`, genera `GATEWAY_API_KEY`, `APPROVAL_API_KEY` y `STATE_KEY` con `secrets`/`Fernet`, y crea `data/` y `secrets/`. **No reemplaza una clave existente** y se niega a generar una nueva `STATE_KEY` si ya hay una base de datos: una clave distinta dejaría el estado cifrado ilegible. En sistemas POSIX ajusta los permisos de `.env` a 600 y registra `LOCAL_UID`/`LOCAL_GID` para Compose.

Arranque:

```bash
uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

## Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[auth,dev]"
.\.venv\Scripts\python.exe scripts\bootstrap.py
.\.venv\Scripts\uao.exe doctor
.\.venv\Scripts\python.exe -m uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

Invocar los ejecutables del entorno por ruta completa evita tener que cambiar la política de ejecución. En Windows no se aplican permisos POSIX al archivo `.env` ni a la base de datos: protéjalos con los permisos NTFS de la carpeta. Existe también [`scripts/start.ps1`](scripts/start.ps1).

## Makefile

```bash
make install   # instala extras y ejecuta bootstrap
make test      # pytest -q
make lint      # ruff check
make run       # uvicorn en 127.0.0.1:8080
```

## Contenedor

```bash
cp .env.example .env     # y complete claves con python scripts/bootstrap.py
docker compose up --build
```

La imagen corre como usuario 10001 sin privilegios, sin capacidades y con `no-new-privileges`. Publica el puerto únicamente en `127.0.0.1`. Monta `config/` en solo lectura y `data/` en escritura: si los UID del host y del contenedor no coinciden, SQLite no podrá escribir. `bootstrap.py` escribe `LOCAL_UID`/`LOCAL_GID` en `.env` para ese caso. Detalles en [ENVIRONMENTS](docs/ENVIRONMENTS.md).

## Dev Container

[`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json) instala los extras y deja el entorno listo en VS Code o en un Codespace. Las credenciales de proveedor siguen siendo suyas: no se incluyen en la imagen.

## Variables mínimas

| Variable | Para qué | Si falta |
|---|---|---|
| `GATEWAY_API_KEY` | Autenticar a la aplicación cliente. Mínimo 24 caracteres. | Toda ruta `/v1` responde `503 GATEWAY_KEY_NOT_CONFIGURED`. |
| `APPROVAL_API_KEY` | Aprobar escrituras, reconciliar y recargar. | Esas operaciones responden `403`. |
| `STATE_KEY` | Cifrar tokens, reservas e inbox. | El proceso no arranca. |
| `ALLOW_WRITES` | Habilitar el envío. Predeterminado `false`. | Las escrituras se rechazan con `WRITE_APPROVAL_REQUIRED`. |

El inventario completo está en [`.env.example`](.env.example) y explicado en [CONFIGURATION](docs/system-documentation/10-configuration.md).

## Verificar la instalación

```bash
python -m pytest -q                   # 162 pruebas, sin red
python scripts/verify_repository.py   # coherencia de catálogo, ejemplos, enlaces y versión
python scripts/demo_offline.py        # integración simulada, identificada como simulada
uao health                            # el proceso responde
uao stats                             # recuentos del estado local
```

## Actualizar

```bash
git pull
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py   # conserva las claves existentes
python -m pytest -q
```

No borre `data/` ni rote `STATE_KEY` al actualizar: perdería los tokens cifrados y las reservas de idempotencia. Antes de subir de versión, lea el [CHANGELOG](CHANGELOG.md) y la guía de migración correspondiente.

## Desinstalar

Detenga el proceso, elimine el entorno virtual y borre `data/`, `secrets/` y `.env` si no desea conservar el estado. Revoque además los permisos OAuth concedidos en Google, Microsoft o Meta: eliminar el estado local no revoca un consentimiento remoto.
