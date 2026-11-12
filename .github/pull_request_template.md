## Qué cambia

<!-- Describa el comportamiento observable que cambia, no solo los archivos tocados. -->

## Por qué

<!-- Problema que resuelve. Enlace a la incidencia si existe. -->

## Tipo de cambio

- [ ] Corrección de defecto
- [ ] Capacidad nueva
- [ ] Conector nuevo o cambio en un conector existente
- [ ] Documentación
- [ ] Mantenimiento (dependencias, CI, lint)

## Verificación ejecutada

Pegue la salida real, no una afirmación.

- [ ] `python -m pytest -q`
- [ ] `python -m ruff check src tests tools scripts`
- [ ] `python scripts/verify_repository.py`

```text
<!-- salida -->
```

## Frontera entre leer y escribir

- [ ] No debilita `ALLOW_WRITES`, `X-Approval-Key`, `confirmed` ni `idempotency_key`.
- [ ] Ninguna operación que modifica datos queda declarada como `effect: read`.
- [ ] No introduce reintento automático de escrituras ni libera reservas sin decisión humana.
- [ ] Un sistema nuevo nace con `enabled: false`.

## Seguridad y datos

- [ ] No incluye credenciales, tokens, `.env`, contenidos de buzones ni datos personales reales.
- [ ] No relaja la allowlist de hosts, la prohibición de redirecciones ni el bloqueo de redes privadas.
- [ ] No se ejecutó ninguna prueba contra cuentas de terceros.

## Documentación

- [ ] Guía de proveedor, esquema y matriz actualizados si cambió un conector.
- [ ] Entrada en el `CHANGELOG`.
- [ ] Recuentos de `config/catalog.json` y versión coherentes (`verify_repository.py` lo comprueba).

## Qué queda fuera

<!-- Lo que no hace este cambio, y por qué. -->
