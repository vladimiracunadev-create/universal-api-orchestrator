# Migrar desde v0.1

## Respaldo y decisión de despliegue

Conserve el ZIP anterior, catálogo personalizado y configuración privada fuera de Git. La v0.2 modifica controles de seguridad y requiere revisión de clientes. No sustituya silenciosamente un servidor que tenga integraciones activas.

Las rutas `/health`, `/v1/systems`, `/v1/execute`, `/v1/batch` y `/v1/ask` se conservan. La forma básica `system/operation/params` continúa. **Esto no implica compatibilidad completa sin cambios:** ahora se exige autenticación y las escrituras se bloquean por defecto.

## Cambios obligatorios

Genere claves con `scripts/bootstrap.py`, configure STATE_KEY y un directorio durable. El script preserva valores existentes y no rota automáticamente la clave de una base ya creada. Añada X-API-Key a clientes; use clave de aprobación únicamente donde deba permitirse modificar.

Revise cada operación de su YAML y declare `effect:read` o `write`. Un POST sin clasificación no se considera consulta por defecto. Asigne schema, allowlist explícita y credenciales; no pase Authorization arbitrario desde el cliente.

El antiguo webhook genérico sin verificación de proveedor fue reemplazado por verificadores específicos. Migre cada callback y su secreto/firmas. No mantenga un endpoint inseguro solo para evitar cambiar el emisor.

`/ask` nunca escribe. Separe cualquier workflow anterior que mezclara consulta y mutación. La composición opcional con IA ahora bloquea datos sensibles salvo habilitación explícita.

## Protocolos y salidas

Los adaptadores se conservan, con controles de red más estrictos y errores reducidos. La validación DNS falla cerrada y no se siguen redirecciones. Configuraciones que dependían de hosts privados necesitan permiso explícito, allowlists y control de egress.

gRPC exige TLS por defecto; un servicio local inseguro debe habilitarse deliberadamente para desarrollo. La respuesta binaria se representa en base64 para no asumir UTF-8. Revise consumidores que dependían de la representación anterior.

El importador OpenAPI genera sistemas deshabilitados y clasifica verbos de forma inicial; requiere revisión manual, como antes, para cuerpos y autenticación.

## Prueba de aceptación

Ejecute tests y verificador. Después pruebe un sistema de lectura real, valide secretos no expuestos y pruebe una escritura autorizada con repetición idempotente. Verifique un webhook real y su deduplicación cuando corresponda. Active producción únicamente tras registrar resultados, permisos y un procedimiento de restauración.

Las copias históricas del [README anterior](history/README_v0.1.md) y [roadmap anterior](history/ROADMAP_v0.1.md) quedan como referencia; sus comandos no se recomiendan para v0.2.
