# Estado del repositorio

Foto verificable de la entrega **v0.3.0**, con fecha **12 de noviembre de 2026**. Cada cifra sale de un comando que se puede repetir; la columna "cómo comprobarlo" dice cuál. Si un número y el código dejan de coincidir, `python scripts/verify_repository.py` falla.

## Recuentos

| Qué | Cuánto | Cómo comprobarlo |
|---|---|---|
| Versión | 0.3.0 | `uao doctor`, `GET /health`, `pyproject.toml`, `config/catalog.json` |
| Conectores de proveedor | 13 | `python scripts/verify_repository.py` → `providers` |
| Operaciones de proveedor | 69 | el mismo comando → `provider_operations` |
| Sistemas en el catálogo | 18 (13 proveedores + 5 ejemplos de protocolo) | `uao catalog`, `GET /v1/stats` → `systems` |
| Ejemplos de petición | 18 | `verify_repository.py` → `request_examples` |
| Rutas HTTP publicadas | 13 | `GET /openapi.json` |
| Protocolos de transporte | 5 (REST, GraphQL, JSON-RPC, SOAP, gRPC) | `src/universal_api_orchestrator/adapters/` |
| Módulos del paquete | 27 archivos, 1.630 líneas | `src/` |
| Pruebas | 162 casos en 67 funciones, 13 archivos | `python -m pytest -q` |
| Cobertura de líneas | 76,4 % | `python -m pytest --cov=universal_api_orchestrator` |
| Documentos Markdown | 61 | `docs/README.md` enumera los principales |
| Catálogo declarativo | 1.493 líneas de YAML | `config/systems.yaml` |
| Workflows de CI | 2 (CI y Security), 7 jobs | `.github/workflows/` |
| Versiones de Python probadas en CI | 3.11, 3.12 y 3.13, en Linux, Windows y macOS | `.github/workflows/ci.yml` |

## Calidad en la última ejecución

| Comprobación | Herramienta | Resultado |
|---|---|---|
| Pruebas | pytest 9.2.0 | 162 pasaron, 0 fallos |
| Lint | ruff 0.17.5 | sin hallazgos |
| Análisis estático de seguridad | bandit 1.9.4 | sin hallazgos |
| Dependencias | pip-audit 2.10.1 | sin vulnerabilidades conocidas |
| Coherencia del repositorio | `verify_repository.py` | `ok: true` |
| Servicio en ejecución | uvicorn real en loopback | 23 comprobaciones de contrato y política |

Entorno de esa ejecución: Windows 11, Python 3.12.9. El detalle, la evidencia y las versiones exactas están en [VALIDATION](docs/VALIDATION.md).

## Qué está implementado y probado offline

Las 69 operaciones con sus constructores y esquemas. Los cinco adaptadores de protocolo. OAuth con refresco y caché MSAL, con transporte simulado. Cifrado del estado con Fernet. Las cuatro condiciones de escritura. Idempotencia con huella de contenido, conflicto y reserva pendiente. Reconciliación y liberación explícita de reservas. Webhooks firmados de cuatro proveedores, con deduplicación e inbox. Composición determinista con fuentes y bloqueo de datos sensibles hacia un modelo. Defensa de salida completa. Control de carga local. Recarga de catálogo en caliente. CLI con 18 comandos.

## Qué está como guía, no como ejecución verificada

Docker y Compose, Dev Container, macOS, Linux, WSL, despliegue en VPS o nube, y proxy inverso con TLS. Hay archivos y procedimientos revisados; en esta entrega no se ejecutaron en esos sistemas. La CI sí los define, y su resultado se lee en la pestaña Actions del repositorio.

## Qué no está verificado con cuentas reales

**Ninguna operación de esta entrega se ejecutó contra un proveedor real.** No se enviaron mensajes ni correos, no se recibieron eventos externos y no se completó un consentimiento OAuth interactivo. El adaptador gRPC no se ejercitó contra un servicio con stubs generados. El procedimiento para registrar esa aceptación, proveedor por proveedor, está en [VALIDATION](docs/VALIDATION.md).

## Qué no existe en esta versión

SSO, RBAC, aislamiento multitenant, workers distribuidos, cola durable, límite de carga compartido entre réplicas, métricas en formato de scraping, motor de workflows, panel de administración y reintento automático de escrituras. No son defectos: son límites declarados, con su justificación en el [ROADMAP](ROADMAP.md) y en el checklist de [SECURITY](docs/SECURITY.md).

## Cómo reproducir esta foto

```bash
python -m pip install -e ".[auth,dev]"
python -m pytest -q --cov=universal_api_orchestrator
python -m ruff check src tests tools scripts
python scripts/verify_repository.py
python scripts/demo_offline.py
```

Ninguno de esos comandos contacta a un proveedor, necesita una cuenta ni envía nada.
