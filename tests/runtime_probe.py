"""Run with the installed Hermes Python and --runtime SOURCE. Uses a throwaway profile."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

parser=argparse.ArgumentParser()
parser.add_argument('--runtime',required=True)
parser.add_argument('--plugin-root',type=Path)
options=parser.parse_args()
workspace=Path(__file__).resolve().parents[1]
root=options.plugin_root.resolve() if options.plugin_root else workspace
sys.dont_write_bytecode=True
sys.path.insert(0,options.runtime)
with tempfile.TemporaryDirectory(dir=workspace/'.reference') as scratch:
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
    assert set(manager._hooks)=={'pre_tool_call','post_tool_call','pre_llm_call','transform_tool_result'}
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
        return 'synthetic-provider','synthetic-expert-model',{'choices':[{'message':{'content':'advice'}}]}
    llm=PluginLlm(plugin_id='hermes-expert-guardian',sync_caller=caller)
    with patch('agent.plugin_llm._resolve_task_ownership',return_value=({'guardian_expert'},set())):
        llm.complete(messages=[{'role':'user','content':'Synthetic public diagnostic'}],task='guardian_expert')
    assert 'tools' not in captured[0]
    # Exercise the installed host's real approval resolver with fake human responses.
    # No tool dispatch, provider call or Desktop profile is involved.
    from hermes_cli.plugins import _get_pre_tool_call_directive_details, _resolve_block_from_details
    advice = dict(root_cause='Synthetic public fixture typo', confidence=.95, verified_facts=[],
                  additional_evidence_required=[], recommended_corrective_action='Read public fixture',
                  commands=[], risks=[], rollback_considerations='No writes', user_approval_required=True,
                  unresolved=False)
    g.llm = SimpleNamespace(complete=lambda **kwargs: SimpleNamespace(text=json.dumps(advice)))
    context.set_config('expert_enabled', True)
    approval_results = {}
    for label, response in [('approved', {'approved':True}), ('denied', {'approved':False}),
                            ('timeout', TimeoutError('Synthetic approval timeout')),
                            ('gate_error', RuntimeError('Synthetic approval failure'))]:
        session='native-'+label
        arguments={'path':'public-fixture.txt'}
        for _ in range(2):
            g.post('read_file',arguments,session_id=session,status='error',result={'error':'Synthetic error'})
        item=g.view(session)['incidents'][0]
        g.prepare(session,item['id'],'Synthetic public fixture typo','Read succeeds')
        item=g.view(session)['incidents'][0]
        g.send(session,item['id'],item['packet_hash'])
        g.authorize(session,item['id'],'read_file',arguments,'Read succeeds')
        with patch('hermes_cli.lifecycle.invoke_hook',side_effect=invoke):
            directive=_get_pre_tool_call_directive_details('read_file',arguments,session_id=session,tool_call_id='once')
        assert directive.action=='approve' and directive.rule_key.startswith('guardian:'+item['id']+':')
        mocked={'side_effect':response} if isinstance(response,Exception) else {'return_value':response}
        with patch('tools.approval.request_tool_approval',**mocked) as approval:
            blocked=_resolve_block_from_details(directive,'read_file',session_id=session,tool_call_id='once')
        assert approval.call_count==1
        assert (blocked is None)==(label=='approved')
        g.post('read_file',arguments,session_id=session,tool_call_id='once',
               status='ok' if label=='approved' else 'blocked',result={'success':label=='approved'})
        assert g.pre('read_file',arguments,session_id=session,tool_call_id='second')['action']=='block'
        if label=='approved':
            g.resolve(session,item['id'])
            assert g.view(session)['incidents'][0]['state']=='RESOLVED'
        else:
            try:
                g.resolve(session,item['id'])
            except ValueError:
                pass
            else:
                raise AssertionError('Unapproved native result resolved')
        approval_results[label]='pass'
    print(json.dumps({'manifest':'pass','registration':'pass','native_block_directive':'pass',
                     'text_only_facade':'pass','native_approval_resolver':approval_results,
                     'real_tools_executed':0,'cloud_requests':0,'production_modified':False}))


