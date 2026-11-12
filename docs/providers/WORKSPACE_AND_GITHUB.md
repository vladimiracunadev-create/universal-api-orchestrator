# Calendar, Drive y GitHub

## Google Calendar

Habilite Calendar API en su proyecto. Para leer eventos use un consentimiento separado:

```bash
uao auth-google --client secrets/google-client.json --token-key google_calendar --scopes https://www.googleapis.com/auth/calendar.events.readonly
uao enable google_calendar
```

`list_events` y `get_event` son lectura. `calendar_id:primary` representa el calendario principal de la identidad autorizada. Los eventos de otros calendarios requieren sus permisos. Use rangos temporales explícitos y zonas horarias al preparar informes.

`create_event` requiere scope de escritura apropiado, como `calendar.events`, además de la aprobación del gateway. El objeto de evento debe corresponder al contrato de Google Calendar. Cree eventos con start/end y zona horaria coherentes; la validación semántica final corresponde a Calendar. [Ejemplo de lectura](../../examples/requests/calendar-list.json).

No se incluye sincronización incremental completa, disponibilidad free/busy, invitaciones en todos sus modos ni programación recurrente administrada por el gateway.

## Google Drive

Habilite Drive API y autorice el slot `google_drive`:

```bash
uao auth-google --client secrets/google-client.json --token-key google_drive --scopes https://www.googleapis.com/auth/drive.readonly
uao enable google_drive
```

El scope readonly concede lectura amplia de archivos accesibles a la identidad; para una aplicación de alcance menor evalúe un scope más limitado y ajuste su flujo de selección/archivos. No trate el scope como autorización de publicar contenido fuera de la organización.

`list_files` consulta listado/filtros, `get_file` obtiene metadatos y `export_text` exporta un documento compatible como texto. No hay subida de archivos, edición de documentos, extracción PDF/OCR ni lectura ilimitada de todos los formatos. Las respuestas grandes se rechazan según el límite HTTP del gateway.

[Ejemplo](../../examples/requests/drive-list.json). Solicite solo campos necesarios y pagine con el cursor admitido. No utilice URLs compartidas como si fueran IDs de archivo sin resolverlas explícitamente.

## GitHub

Genere un token de alcance mínimo para los repositorios que debe consultar o modificar. Guárdelo en `GITHUB_TOKEN`; para recepción añada `GITHUB_WEBHOOK_SECRET`, un secreto independiente.

```bash
uao enable github
```

`get_repo` obtiene metadatos, `list_issues` consulta issues y `create_issue` crea uno con aprobación. No están implementados escritura de commits, publicación del propio repositorio, gestión de ramas, pull requests ni ejecución remota de workflows. Los permisos deben coincidir con recurso/operación; un token válido no implica acceso a todos los repositorios privados.

La API se versiona explícitamente con una cabecera en YAML; revise esa versión antes de migrar. El webhook `/v1/webhooks/github` valida firma sobre el cuerpo y combina identidad de entrega con hash del payload para deduplicar. Seleccione los eventos necesarios en la configuración del repositorio/app. [Ejemplo de consulta](../../examples/requests/github-list.json).

## Cuentas y separación

Calendar, Drive y Gmail usan slots separados por defecto; Microsoft utiliza su propia caché. Una instancia no es multitenant: para clientes diferentes no basta con crear nombres nuevos, porque la misma clave del gateway permite operar los sistemas habilitados. Use instancias separadas o implemente autorización/aislamiento antes de servir a múltiples empresas.

Fuentes: [SOURCES](../SOURCES.md).
