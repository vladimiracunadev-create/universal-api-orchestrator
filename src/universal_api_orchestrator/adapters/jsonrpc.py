import uuid

from ..errors import IntegrationError
from ..transport import request
from .base import Adapter


class JsonRpcAdapter(Adapter):
    async def execute(self,system,operation,params,headers):
        request_id=str(uuid.uuid4())
        body={"jsonrpc":"2.0","id":request_id,"method":operation["rpc_method"],"params":params}
        code,payload=await request("POST",system["base_url"],system["allowed_hosts"],json=body,headers=headers,timeout=operation.get("timeout_seconds"))
        if not isinstance(payload,dict) or payload.get("error") or payload.get("id") != request_id or payload.get("jsonrpc")!="2.0":
            raise IntegrationError("JSONRPC_ERROR",code)
        return code,payload.get("result")
