# Política de seguridad

Este documento explica **cómo reportar** un problema. El endurecimiento técnico, el modelo de amenazas y el checklist previo a producción están en [docs/SECURITY.md](docs/SECURITY.md).

## Versiones con soporte

| Versión | Estado |
|---|---|
| 0.3.x | Con soporte. Correcciones de seguridad sobre `main`. |
| 0.2.x | Sin soporte. Actualice con [la guía de migración](docs/MIGRATION_0_2_TO_0_3.md); los cambios son aditivos. |
| 0.1.x | Sin soporte. |

## Cómo reportar

Use el aviso privado de GitHub: pestaña **Security → Report a vulnerability** del repositorio. Así el informe no es público mientras se analiza.

Si esa vía no está disponible, abra una incidencia **sin detalles explotables** pidiendo un canal privado. No publique credenciales, volcados de correos, números de teléfono ni capturas con tokens: si su informe los contiene, dígalo y espere el canal privado.

Incluya, en la medida de lo posible: versión y comando exacto, sistema operativo y versión de Python, pasos reproducibles, resultado esperado y resultado observado, y el `trace_id` o `X-Request-Id` si aparece en una respuesta.

## Qué esperar

Es un proyecto mantenido por una persona, no un servicio con guardia. El compromiso es honesto y limitado: acuse de recibo en cuanto se lea el informe, un primer análisis con calificación de impacto, y publicación de la corrección en `main` con entrada en el [CHANGELOG](CHANGELOG.md). No hay programa de recompensas, SLA contractual ni acuerdo de divulgación coordinada previo. Se le dará crédito en el changelog salvo que prefiera lo contrario.

## Dentro del alcance

- Omisión de las cuatro condiciones que autorizan una escritura (`ALLOW_WRITES`, clave de aprobación, `confirmed`, `idempotency_key`).
- Escape de la allowlist de hosts, de la prohibición de redirecciones o del bloqueo de redes privadas (SSRF).
- Aceptación de un webhook con firma inválida, replicación de eventos o cálculo de firma vulnerable a comparación no constante.
- Fuga de credenciales, tokens, URLs firmadas o contenidos de proveedor en respuestas, errores o registros.
- Lectura o manipulación del estado cifrado sin `STATE_KEY`, o inyección SQL en el almacén local.
- Inyección de cabeceras del llamante fuera de la allowlist, inyección CR/LF en cabeceras MIME o de ruta.
- Envío de datos marcados como sensibles a un modelo con `AI_ALLOW_SENSITIVE_DATA=false`.
- Liberación de una reserva de idempotencia sin clave de aprobación o sin confirmación.

## Fuera del alcance

- Falta de TLS, de SSO, de RBAC o de aislamiento multitenant: son limitaciones documentadas de esta versión, no defectos. El README y [docs/SECURITY.md](docs/SECURITY.md) las declaran.
- El límite de carga incluido no se comparte entre réplicas: es un control local declarado como tal.
- Agotamiento de recursos desde un cliente que ya posee la clave del gateway, salvo que amplifique mucho más allá de los límites configurados.
- Vulnerabilidades de dependencias de terceros sin explotación demostrable aquí: repórtelas al proyecto correspondiente y, si procede, abra una incidencia para subir la versión mínima.
- DNS rebinding puro: la verificación de endpoint se hace antes de la petición y el propio código documenta que requiere firewall o proxy de egreso como complemento.
- Resultados de un escáner sin análisis: un hallazgo sin ruta de explotación en este código se cerrará pidiendo el caso concreto.

## Qué no debe hacer

No pruebe contra cuentas, buzones, números o repositorios de terceros. No envíe mensajes reales para demostrar un hallazgo. Una prueba de concepto debe ejecutarse contra su propia instalación y sus propias cuentas de prueba.

## Verificación continua

El workflow [`security.yml`](.github/workflows/security.yml) ejecuta en cada push y cada semana: gitleaks sobre el historial completo, Bandit sobre `src/`, `pip-audit` sobre las dependencias resueltas y CodeQL para Python. Las acciones están fijadas a SHA y Dependabot propone actualizaciones semanales de pip y de GitHub Actions. Ninguna de esas herramientas prueba un proveedor real ni sustituye una revisión humana.
