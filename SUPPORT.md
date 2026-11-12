# Soporte

## Antes de pedir ayuda

1. Ejecute `uao doctor`: dice si las claves están configuradas, si las escrituras están habilitadas y qué sistemas tienen su entorno completo. **No** verifica una sesión con el proveedor.
2. Ejecute `python scripts/verify_repository.py`: detecta catálogo inválido, ejemplos incoherentes, enlaces rotos y desajustes de versión.
3. Busque el código de error en [TROUBLESHOOTING](docs/TROUBLESHOOTING.md). Los códigos son estables y están documentados uno por uno.
4. Confirme que el sistema está habilitado (`uao catalog`) y que recargó el catálogo (`uao reload`) después de `uao enable`.

## Dónde preguntar

| Situación | Canal |
|---|---|
| Error reproducible, comportamiento distinto al documentado | Incidencia con la plantilla de **defecto**. |
| Falta una operación o un proveedor | Incidencia con la plantilla de **capacidad**. Indique el endpoint oficial y para qué lo necesita. |
| La documentación dice algo que el código no hace | Incidencia de defecto: una afirmación incorrecta en los documentos se trata como fallo. |
| Vulnerabilidad | **No** abra una incidencia pública. Siga [SECURITY](SECURITY.md). |
| Duda de uso o de diseño | Incidencia marcada como pregunta, o la pestaña Discussions si está habilitada. |

Incluya siempre: versión (`uao doctor` la imprime), sistema operativo, versión de Python, comando exacto, respuesta completa sin secretos y el `X-Request-Id` o `trace_id`. Elimine tokens, direcciones de correo reales, números de teléfono y contenidos privados antes de pegar nada.

## Qué cubre el proyecto

Cubre el código de este repositorio, su documentación y sus pruebas. **No** cubre: la configuración de su cuenta en Google, Microsoft, Meta, Slack, Discord, Twilio, SendGrid, Resend o GitHub; la aprobación de aplicaciones o plantillas por parte de esos proveedores; costos de API; su infraestructura, red o TLS; ni el cumplimiento normativo de su organización sobre los datos que decida mover.

Un proveedor puede cambiar su API sin avisar a este proyecto. Si una operación deja de funcionar por un cambio remoto, abra una incidencia con la respuesta del proveedor y la fecha: la corrección es un cambio de conector documentado, no una configuración suya.

## Tiempos

Mantenimiento de una persona, sin guardia ni SLA. Los informes se atienden por impacto: primero seguridad, después defectos que contradicen la documentación, después capacidades nuevas. Un informe sin pasos reproducibles puede cerrarse pidiendo más datos.

## Contribuir una solución

Las correcciones son bienvenidas. Lea [CONTRIBUTING](CONTRIBUTING.md): se piden cambios pequeños, con prueba que falle antes del arreglo y documentación actualizada en el mismo cambio.
