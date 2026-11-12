# Instrucciones para agentes de código

Este archivo es para un asistente que trabaje en este repositorio. Las reglas de personas están en [CONTRIBUTING](CONTRIBUTING.md); las de seguridad, en [SECURITY](SECURITY.md).

## Qué es este proyecto

Un gateway que conecta correo y mensajería reales. Una operación mal marcada puede enviar un mensaje a una persona. Por eso el proyecto distingue de forma estricta leer de escribir, y cualquier cambio que afecte esa frontera se revisa con más cuidado que el resto.

## Reglas que no se negocian

1. **No afirme que algo está probado si no lo ejecutó.** Pegue la salida real de `pytest`, `ruff` y `verify_repository.py`. Un cambio "debería funcionar" no se reporta como verificado.
2. **No debilite las cuatro condiciones de escritura** (`ALLOW_WRITES`, `X-Approval-Key`, `confirmed:true`, `idempotency_key`) ni las convierta en una sola. No marque como `effect: read` una operación que modifica datos.
3. **No añada reintento automático de escrituras** ni libere reservas de idempotencia por su cuenta. Una escritura en duda requiere decisión humana: vea [RECONCILIATION](docs/RECONCILIATION.md).
4. **No envíe mensajes reales ni use cuentas reales** para comprobar nada. Las pruebas simulan el transporte con `httpx.MockTransport`.
5. **No escriba secretos en el repositorio.** `.env`, `secrets/`, `data/` y cualquier token quedan fuera. No los pegue en una respuesta, un commit, un comentario ni una prueba.
6. **No relaje los controles de red**: allowlist de hosts, prohibición de redirecciones y bloqueo de direcciones privadas. Si una prueba necesita saltarlos, parchee `assert_safe_endpoint` en el test, no el código de producción.
7. **No verifique una firma de webhook con `==`.** Use `hmac.compare_digest` y valide sobre los bytes originales, antes de deserializar.
8. **No invente contenidos.** `_content` existe solo cuando hay MIME real; un listado de IDs no produce cuerpos de correo.

## Cómo trabajar

- Lea `src/universal_api_orchestrator/orchestrator.py` antes de tocar políticas y `docs/ARCHITECTURE.md` antes de tocar la estructura.
- El estilo del código fuente es denso a propósito en los módulos antiguos. No reformatee archivos completos en un cambio funcional: el diff se vuelve irrevisable.
- Un cambio llega con prueba, documentación y entrada en el [CHANGELOG](CHANGELOG.md), en el mismo commit.
- Añadir un conector se hace por catálogo declarativo (`config/systems.yaml`) siempre que sea posible, no con código nuevo. Siga [ADDING_CONNECTOR](docs/ADDING_CONNECTOR.md).
- Un sistema nuevo nace con `enabled: false`.

## Comandos

```bash
python -m pip install -e ".[auth,dev]"
python -m pytest -q
python -m ruff check src tests tools scripts
python scripts/verify_repository.py
python scripts/demo_offline.py
```

## Codificación

Todos los archivos son UTF-8 sin BOM y la documentación está acentuada. En Windows, `Set-Content` y `Out-File` de PowerShell pueden reescribir un archivo en la codificación del sistema y convertir `ñ` en `Ã±`. Edite con herramientas que respeten UTF-8 y compruebe con `verify_repository.py`, que falla ante ese daño.

## Al terminar

Diga qué ejecutó, qué pasó y qué no pudo comprobar. Si dejó algo fuera del alcance pedido, dígalo explícitamente en lugar de presentarlo como completo.
