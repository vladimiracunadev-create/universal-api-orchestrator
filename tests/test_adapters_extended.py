import pytest

from universal_api_orchestrator.adapters import provider, rest
from universal_api_orchestrator.config import settings
from universal_api_orchestrator.errors import IntegrationError
from universal_api_orchestrator.response_engine import compose_answer


@pytest.mark.asyncio
@pytest.mark.parametrize('vendor', ['slack','telegram'])
async def test_provider_semantic_error(monkeypatch,vendor):
    async def fake(*args,**kwargs):
        return 200, {'ok':False,'error':'not_allowed'}
    monkeypatch.setattr(provider,'request',fake)
    with pytest.raises(IntegrationError,match='PROVIDER_REJECTED_REQUEST'):
        await provider.ProviderAdapter().execute({'provider':vendor,'base_url':'https://example.com','allowed_hosts':['example.com']},{'method':'GET','path':'/test'}, {}, {})

@pytest.mark.asyncio
async def test_gmail_adapter_decodes_body(monkeypatch):
    async def fake(*args,**kwargs):
        return 200, {'id':'abc','payload':{'mimeType':'text/plain','body':{'data':'SG9sYQ'}}}
    monkeypatch.setattr(provider,'request',fake)
    _,body=await provider.ProviderAdapter().execute({'provider':'gmail','base_url':'https://gmail.googleapis.com','allowed_hosts':['gmail.googleapis.com']},{'method':'GET','path':'/a'}, {}, {})
    assert body['_content']['text']=='Hola'

@pytest.mark.asyncio
async def test_rest_real_builder(monkeypatch):
    async def fake(method,url,hosts,**kwargs):
        assert method=='GET' and url=='https://example.com/customers/a%2Fb'
        assert kwargs['params']=={'fields':'name'}
        return 200, {'name':'Ejemplo'}
    monkeypatch.setattr(rest,'request',fake)
    result=await rest.RestAdapter().execute({'base_url':'https://example.com','allowed_hosts':['example.com']},{'method':'GET','path':'/customers/{id}'},{'id':'a/b','fields':'name'}, {})
    assert result[1]['name']=='Ejemplo'

@pytest.mark.asyncio
async def test_ask_template_failure_sources(monkeypatch):
    monkeypatch.setattr(settings,'ai_mode','off')
    result=await compose_answer('Pregunta',{'fallo':{'system':'s','operation':'o','ok':False,'error':'ERROR','data':None}},'{question} {data} {errors}')
    assert 'ERROR' in result['answer'] and result['sent'] is False
    assert result['sources'][0]['ok'] is False

@pytest.mark.asyncio
async def test_ask_model_uses_decoded_evidence(monkeypatch):
    from universal_api_orchestrator import response_engine as mod
    monkeypatch.setattr(settings,'ai_mode','openai_compatible')
    monkeypatch.setattr(settings,'ai_allow_sensitive_data',True)
    monkeypatch.setattr(settings,'openai_compatible_model','mock-model')
    async def fake(method,url,hosts,**kwargs):
        assert 'CUERPO REAL' in kwargs['json']['messages'][1]['content']
        assert 'SECRET_BASE64' not in kwargs['json']['messages'][1]['content']
        return 200, {'choices':[{'message':{'content':'[correo] Respuesta simulada'}}]}
    monkeypatch.setattr(mod,'request',fake)
    results={'correo':{'ok':True,'system':'gmail','operation':'get_message','meta':{'sensitive':True},'data':{'id':'a','payload':{'raw':'SECRET_BASE64'},'_content':{'text':'CUERPO REAL'}}}}
    out=await compose_answer('Resume',results)
    assert out['mode']=='openai_compatible' and out['sent'] is False

@pytest.mark.asyncio
async def test_ask_model_failure_falls_back(monkeypatch):
    from universal_api_orchestrator import response_engine as mod
    monkeypatch.setattr(settings,'ai_mode','openai_compatible')
    monkeypatch.setattr(settings,'openai_compatible_model','mock-model')
    async def fake(*args,**kwargs):
        raise IntegrationError('UPSTREAM_HTTP_500')
    monkeypatch.setattr(mod,'request',fake)
    out=await compose_answer('Pregunta',{'a':{'ok':True,'system':'s','operation':'o','data':{'x':1}}})
    assert out['mode']=='deterministic'
    assert 'AI_FAILED_DETERMINISTIC_FALLBACK' in out['warnings']
