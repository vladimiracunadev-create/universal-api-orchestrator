import asyncio
import base64

from ..config import settings
from ..errors import IntegrationError
from ..security import assert_safe_endpoint
from ..transport import bounded_timeout
from .base import Adapter


class GrpcAdapter(Adapter):
    """Unary bytes. Requiere extra grpc y protobuf generado para contratos tipados."""
    async def execute(self,system,operation,params,headers):
        try:
            import grpc
        except ImportError as exc:
            raise IntegrationError("INSTALL_GRPC_EXTRA") from exc
        target=system["base_url"]
        await asyncio.to_thread(assert_safe_endpoint,target,system["allowed_hosts"])
        raw=base64.b64decode(params["raw_base64"],validate=True) if "raw_base64" in params else params.get("raw","").encode()
        if system.get("insecure",False):
            if not settings.allow_private_networks:
                raise IntegrationError("TLS_REQUIRED")
            channel=grpc.aio.insecure_channel(target)
        else:
            channel=grpc.aio.secure_channel(target,grpc.ssl_channel_credentials())
        async with channel:
            call=channel.unary_unary(operation["grpc_method"],request_serializer=lambda v:v,response_deserializer=lambda v:v)
            response=await call(raw,metadata=[(k.lower(),v) for k,v in headers.items()],timeout=bounded_timeout(operation.get("timeout_seconds")))
            return None,{"raw_base64":base64.b64encode(response).decode()}
