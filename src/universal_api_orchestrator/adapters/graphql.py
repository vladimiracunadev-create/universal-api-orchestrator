from ..errors import IntegrationError
from ..transport import request
from .base import Adapter


class GraphQLAdapter(Adapter):
    async def execute(self,system,operation,params,headers):
        code,payload=await request("POST",system["base_url"],system["allowed_hosts"],json={"query":operation["query"],"variables":params},headers=headers,timeout=operation.get("timeout_seconds"))
        if not isinstance(payload,dict) or payload.get("errors"):
            raise IntegrationError("GRAPHQL_ERROR",code)
        return code,payload
