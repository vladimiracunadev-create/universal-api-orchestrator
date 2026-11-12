from .graphql import GraphQLAdapter
from .grpc_adapter import GrpcAdapter
from .jsonrpc import JsonRpcAdapter
from .provider import ProviderAdapter
from .rest import RestAdapter
from .soap import SoapAdapter

ADAPTERS={"rest":RestAdapter(),"graphql":GraphQLAdapter(),"jsonrpc":JsonRpcAdapter(),"soap":SoapAdapter(),"grpc":GrpcAdapter(),"provider":ProviderAdapter()}
