# Documentación de sistema

Recorrido completo del proyecto en 19 capítulos, pensado para quien llega sin contexto: un desarrollador nuevo, una auditoría, una revisión técnica o quien deba mantener esto dentro de un año.

Cada capítulo declara sus fuentes: archivo y, cuando aporta, función concreta. Si un capítulo afirma algo que el código no hace, es un defecto y se corrige como tal. Lo que no se verificó se dice, no se insinúa.

| # | Capítulo | Responde a |
|---|---|---|
| 01 | [Visión general del sistema](01-system-overview.md) | Qué es, para quién, qué problema resuelve y qué no hace. |
| 02 | [Instalación y ejecución](02-installation-and-execution.md) | Cómo levantarlo en cada entorno y cómo comprobar que funciona. |
| 03 | [Arquitectura](03-architecture.md) | Capas, flujos y por qué están separadas así. |
| 04 | [Mapa del código](04-code-map.md) | Qué hace cada archivo y a quién llama. |
| 05 | [Referencia técnica](05-technical-reference.md) | Endpoints, modelos, funciones públicas y códigos de error. |
| 06 | [Explicación profunda del código](06-deep-code-explanation.md) | Las decisiones difíciles, línea a línea donde hace falta. |
| 07 | [Base de datos](07-database.md) | Esquema SQLite, cifrado, índices y ciclo de vida de cada fila. |
| 08 | [Flujo de datos](08-data-flow.md) | El camino de una consulta, de una escritura y de un evento. |
| 09 | [APIs e integraciones](09-apis-and-integrations.md) | Los 13 proveedores, sus contratos y sus límites reales. |
| 10 | [Configuración](10-configuration.md) | Cada variable, su valor por defecto y qué pasa si falta. |
| 11 | [Seguridad](11-security.md) | Modelo de amenazas, controles y lo que no está cubierto. |
| 12 | [Pruebas y calidad](12-testing-and-quality.md) | Qué se prueba, cómo y qué queda sin cubrir. |
| 13 | [Despliegue y operación](13-deployment-and-operations.md) | Puesta en marcha, mantenimiento y respaldo. |
| 14 | [Troubleshooting](14-troubleshooting.md) | Síntomas, causas y procedimiento de diagnóstico. |
| 15 | [Riesgos y deuda técnica](15-risks-and-technical-debt.md) | Lo que puede fallar y lo que falta hacer, sin adornos. |
| 16 | [Glosario](16-glossary.md) | Términos del dominio y del proyecto. |
| 17 | [Resumen ejecutivo](17-executive-summary.md) | Una página para quien decide, sin jerga. |
| 18 | [Guía para desarrollador nuevo](18-new-developer-guide.md) | Primer día, primera tarea, primeros errores. |
| 19 | [Matriz de trazabilidad](19-traceability-matrix.md) | Cada capacidad declarada contra su código y su prueba. |

## Cómo leerla

Si va a **operar** la instancia: 01, 02, 10, 13 y 14. Si va a **desarrollar**: 01, 03, 04, 06, 12 y 18. Si va a **auditar**: 01, 07, 11, 12, 15 y 19. Si va a **decidir** si sirve para un proyecto: 01, 17 y 15, en ese orden.

La documentación de uso diario vive en el [índice general](../README.md) y es más corta. Esta carpeta es el detalle.

## Alcance y fecha

Corresponde a la versión **0.3.0**, al 12 de noviembre de 2026. Los recuentos coinciden con [STATUS](../../STATUS.md) y los resultados de ejecución con [VALIDATION](../VALIDATION.md). `python scripts/verify_repository.py` falla si la versión declarada deja de coincidir con el código.
