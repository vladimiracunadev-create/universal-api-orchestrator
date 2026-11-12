# Credenciales, OAuth y separación de permisos

## Dos niveles independientes

La **clave del gateway** autoriza a una aplicación a utilizar este servicio. El **token del proveedor** autoriza a este servicio ante Google, Meta, Microsoft u otra API. No se intercambian: entregar la clave del gateway a un frontend público expondría las operaciones habilitadas en el servidor.

`APPROVAL_API_KEY` es adicional para escrituras y ack de eventos. Debe mantenerse separada de clientes solo lectura. No implementa identidad por usuario, expiración de sesiones ni RBAC; corresponde a un dominio de confianza controlado.

## Secretos locales

`bootstrap.py` genera claves aleatorias y Fernet; preserva valores ya existentes. Si hay una base de datos pero falta STATE_KEY, se debe restaurar la clave original, no crear otra. Copie de forma segura el respaldo de la base y su clave, separados cuando sea posible. Perder STATE_KEY impide recuperar tokens y resultados cifrados.

`.env` está ignorado por Git. En Unix se crea con modo 600; en Windows utilice ACLs. En producción inyecte secretos mediante el gestor de su plataforma; esta versión no tiene adaptadores directos de Vault/Secrets Manager/Key Vault.

## Tipos implementados

| Tipo | Configuración y uso |
|---|---|
| `none` | API pública o proveedor que autentica en ruta confiable, como el bot Telegram configurado. |
| `bearer` | `token_env`, prefijo por defecto Bearer; Discord usa Bot. |
| `api_key` | `token_env` y nombre de cabecera. |
| `basic` | `username_env` y `password_env`, utilizados por Twilio. |
| `oauth2` | Refresh token guardado, token_key y endpoint token con allowlist. |
| `client_credentials` | Client ID/secret desde entorno, scope opcional y token endpoint permitido. |
| `msal` | Token delegado Microsoft; caché serializada cifrada y selección de cuenta. |

No están implementados autorización JWT propia de un servidor, mTLS por proveedor, service accounts Google con delegación de dominio ni un portal OAuth multiusuario con callbacks web. Son extensiones diferentes, no variantes que se habilitan solo cambiando una variable.

## Google

La CLI usa flujo de aplicación instalada con biblioteca oficial, PKCE y callback loopback. El consentimiento del usuario se realiza en Google; el gateway no pide su contraseña. Los tokens se almacenan cifrados bajo `token_key`.

Gmail usa por defecto `google`; Calendar usa `google_calendar`; Drive usa `google_drive`. Autorice cada slot con sus scopes mínimos. Cada sistema puede configurarse con otro slot si administra cuentas distintas. No basta con cambiar el nombre para obtener aislamiento entre usuarios: no existe RBAC por slot.

Si Google devuelve `invalid_grant`, revise revocación, estado de la app y alcance del consentimiento. Repita la autorización solo tras identificar la causa. Guardar un nuevo token en el mismo slot reemplaza el anterior. No imprima ni pegue refresh tokens en issues.

## Microsoft

La CLI inicia device flow para una app pública registrada. La caché de MSAL permite refresco silencioso y se cifra. La cuenta debe tener permisos delegados adecuados; algunas organizaciones deshabilitan device flow o requieren consentimiento administrativo. No se eluden esas restricciones.

Outlook y Teams usan el slot `microsoft` salvo configuración distinta. Debe autorizar scopes suficientes para el conjunto usado. Si la caché contiene múltiples cuentas sin selección explícita, el código falla en lugar de elegir una arbitrariamente; configure `username` o un slot separado.

## Refresh y concurrencia

Hay un lock por slot para evitar renovar simultáneamente el mismo token dentro del proceso. Si el proveedor rota refresh tokens, se persiste la versión recibida. La expiración se comprueba antes de usarlo. Los locks no son distribuidos: mantenga un solo worker con esta implementación.

## Revocar acceso

Deshabilite el sistema, reinicie el servicio y revoque el consentimiento/token en el proveedor. Cambie claves del gateway si se filtraron. La revocación real es responsabilidad del proveedor; borrar un archivo local no invalida un token ya copiado por un tercero.
