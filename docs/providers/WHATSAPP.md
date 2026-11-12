# WhatsApp Cloud API: de la cuenta al mensaje

## Qué integración es

Se utiliza la API empresarial oficial de Meta, no automatización de WhatsApp Web, scraping, lectura de una cuenta personal por QR ni extracción de conversaciones privadas. El código envía solicitudes reales al endpoint Graph que configure; no da de alta la cuenta ni evita permisos del proveedor. Documentación y política oficial: [fuentes](../SOURCES.md).

## Preparar cuenta y permisos

En el entorno de desarrolladores de Meta cree o seleccione su aplicación, vincule el negocio y WhatsApp Business Account (WABA), y complete el alta del número que utilizará. Para comenzar use los recursos y destinatarios de prueba que permita la consola. Obtenga el **phone number ID**, que no es el número telefónico, y un access token autorizado para ese recurso.

Revise los permisos `whatsapp_business_messaging` y, para funciones administrativas/plantillas, `whatsapp_business_management`, además de las condiciones de su aplicación y negocio. Un token temporal es útil para pruebas, no un plan de operación permanente. Gestione duración, rotación y permisos en Meta; no se fija una duración universal en esta guía.

Complete en `.env`:

```dotenv
WHATSAPP_GRAPH_VERSION=VERSION_VIGENTE_CON_PREFIJO_v
WHATSAPP_PHONE_NUMBER_ID=ID_DEL_RECURSO_NUMERO
WHATSAPP_ACCESS_TOKEN=TOKEN_DE_SU_APLICACION
WHATSAPP_APP_SECRET=SECRETO_DE_LA_APP_META
WHATSAPP_VERIFY_TOKEN=CADENA_ALEATORIA_ELEGIDA_POR_USTED
```

Reemplace los valores; no son credenciales funcionales. `WHATSAPP_GRAPH_VERSION` queda sin valor en el repositorio para que seleccione explícitamente una versión soportada en su consola. Los ejemplos antiguos de documentación no deben utilizarse como prueba de cuál versión está vigente.

```bash
uao enable whatsapp
uao doctor
```

Reinicie el proceso tras cambiar configuración. Si `.env` alimenta Compose, recree el contenedor. Use primero `get_business_profile` o `list_templates` con su WABA para validar acceso antes de habilitar envíos.

## Enviar texto, plantilla o medios

El contrato usa `system:whatsapp`. Los campos de `send_template` son `to`, `template_name`, `language` y `components` opcionales. El gateway construye `messaging_product`, tipo template y el cuerpo esperado por Meta.

[Ejemplo de plantilla](../../examples/requests/whatsapp-template.json): `hello_world/en_US` es un ejemplo de prueba, no una plantilla garantizada en su cuenta. Consulte las plantillas disponibles, el idioma y sus parámetros. Reemplace el teléfono de ejemplo por un destinatario autorizado; no envíe a ese valor de relleno.

`send_text` acepta texto, preview_url y reply_to opcional. `send_media` admite un objeto de medio compatible (por ejemplo ID ya subido o enlace admitido por Meta); `upload_media` sube bytes base64 con nombre y MIME. La carga decodificada está limitada a **512.000 bytes** por esta implementación. `get_media_metadata` obtiene metadatos/URL; no descarga cualquier URL devuelta ni adjuntos arbitrariamente.

`send_interactive` permite estructura de interacción, pero debe respetar el contrato vigente de Meta. El schema admite el objeto; la validación semántica final pertenece al proveedor.

Toda escritura pasa por [aprobación e idempotencia](../API_GUIDE.md): activar sistema no equivale a activar envíos. Copie el JSON, revise, establezca una clave única y `confirmed:true` solo después de autorizar la acción.

## Consentimiento y ventanas

La política de WhatsApp distingue respuestas en la ventana de atención de 24 horas desde el último mensaje del usuario y contacto fuera de esa ventana mediante plantillas aprobadas. También exige los consentimientos pertinentes y respetar la baja del destinatario. Consulte la política oficial antes de operar campañas o automatizaciones; no se incluye una validación automática del consentimiento en este gateway.

El repositorio no mantiene un reloj de conversación ni impone automáticamente la elegibilidad de cada plantilla. Que el constructor produzca JSON válido no garantiza que Meta permita enviarlo. La aplicación de negocio debe conservar consentimiento, última interacción y reglas de atención humana cuando correspondan.

## Recibir mensajes y estados

Publique por HTTPS `/v1/webhooks/whatsapp`. En Meta configure esa URL y el mismo verify token. El challenge GET devuelve `hub.challenge` solo si el token coincide. El POST verifica `X-Hub-Signature-256` con el **app secret**, no con el verify token ni con el access token.

Configure la suscripción a los eventos de mensajes en la aplicación/WABA según la consola. El gateway recibe mensajes entrantes y estados (por ejemplo enviado/entregado/leído/fallido), separa cada evento y lo guarda cifrado. Lea con `uao events` y reconozca con `uao ack ID` cuando su proceso termine.

Un éxito de `/messages` no significa entrega al teléfono. Correlacione el identificador devuelto con los eventos de estado. No hay chatbot automático conectado al webhook; se requiere una política de negocio y un consumidor explícito.

## Diagnóstico y validación mínima

Compruebe, en este orden: sistema habilitado, variables presentes, versión Graph, relación token/WABA/phone ID, permisos, plantilla/idioma, destinatario, ventana/consentimiento y condiciones de la cuenta. Revise el panel del proveedor con el ID de mensaje, sin copiar tokens a logs.

Antes de aceptar una integración para un cliente, pruebe lectura, un envío autorizado, recepción webhook, deduplicación y un fallo controlado. Registre el resultado en el checklist de [validación](../VALIDATION.md). Ninguna de esas pruebas con cuentas reales fue realizada al generar este repositorio.
