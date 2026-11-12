# Revisión de la base y justificación de la ampliación

Se revisaron README, roadmap, configuración, adaptadores, autenticación/seguridad disponibles, motor de respuesta y pruebas del ZIP original antes de modificar. No se consultó ni modificó un repositorio remoto.

| Hallazgo de alcance/diseño | Cambio en v0.2 | Motivo |
|---|---|---|
| Protocolos genéricos no equivalían a integración completa de Gmail o WhatsApp. | Catálogo con 13 servicios, builders, schemas y guías específicas. | MIME, scopes, endpoints y firmas requieren conocimiento del proveedor. |
| OAuth/refresh figuraba como evolución pendiente. | Autorización local Google, MSAL y gestión de tokens cifrados. | Evitar contraseñas/tokens pegados manualmente en código. |
| No había una política homogénea de aprobación de escrituras. | Bloqueo global, clave separada, confirmed e idempotencia. | Reducir correos/mensajes accidentales y repetición de efectos. |
| Recepción genérica no aportaba verificadores específicos de origen. | Meta, Slack, Telegram y GitHub verificados antes de persistir. | No aceptar mensajes de origen desconocido como eventos auténticos. |
| Necesidad de reforzar controles de red y transparencia. | DNS fail-closed, no redirects, límites y advertencia sobre riesgo residual. | Reducir SSRF y evitar promesas absolutas de seguridad. |
| Pruebas originales reducidas. | Suite de contratos, políticas, firmas, almacenamiento, MIME y transporte. | Hacer verificables los componentes sin usar cuentas personales. |
| Documentación general, predominantemente en inglés. | Manuales en español por proveedor, entorno y caso de uso. | Poder instalar, operar, mantener y explicar el sistema sin adivinar pasos. |

Se preservan licencia/autor original y los adaptadores existentes. Se documentan cambios incompatibles en [MIGRATION](MIGRATION_0_1_TO_0_2.md). Los componentes todavía no implementados permanecen identificados en [ROADMAP](../ROADMAP.md); no se les asigna estado de terminado por mencionarlos.
