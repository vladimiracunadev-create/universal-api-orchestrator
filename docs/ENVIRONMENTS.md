# Entornos técnicos y despliegue

## Requisitos comunes

Python 3.11 o superior; se recomienda utilizar una versión incluida en la matriz de CI (3.11, 3.12 o 3.13) y un entorno virtual independiente. Conectividad HTTPS y DNS para llamadas reales; los tests no la requieren. Ejecute comandos desde la raíz del repositorio. La configuración y el estado usan rutas relativas a esa carpeta salvo que las sobrescriba.

`python -m pip install -e ".[auth,dev]"` instala el núcleo, herramientas de OAuth Google/Microsoft y tests. Para servicio sin herramientas de desarrollo: `python -m pip install ".[auth]"`. gRPC es opcional: `python -m pip install -e ".[grpc]"`. No se necesita GPU, CUDA, entrenamiento ni un modelo para consultar APIs.

Los rangos de dependencias están en `pyproject.toml`; no se afirma que constituyan un lock completo. Para una liberación empresarial, genere y audite un lock con las versiones resueltas de su entorno, repita CI y conserve el artefacto de despliegue.

## macOS, incluido Apple Silicon

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py
uao doctor
uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

No se obliga a emular x86. El servicio Python no usa instrucciones específicas de Intel. Los wheels que instale pip deben corresponder a su versión de Python y arquitectura. El Mac mini puede actuar como backend local mientras esté encendido; no se convierte por eso en un servidor público disponible permanentemente.

## Windows 11: PowerShell sin activar scripts

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[auth,dev]"
.\.venv\Scripts\python.exe scripts\bootstrap.py
.\.venv\Scripts\uao.exe doctor
.\.venv\Scripts\python.exe -m uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --no-access-log
```

Se utiliza el ejecutable dentro de `.venv`; no hace falta permitir globalmente scripts no firmados. Para OAuth desde otra terminal, sustituya `uao` por `.\.venv\Scripts\uao.exe`. Proteja `.env` y `data` con permisos de su usuario de Windows y evite carpetas sincronizadas públicamente.

## Linux y WSL2

Use la secuencia macOS/Linux. En WSL mantenga el proyecto preferentemente dentro de su sistema de archivos Linux. Si el navegador abre en Windows y el OAuth loopback no retorna a WSL, realice la autorización en el mismo entorno que ejecuta el servidor o revise el reenvío local del puerto 8765. No convierta el callback OAuth en un endpoint público para resolver ese problema.

Para un servicio administrado, configure directorio de trabajo, usuario no privilegiado, entorno de secretos y disco persistente. Ejemplo de unidad, **plantilla que debe adaptar**:

```ini
[Unit]
Description=Universal API Orchestrator
After=network-online.target
[Service]
User=uao
WorkingDirectory=/opt/uao
EnvironmentFile=/etc/uao/uao.env
ExecStart=/opt/uao/.venv/bin/uvicorn universal_api_orchestrator.main:app --host 127.0.0.1 --port 8080 --workers 1 --no-access-log
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
```

Cree el usuario, carpetas y permisos antes de instalar esa unidad; no se crea por ejecutar el README. Mantenga `.env` fuera de un directorio web.

## Docker / Compose

Prepare primero las claves en el host con `python scripts/bootstrap.py`. Ese script anota `LOCAL_UID` y `LOCAL_GID` en Unix para que el contenedor escriba el volumen con el mismo usuario; no despliegue como root. En Windows, Compose utiliza por defecto UID/GID 10001 y Docker Desktop gestiona la carpeta compartida.

```bash
docker compose up --build -d
docker compose logs --tail=100 api
docker compose exec api uao doctor
```

El puerto publicado se limita a `127.0.0.1:8080`. `config/` se monta en solo lectura, `data/` es persistente y `.env` se inyecta como entorno; las claves no se copian a la imagen. Los tokens cifrados de una autorización realizada en el host pueden utilizarse en el contenedor porque se comparte `data/` y la misma `STATE_KEY`.

Autorice Google **en el host**, antes de iniciar/usar el contenedor: el callback de escritorio escucha en el loopback del equipo. No copie un token sin copiar también su contexto de almacenamiento y clave. Microsoft device flow no depende de un callback entrante y puede autorizarse con `docker compose exec api uao auth-microsoft ...`, usando los scopes de la guía.

Si aparece `Permission denied`, revise propietario de `data/`, variables UID/GID y permisos de Docker Desktop. No use `chmod 777` como solución. Si cambia `config/` desde el host, reinicie el contenedor; `uao enable` dentro del contenedor no puede escribir el montaje de solo lectura. Si cambia `.env`, recree el contenedor, no solo reinicie el proceso:

```bash
docker compose up -d --force-recreate
```

La imagen declara un solo worker. No escale réplicas compartiendo este SQLite sobre un disco de red. El perfil multiinstancia requiere otra capa de persistencia y coordinación, no está implementado.

## VS Code Dev Container / entorno remoto

`.devcontainer/devcontainer.json` instala extras de desarrollo y prepara claves. Los puertos 8080 y 8765 deben permanecer privados. La autorización Google puede requerir reenvío local del callback; no se garantiza que todo entorno remoto lo resuelva de la misma forma. Para un primer uso, autorice en el equipo local y transfiera el estado mediante un procedimiento seguro, o desarrolle un flujo web OAuth dedicado con callback registrado.

GitHub Codespaces no es un hosting permanente. Un contenedor de desarrollo y su disco pueden eliminarse; haga respaldo seguro antes de usar credenciales reales. No deje claves en dotfiles de sincronización pública.

## VPS, servidor de empresa y nube

Esta entrega aporta aplicación, Dockerfile, healthcheck y guía; **no incluye Terraform, Helm ni un despliegue validado en AWS/GCP/Azure**.

Use proxy inverso con HTTPS, acceso privado a endpoints operativos, límites de carga, secretos externos y almacenamiento persistente. Publique exclusivamente las rutas webhook necesarias para proveedores externos. `/docs` y `/openapi.json` son públicos en el servidor de aplicación: restrínjalos en el proxy en producción.

En servicios como Cloud Run, ECS o Azure Container Apps, compruebe si el disco es efímero, cómo se montan secretos y cómo se garantiza una sola instancia. La configuración SQLite actual no tolera perder el filesystem entre solicitudes. Migrar tokens, inbox e idempotencia a almacenamiento compartido transaccional es un requisito previo para réplicas o procesos efímeros.

## Redes corporativas

El transporte HTTPX usa `trust_env=False`: no acepta automáticamente proxies definidos por `HTTP_PROXY`/`HTTPS_PROXY`. Para una red que obliga a pasar por un proxy, implemente configuración explícita, validada y documentada en `transport.py`; no desactive TLS. Añada los dominios permitidos al control de salida corporativo. El gateway valida hosts y DNS, pero requiere protección de egress para cubrir el riesgo residual de cambios DNS entre validación y conexión.

## Laboratorio, pruebas y producción

| Entorno | Credenciales | Efectos | Estado |
|---|---|---|---|
| Test offline | Ficticias | Ninguno externo | Temporal por prueba. |
| Desarrollo | Cuentas de prueba autorizadas | Escrituras inicialmente bloqueadas | Disco local protegido. |
| Staging | Aplicación y destinatarios de prueba separados | Aprobación y cuotas controladas | Respaldo y reconciliación ensayados. |
| Producción | Secretos administrados | Autorización por proceso/usuario | Persistencia, monitoreo y plan de recuperación. |

Las APIs remotas no funcionan sin Internet. El inbox ya recibido puede leerse localmente, pero no existe una cola de envíos offline que se reenvíe automáticamente al reconectar: una escritura interrumpida queda como reserva en duda y se cierra a mano con el procedimiento de [reconciliación](RECONCILIATION.md).

El estado y los controles de carga son **por instancia**: SQLite local, locks de OAuth en memoria y un token bucket propio de cada proceso. Dos réplicas detrás de un balanceador comparten el archivo de estado solo si comparten el volumen, y nunca comparten el contador de peticiones. Para un entorno con varias réplicas, ponga el límite en el proxy inverso y lea los límites de escala en [ARCHITECTURE](ARCHITECTURE.md).

## Jupyter / Colab y sesiones efímeras

Puede usar el cliente Python para consultar un gateway privado que ya esté desplegado. No se incluye un notebook ni se presenta Colab como hosting estable para webhooks, tokens o un servicio permanente. Una sesión que se suspende no garantiza recepción continua; no guarde secretos en notebooks compartidos y no monte el inbox de producción en almacenamiento público.

## Qué se validó aquí

Consulte [VALIDATION](VALIDATION.md). En la entrega de v0.3.0 las pruebas, el lint, la auditoría de dependencias y el arranque real del servicio se ejecutaron en **Windows 11 con Python 3.12**; la entrega de v0.2.0 se validó en Linux. Las instrucciones para macOS, contenedores y nube son entregables revisados en código, no ejecuciones realizadas en esos sistemas. La CI está definida para Linux, Windows y macOS con Python 3.11, 3.12 y 3.13, e incluye un job que construye la imagen y comprueba `/health` dentro del contenedor: su resultado se lee en la pestaña Actions, no aquí.

Para la operación continua en cualquiera de estos entornos, el procedimiento está en el [RUNBOOK](RUNBOOK.md).
