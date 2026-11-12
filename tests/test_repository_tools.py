import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def bootstrap_copy(tmp_path):
    scripts=tmp_path/'scripts';scripts.mkdir()
    (scripts/'bootstrap.py').write_bytes((ROOT/'scripts/bootstrap.py').read_bytes())
    (tmp_path/'.env.example').write_bytes((ROOT/'.env.example').read_bytes())
    return scripts/'bootstrap.py'

def test_bootstrap_creates_preserves_and_never_prints_keys(tmp_path):
    script=bootstrap_copy(tmp_path)
    first=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,check=True)
    env=(tmp_path/'.env').read_text()
    assert 'STATE_KEY=\n' not in env and 'ALLOW_WRITES=false' in env
    second=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,check=True)
    assert (tmp_path/'.env').read_text()==env
    assert env not in first.stdout+second.stdout

def test_bootstrap_refuses_key_replacement_with_existing_db(tmp_path):
    script=bootstrap_copy(tmp_path)
    (tmp_path/'data').mkdir()
    (tmp_path/'data/state.sqlite3').touch()
    result=subprocess.run([sys.executable,str(script)],capture_output=True,text=True)
    assert result.returncode!=0 and 'restaure' in result.stderr

def test_openapi_import_is_disabled_and_classifies_effects():
    spec=importlib.util.spec_from_file_location('uao_importer',ROOT/'tools/import_openapi.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fragment=module.build_fragment({'servers':[{'url':'https://example.com'}],'paths':{'/x':{'get':{'operationId':'read'},'post':{'operationId':'write'}}}},'api')['systems']['api']
    assert fragment['enabled'] is False
    assert fragment['operations']['read']['effect']=='read'
    assert fragment['operations']['write']['effect']=='write'
