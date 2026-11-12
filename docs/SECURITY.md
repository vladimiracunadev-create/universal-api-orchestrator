# Seguridad, privacidad y checklist de operación

## Modelo de confianza

La configuración YAML y las variables de proceso son confiables y administradas por el operador. El cliente HTTP, el texto de mensajes y las respuestas externas no lo son. Este servidor utiliza claves compartidas y un almacén local; es adecuado como componente backend dentro de un dominio de confianza, no como servicio abierto a múltiples empresas sin aislamiento adicional.

## Controles implementados

El gateway exige clave en endpoints operativos, separa aprobación de escrituras y prohíbe escribir desde `/ask`. Los destinos requieren allowlist, resolución DNS válida y bloqueo de direcciones no globales salvo habilitación explícita de redes privadas. No se siguen redirecciones. Se verifica TLS y se limita la respuesta HTTP durante su lectura. Las cabeceras del cliente no pueden reemplazar credenciales del proveedor.

Solo se reintentan GET/HEAD en casos temporales; no los envíos. La reserva idempotente conserva fallos ambiguos para revisión, y liberarla exige clave de aprobación, confirmación explícita y un resultado comprobado; declarar `delivered_do_not_retry` mantiene el bloqueo a propósito. Hay límites de tamaño, validación de parámetros, semáforo de concurrencia y timeouts de transporte acotados aunque el catálogo pida otro valor.

Existe además un control de carga local por identidad de llamada (token bucket en memoria): responde 429 con `Retry-After` y la identidad es un resumen SHA-256, de modo que la clave no se almacena para contar. Toda respuesta lleva `X-Request-Id`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` y `Referrer-Policy: no-referrer`; un identificador aportado por el cliente se acepta solo si coincide con un formato restringido, para no reflejar contenido arbitrario en una cabecera. La recarga del catálogo requiere aprobación y, ante un archivo inválido, conserva el catálogo anterior en lugar de quedarse sin sistemas.

Tokens, eventos y respuestas persistidas tienen cifrado autenticado Fernet; algunas columnas de control —identificador, origen, tiempos y estado— permanecen en texto. No se registra deliberadamente el contenido de mensajes, URLs con tokens ni secretos en el log de auditoría. La CLI sí muestra datos que el operador ha solicitado: su terminal y redirecciones de salida también deben protegerse.

Se valida origen de webhooks implementados y se deduplican eventos. SOAP usa un parser defensivo y escapa valores interpolados. Gmail decodifica MIME sin descargar adjuntos implícitos y sin ejecutar HTML.

## Límites que no deben ocultarse

La comprobación DNS previa tiene un riesgo residual entre verificación y conexión; **no es una defensa SSRF absoluta**. Use firewall/egress proxy a destinos controlados. Las APIs que se registren pueden exponer información sensible aunque el destino sea legítimo: allowlist no reemplaza autorización de datos.

El límite de carga incluido es **de una instancia**: vive en memoria del proceso, se reinicia con él y cada réplica cuenta por separado. No es protección contra abuso ni contra denegación de servicio distribuida; eso corresponde al proxy inverso o al WAF. No existe límite por usuario o tenant, circuito distribuido, protección DDoS, mTLS, SSO/RBAC, rotación automática de claves, firma individual de aprobaciones, gestor de secretos integrado ni auditoría inmutable. El semáforo limita concurrencia, no cuotas comerciales. Los logs pueden falsificarse si se comprometió el host.

La clave de aprobación es un secreto compartido: cualquier proceso que la posea puede aprobar una escritura, reconocer un evento, liberar una reserva o recargar el catálogo. Una liberación **no** queda atribuida a una persona concreta. Para separación de funciones real hacen falta identidad y autorización por usuario, que esta versión no implementa.

SQLite, locks y cachés son locales. No hay consistencia multiinstancia ni recuperación automática de envíos ambiguos. Un timeout no demuestra que la acción no se realizó. El cifrado en reposo no protege el proceso que ya tiene la clave ni reemplaza controles de acceso al equipo.

## IA y datos de correo

La IA está apagada; datos sensibles se bloquean salvo permiso explícito. Al habilitarla, el endpoint puede recibir cuerpos de mensajes y otros datos privados. Revise contratos, finalidad, minimización y permisos de la organización. Use `response_map` para reducir datos y no envíe contraseñas ni secretos presentes accidentalmente en correos.

Las instrucciones del modelo tratan los resultados como datos, pero eso no prueba inmunidad a prompt injection. El control sólido aquí es que `/ask` no puede ejecutar escrituras ni herramientas arbitrarias. La respuesta debe revisarse antes de convertirla en mensaje o acción externa.

## Antes de producción

- Separar desarrollo, staging y producción; probar con destinatarios consentidos y comprobar recibos en el proveedor.
- Publicar HTTPS mediante proxy, restringir endpoints operativos/documentación y controlar egress/DNS.
- Agregar identidad y autorización por cliente/usuario cuando haya más de un dominio de confianza; separar claves de aprobación.
- Administrar secretos, permisos del volumen, respaldos cifrados, prueba de restauración y recuperación de STATE_KEY.
- Definir límites de consumo y un límite de carga compartido en el proxy, política de retención (`uao prune-events`, `uao prune-requests`), monitoreo del recuento de reservas pendientes y procedimiento de reconciliación ensayado; verificar el comportamiento ante 429, timeout y caídas.
- Revisar licencias, permisos de APIs, consentimiento, protección de datos y requisitos sectoriales aplicables al despliegue concreto.

No se declara cumplimiento normativo ni certificación de seguridad por incluir esta lista. Para un negocio en Chile u otra jurisdicción, la revisión legal depende de los datos, tratamiento, contratos y normativa vigente; no viene resuelta en el código.

## Verificación automatizada

El workflow de seguridad ejecuta en cada push y una vez por semana gitleaks sobre el historial completo, Bandit sobre `src/`, `pip-audit` sobre las dependencias resueltas y CodeQL para Python, con las acciones fijadas a SHA. Dependabot propone actualizaciones semanales de pip, GitHub Actions y Docker. Ninguna de esas herramientas prueba un proveedor real ni sustituye una revisión humana: los resultados realmente obtenidos están en [VALIDATION](VALIDATION.md).

## Reportar un problema

El procedimiento, el alcance y lo que queda fuera están en la [política de seguridad](../SECURITY.md): use el aviso privado de GitHub, no una incidencia pública. No publique tokens ni datos personales. Incluya versión, escenario mínimo sin secretos, impacto y prueba reproducible. Ante una filtración, revoque en el proveedor y rote las claves afectadas; eliminar un commit no basta.
