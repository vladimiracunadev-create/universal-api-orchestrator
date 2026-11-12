from ..connectors.builders import generic
from ..transport import request
from .base import Adapter


class RestAdapter(Adapter):
    async def execute(self, system, operation, params, headers):
        spec=generic(system,operation,params)
        return await request(spec.method,system["base_url"].rstrip("/")+spec.path,system["allowed_hosts"],headers=headers,**spec.kwargs)
