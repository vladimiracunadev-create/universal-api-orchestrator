# Migración de 0.2 a 0.3

**Resumen: no hay cambios de ruptura.** Todo lo del contrato HTTP es aditivo y los clientes de 0.2 siguen funcionando sin tocarlos. Lo único que puede sorprender es el límite de carga, activo por defecto, y los códigos de error de catálogo, ahora más precisos.

## Actualizar

```bash
git pull
python -m pip install -e ".[auth,dev]"
python scripts/bootstrap.py      # conserva las claves existentes
python -m pytest -q
python scripts/verify_repository.py
```

No borre `data/` ni rote `STATE_KEY`: el esquema de SQLite es compatible y las tablas existentes se conservan. Al abrir la base se activan WAL y los índices nuevos; no hay migración manual ni script que ejecutar.

## Lo que debe revisar

### 1. Límite de carga activo por defecto

Nuevo: 120 peticiones por minuto con ráfaga de 30, por clave de llamada. Si su cliente hace más, recibirá `429` con `Retry-After`.

```dotenv
RATE_LIMIT_PER_MINUTE=120   # ajuste al tráfico real; 0 lo desactiva
RATE_LIMIT_BURST=30
```

`/health` queda fuera del control. Si tiene un cliente que itera sin pausa, ajuste el valor antes de actualizar en lugar de descubrirlo en marcha.

### 2. Códigos de error de catálogo más precisos

Donde 0.2 devolvía `INVALID_OPERATION_CONFIGURATION_OR_INPUT` con 400 para cualquier problema de catálogo, 0.3 distingue:

| Situación | 0.2 | 0.3 |
|---|---|---|
| El sistema no existe | `INVALID_OPERATION_CONFIGURATION_OR_INPUT` (400) | `SYSTEM_NOT_FOUND` (404) |
| El sistema está deshabilitado | igual que arriba | `SYSTEM_DISABLED` (409) |
| La operación no existe | igual que arriba | `OPERATION_NOT_FOUND` (404) |
| Falta una variable del catálogo | igual que arriba | `SYSTEM_CONFIGURATION_INCOMPLETE` (503) |

Ese `status_code` viaja dentro del sobre unificado, no en el HTTP externo. Si su código compara el texto exacto del error, actualícelo. El código genérico sigue existiendo para el resto de los casos de entrada inválida.

### 3. `uao enable` ya no obliga a reiniciar

```bash
uao enable gmail
uao reload        # nuevo
```

El mensaje de `enable` ahora lo recuerda. Reiniciar el proceso sigue funcionando igual.

### 4. `cryptography` sube a la serie 50

El rango anterior (`>=43,<49`) permitía versiones con avisos publicados (PYSEC-2026-3552, 3553 y 3554). Ahora es `>=50,<51`. Si su entorno fija esa dependencia por otro motivo, resuélvalo antes de instalar.

## Lo que gana sin hacer nada

- **Pool HTTP compartido.** Se elimina un handshake TLS por operación. En consultas seguidas al mismo proveedor la diferencia es apreciable; no cambia ninguna respuesta.
- **SQLite con WAL.** Leer el inbox ya no espera a una escritura en curso.
- **`X-Request-Id` en toda respuesta**, más `Referrer-Policy: no-referrer`. Si envía su propio identificador con formato seguro, se reutiliza.
- **`meta.reservation_id`** en una escritura que falla tras reservar: ya no hay que adivinar qué reconciliar.
- **Catálogo malformado** con un error legible en lugar de `AttributeError`.

## Capacidades nuevas, opcionales

| Capacidad | Endpoint o comando | Notas |
|---|---|---|
| Reconciliar escrituras en duda | `GET /v1/reconciliation`, `POST /v1/reconciliation/{id}/release`, `uao pending`, `uao release` | Requiere clave de aprobación y confirmación explícita. Ver [RECONCILIATION](RECONCILIATION.md). |
| Ficha de un sistema | `GET /v1/systems/{system}` | Sin credenciales ni URL internas. |
| Recuentos del estado | `GET /v1/stats`, `uao stats` | No consulta proveedores. |
| Recarga de catálogo | `POST /v1/admin/reload`, `uao reload` | Un YAML inválido deja el anterior en uso. |
| Purga de reservas completadas | `uao prune-requests --days N` | Nunca toca una reserva pendiente. |
| Estado del proceso desde la CLI | `uao health` | No necesita clave. |
| Tiempo por operación | `timeout_seconds` en el catálogo | Acotado entre 0,5 y 120 segundos. |

## Lo que no cambió a propósito

Las cuatro condiciones para escribir. La ausencia de reintento automático de escrituras. El bloqueo de redes privadas y la prohibición de redirecciones. La verificación de firma de webhooks sobre los bytes originales antes de deserializar. El modo de IA apagado y el rechazo de datos sensibles sin autorización explícita. El arranque sin llamadas externas. Los 13 proveedores y las 69 operaciones: esta versión no añade cobertura de proveedor.

## Si viene de 0.1

Lea primero [MIGRATION_0_1_TO_0_2](MIGRATION_0_1_TO_0_2.md): ahí sí hay cambios de ruptura (autenticación obligatoria, política de escrituras y webhooks firmados).
