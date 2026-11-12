from defusedxml import ElementTree as ET

from ..errors import IntegrationError
from ..transport import request
from .base import Adapter

ENTITIES = (("&","&amp;"),("<","&lt;"),(">","&gt;"),('"',"&quot;"),("'","&apos;"))

def escape_text(value) -> str:
    """Escapa el valor como texto XML. No se usa ningún parser para construir el sobre."""
    text = str(value)
    for raw, entity in ENTITIES:
        text = text.replace(raw, entity)
    return text

class SoapAdapter(Adapter):
    async def execute(self,system,operation,params,headers):
        envelope=operation["envelope_template"].format(**{k:escape_text(v) for k,v in params.items()})
        headers={"Content-Type":"text/xml; charset=utf-8","SOAPAction":operation.get("soap_action",""),**headers}
        code,payload=await request("POST",system["base_url"],system["allowed_hosts"],content=envelope.encode(),headers=headers,timeout=operation.get("timeout_seconds"))
        root=ET.fromstring(payload)
        if any(node.tag.split("}")[-1]=="Fault" for node in root.iter()):
            raise IntegrationError("SOAP_FAULT",code)
        return code,xml_to_dict(root)

def xml_to_dict(node):
    children = list(node)
    tag = node.tag.split("}")[-1]
    if not children:
        return {tag: node.text}
    result = {}
    for child in children:
        item = xml_to_dict(child)
        key, value = next(iter(item.items()))
        if key in result:
            result[key] = result[key] if isinstance(result[key], list) else [result[key]]
            result[key].append(value)
        else:
            result[key] = value
    return {tag: result}
