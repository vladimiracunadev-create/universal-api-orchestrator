# Por dónde empezar

Esta documentación distingue **entorno técnico** (Windows, macOS, Linux, contenedor o servidor) de **entorno de trabajo** (soporte, comercio, oficina, educación o desarrollo). Se pueden combinar sin reescribir cada integración.

## Ruta operativa

1. Instale y arranque desde el [README](../README.md). `bootstrap.py` genera claves propias en su equipo; nunca están incluidas en el ZIP.
2. Lea [ENVIRONMENTS](ENVIRONMENTS.md) y elija dónde vivirá el estado persistente y quién lo administrará.
3. Active primero un solo proveedor con permisos de lectura. Use su guía específica y `uao doctor`, sabiendo que doctor no valida una sesión con el proveedor.
4. Ejecute una consulta pequeña y revise `ok`, `data`, `error` y `meta`. `HTTP 200` del gateway puede contener una operación fallida.
5. Pruebe `ask` sin modelo. Solo después evalúe la exposición de datos al activar una IA.
6. Para enviar, revise destinatario, permisos, consentimiento, idempotencia y autorización separada. No habilite escrituras globales en una instancia que solo consulta.
7. Antes de enviar algo que importe, lea [RECONCILIATION](RECONCILIATION.md): sepa qué hará cuando una escritura quede en duda, porque el gateway no reintentará por su cuenta.
8. Para el día a día —arranque, purga, límites de carga, incidentes y rotación de claves— use el [RUNBOOK](RUNBOOK.md).

## Ruta para desarrollar y mantener

Lea [ARCHITECTURE](ARCHITECTURE.md), [API_GUIDE](API_GUIDE.md), [CLI](CLI.md), [ADDING_CONNECTOR](ADDING_CONNECTOR.md) y [SECURITY](SECURITY.md). El [índice de documentación](README.md) enumera todo, el [glosario](GLOSSARY.md) fija el significado de cada término y la [documentación de sistema](system-documentation/README.md) recorre el proyecto en 19 capítulos. Revise las pruebas existentes antes de tocar adaptadores. La [matriz](CONNECTOR_MATRIX.md) es el contrato de cobertura, no una promesa de soporte a todos los endpoints de un proveedor.

## Ruta comercial o de implementación

Use [WORK_SCENARIOS](WORK_SCENARIOS.md) para describir una solución completa al cliente. Distinga el canal de comunicación, la fuente de negocio y la decisión de envío. El repositorio aporta conectividad y controles técnicos; no contiene los datos del cliente, sus procesos, contratos comerciales ni la autorización de sus usuarios.

## Qué obtiene sin pagar a un proveedor

El código, los ejemplos locales y las pruebas offline pueden ejecutarse sin credenciales de servicios. Las cuentas, consumos de API, modelos, números telefónicos, servidores y eventuales verificaciones se tramitan por separado. No se incluyen tarifas estáticas: consulte cada proveedor y su cuenta al presupuestar.

## Archivos que no se deben compartir

`.env`, `secrets/`, `data/`, bases de datos, claves privadas, credenciales OAuth y capturas con tokens. El estado cifrado también es confidencial. Los textos de mensajes devueltos por CLI no se guardan automáticamente, pero pueden quedar en la terminal o en redirecciones de salida que haga el operador.

## Lectura del estado de una función

**Implementada** significa que existe un camino de código ejecutable. **Probada offline** significa validada con entradas controladas, no con una cuenta externa. **Guía** significa instrucciones para desplegar/configurar. **Pendiente** significa que no está implementada. No son categorías equivalentes.
