# Agregar un sistema sin duplicar toda la integración

## Primero inspeccionar, luego extender

Revise la matriz, `config/systems.yaml`, los builders y pruebas antes de añadir un sistema. Una API REST simple puede configurarse; contratos MIME, firmas o uploads pueden requerir código. No declare soporte de un proveedor con solo agregar su nombre a una lista.

## Ejemplo REST de solo lectura

```yaml
systems:
  mi_crm:
    enabled: false
    protocol: rest
    base_url: https://api.miempresa.example
    allowed_hosts: [api.miempresa.example]
    sensitive: true
    auth:
      type: bearer
      token_env: MI_CRM_TOKEN
    operations:
      get_customer:
        method: GET
        path: /customers/{id}
        effect: read
        description: Consultar un cliente autorizado por identificador.
        timeout_seconds: 10
        input_schema:
          type: object
          properties:
            id: {type: string, minLength: 1, maxLength: 200}
          required: [id]
          additionalProperties: false
        response_map:
          id: id
          name: profile.name
```

`timeout_seconds` es opcional: fija el tiempo de esa operación y se acota entre 0,5 y 120 segundos; sin él se usa `REQUEST_TIMEOUT_SECONDS`. Un valor no numérico se ignora en lugar de desactivar el límite.

El dominio `.example` es un marcador, no un proveedor real. Sustitúyalo por el host que controla y habilite después de verificar autenticación, permisos y schema. Para un sistema en red privada habilite esa capacidad conscientemente y restrinja egress; no permita hosts arbitrarios.

## Cuerpos, query y formularios

Sin templates, parámetros usados en `{id}` van a la ruta; los restantes van a query para GET/HEAD/DELETE o JSON para los demás métodos. Para contratos específicos utilice `query_template`, `body_template` o `form_template`. `@nombre` sustituye el valor completo conservando tipos:

```yaml
method: POST
path: /tickets
effect: write
body_template:
  customer_id: '@customer_id'
  title: '@title'
  metadata: '@metadata'
```

Declare un `input_schema` con cada parámetro requerido. Use `defaults` para valores por defecto explícitos. No se evalúa Python ni Jinja. Si un valor literal debe comenzar con `@`, adapte el constructor en lugar de asumir un mecanismo de escape no implementado.

`${VARIABLE}` en el catálogo se expande al obtener el sistema, no al iniciar todos los proveedores. Un secreto faltante no habilita un fallback anónimo: la configuración falla de forma visible. La operación debe declarar `effect:read` o `write`. Un POST de consulta puede ser read, pero solo el operador confiable debe clasificarlo.

## Nuevo proveedor con builder

Implemente una función que reciba configuración, operación y parámetros, y devuelva `RequestSpec(method,path,kwargs)`. Regístrela en `BUILDERS`. Mantenga toda llamada de red en el transporte compartido para conservar límites, validación de host y política de retries. Nunca acepte rutas de archivos del cliente para adjuntar contenido del servidor.

Si el proveedor expresa un error dentro de HTTP 200, conviértalo en `IntegrationError`; no lo marque como éxito. Añada pruebas de autorización, formato, éxito, rechazo, tamaños, Unicode y reintentos. Para webhooks, use la verificación oficial sobre bytes originales antes de deserializar; un campo `secret` cualquiera no reemplaza la firma del proveedor.

## Autenticación adicional

Consulte [AUTHENTICATION](AUTHENTICATION.md). OAuth client credentials sirve para APIs que lo soporten, no para sustituir el consentimiento de Gmail. Si incorpora firma JWT, HMAC outbound, mTLS o un SDK externo, establezca timeouts, controles de host y tratamiento de secretos equivalentes; documente cualquier excepción.

## Nuevo protocolo

Implemente la interfaz de `adapters/base.py`, registre el adapter y conserve el sobre de resultado. El hecho de que gRPC/GraphQL exista no cubre WebSocket, streaming o mensajes de una cola. Añada dependencias opcionales para que quienes no usen el protocolo puedan iniciar el núcleo.

## Importar OpenAPI

```bash
python tools/import_openapi.py proveedor.yaml --name proveedor --output proveedor.system.yaml
```

El importador genera un **punto de partida deshabilitado** con server, rutas, verbos y operationId. No resuelve toda la especificación, `$ref`, seguridad, cuerpos complejos ni todas las variantes de OpenAPI. Revise cada operación, clasifique efectos y complete schemas antes de combinarla con el catálogo. No se anuncia compatibilidad completa con una versión OpenAPI por leer `paths`.

## Probar el catálogo nuevo sin reiniciar

```bash
uao catalog                 # ¿aparece el sistema con sus operaciones?
uao enable mi_crm
uao reload                  # requiere clave de aprobación
uao doctor                  # ¿faltan variables de entorno?
```

Si el YAML queda inválido, `reload` responde `422 INVALID_CATALOG_PREVIOUS_KEPT` y el catálogo anterior sigue en uso: corrija el archivo y repita. `verify_repository.py` detecta antes el problema, incluido un `systems` que no sea un mapa.

## Definición de terminado

Un conector terminado para su caso debe tener documentación de alta y de permisos, operaciones delimitadas, schema, formato y errores correctos, tests offline, ejemplo seguro con `confirmed:false` si escribe, y una prueba real autorizada registrada por el operador. Ejecute `python scripts/verify_repository.py` y toda la suite. Actualice la matriz, `config/catalog.json` y el changelog; el verificador falla si los recuentos no coinciden con el catálogo, de modo que no se puede publicar una cifra sin su implementación.
