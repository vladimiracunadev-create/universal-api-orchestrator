from ..connectors.builders import build_request
from ..connectors.mail_content import normalize_gmail
from ..errors import IntegrationError
from ..transport import request
from .base import Adapter


class ProviderAdapter(Adapter):
    async def execute(self, system, operation, params, headers):
        spec=build_request(system,operation,params)
        code,payload=await request(spec.method,system["base_url"].rstrip("/")+spec.path,system["allowed_hosts"],headers=headers,**spec.kwargs)
        if system.get("provider") in {"slack","telegram"} and isinstance(payload,dict) and not payload.get("ok",False):
            raise IntegrationError("PROVIDER_REJECTED_REQUEST",code)
        if system.get("provider") == "gmail":
            payload = normalize_gmail(payload)
        return code,payload
