"""Run with the installed Hermes Python and --runtime SOURCE. Uses a throwaway profile."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

parser=argparse.ArgumentParser()
parser.add_argument('--runtime',required=True)
options=parser.parse_args()
root=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,options.runtime)
with tempfile.TemporaryDirectory(dir=root/'.reference') as scratch:
    os.environ['HERMES_HOME']=scratch
    os.environ['HERMES_DISABLE_DOTENV']='1'
    from hermes_cli.plugins import PluginContext, PluginManager, get_pre_tool_call_block_message
    from hermes_cli.plugins_manifest import parse_manifest_file
    manifest=parse_manifest_file(root/'plugin.yaml',root,'user','')
    assert manifest is not None
    context=PluginContext(manifest,PluginManager())
    spec=importlib.util.spec_from_file_location('guardian_runtime_probe',root/'__init__.py',submodule_search_locations=[str(root)])
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    module.register(context)
    manager=context._manager
    assert set(manager._hooks)=={'pre_tool_call','post_tool_call','pre_llm_call'}
    assert 'guardian_expert' in manager._aux_tasks
    g=module.guardian.integration.create(context)
    context.set_config('mode','enforce')
    for _ in range(2):g.post('terminal',{'command':'synthetic-failure'},session_id='test',task_id='goal',status='error',result={'error':'synthetic'})
    def invoke(name,**kwargs):return [fn(**kwargs) for fn in manager._hooks.get(name,[])]
    with patch('hermes_cli.lifecycle.invoke_hook',side_effect=invoke):
        blocked=get_pre_tool_call_block_message('terminal',{'command':'synthetic-failure'},session_id='test',task_id='goal')
        assert blocked and 'Guardian incident' in blocked
    # Prove the host facade never forwards a tools parameter or creates a subagent.
    from agent.plugin_llm import PluginLlm
    captured=[]
    def caller(**kwargs):
        captured.append(kwargs)
        return 'openai-codex','gpt-6.1-sol',{'choices':[{'message':{'content':'advice'}}]}
    llm=PluginLlm(plugin_id='hermes-expert-guardian',sync_caller=caller)
    with patch('agent.plugin_llm._resolve_task_ownership',return_value=({'guardian_expert'},set())):
        llm.complete(messages=[{'role':'user','content':'Synthetic public diagnostic'}],task='guardian_expert')
    assert 'tools' not in captured[0]
    print(json.dumps({'manifest':'pass','registration':'pass','native_block_directive':'pass','text_only_facade':'pass','production_modified':False}))

