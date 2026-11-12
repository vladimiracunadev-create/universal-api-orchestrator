# Para quien evalúa este repositorio

Resumen en una página de qué demuestra este proyecto, con los puntos del código donde comprobarlo.

## Qué es

Un gateway multicanal en Python que unifica el acceso a 13 servicios de correo, mensajería y colaboración (Gmail, Microsoft Graph, WhatsApp Cloud API, Telegram, Slack, Discord, Twilio, SendGrid, Resend, Calendar, Drive, Teams y GitHub) con un solo contrato HTTP, además de adaptadores genéricos REST, GraphQL, JSON-RPC, SOAP y gRPC.

## Qué problema resuelve

Integrar varios proveedores suele acabar en un cliente distinto por API, credenciales repartidas y un envío accidental a producción. Aquí el catálogo es declarativo, los secretos se resuelven en el backend, y enviar exige cuatro condiciones simultáneas en lugar de una variable de entorno.

## Decisiones de diseño que vale la pena mirar

| Decisión | Dónde verla |
|---|---|
| Un catálogo YAML define sistemas y operaciones; añadir un endpoint no requiere código nuevo | `config/systems.yaml`, `src/universal_api_orchestrator/registry.py` |
| La política se aplica antes del transporte y antes de obtener credenciales | `orchestrator.py` |
| Leer y escribir son caminos distintos: `/v1/ask` rechaza toda escritura aunque el operador tenga la clave de aprobación | `orchestrator.py`, `response_engine.py` |
| Idempotencia con huella del contenido; un fallo ambiguo bloquea el reintento y exige reconciliación humana | `store.py`, `docs/RECONCILIATION.md` |
| Defensa de salida: allowlist de hosts, sin redirecciones, bloqueo de IP privadas, cabeceras del llamante filtradas | `security.py`, `transport.py` |
| Webhooks verificados sobre los bytes originales antes de deserializar, con deduplicación por evento | `webhooks.py` |
| Tokens, reservas e inbox cifrados con Fernet en SQLite; WAL para no bloquear lecturas | `store.py` |
| La IA es opcional, está apagada y no recibe datos marcados como sensibles sin autorización explícita | `response_engine.py`, `config.py` |

## Cómo comprobarlo en cinco minutos

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[auth,dev]"
python -m pytest -q                   # 162 pruebas, sin red ni credenciales
python scripts/verify_repository.py    # coherencia de catálogo, ejemplos, enlaces y versión
python scripts/demo_offline.py         # integración simulada
```

No hace falta ninguna cuenta externa: el proyecto arranca y se prueba sin contactar a ningún proveedor.

## Qué no afirma

No es un SaaS multiempresa ni está certificado en producción. No incluye SSO, RBAC, aislamiento multitenant ni workers distribuidos, y el límite de carga incluido vive en memoria de un proceso. Ninguna operación se ha ejecutado contra una cuenta real en esta entrega: eso está declarado en [VALIDATION](docs/VALIDATION.md) y en [STATUS](STATUS.md) en lugar de quedar insinuado.

## Documentación

[README](README.md) para empezar, [ARCHITECTURE](docs/ARCHITECTURE.md) para el recorrido del código, [API_GUIDE](docs/API_GUIDE.md) para el contrato, [SECURITY](docs/SECURITY.md) para el modelo de amenazas y el checklist, y la [documentación de sistema](docs/system-documentation/README.md) para el detalle en 19 capítulos.

Autor: Vladimir Acuña. Licencia MIT.
