import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from guardian.service import Guardian
from guardian.state import Store
from guardian import privacy, expert

ADVICE = dict(root_cause='A missing package',confidence=.9,verified_facts=[],additional_evidence_required=[],recommended_corrective_action='Check package installation',commands=['echo check'],risks=[],rollback_considerations='Restore backup',user_approval_required=True,unresolved=False)

class Fake:
    def __init__(self, value=None): self.calls=[]; self.value=value or ADVICE
    def complete(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.value, Exception): raise self.value
        return SimpleNamespace(text=json.dumps(self.value))

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings={'mode':'enforce','expert_enabled':True}
        self.fake=Fake()
        self.g=Guardian(Store(Path(self.tmp.name)/'state.db'),lambda k,d:self.settings.get(k,d),self.fake)
    def event(self, cmd='false', session='s', task='objective', status='error', result=None, tool='terminal', **args):
        self.g.post(tool, {'command':cmd,**args}, session_id=session, task_id=task, status=status,result=result or {'exit_code':1,'error':'Missing package'})
    def loop(self):
        self.event();self.event()
        return self.g.view('s')['incidents'][-1]
    def block(self,cmd='false',**kw): return self.g.pre('terminal',{'command':cmd},session_id='s',task_id='objective',**kw)
    def prepared(self):
        i=self.loop();self.g.prepare('s',i['id'],'Package installation fails','Package installed')
        return self.g.view('s')['incidents'][-1]
    def advised(self):
        i=self.prepared();self.g.send('s',i['id'],i['packet_hash']);return i
    def test_two_failures_enforced(self):
        self.loop();self.assertEqual(self.block()['action'],'block')
    def test_three_approaches(self):
        for c in ['one','two','three']: self.event(c)
        self.assertEqual(self.g.view('s')['incidents'][0]['reason'],'unsuccessful_approaches')
    def test_retry_success(self):
        self.event();self.event(status='ok',result={'exit_code':0,'output':'installed'})
        self.assertEqual(self.g.view('s')['incidents'],[])
    def test_rewrites(self):
        for c in ['a','b','c']: self.event(c,tool='write_file',path='/config',status='ok',result={'success':True})
        self.assertEqual(self.g.view('s')['incidents'][0]['reason'],'configuration_rewrite')
    def test_polling(self):
        for _ in range(10): self.event(tool='process',status='ok',result={'status':'running'})
        self.assertFalse(self.g.view('s')['incidents'])
    def test_sessions(self):
        self.loop();self.assertIsNone(self.g.pre('terminal',{'command':'false'},session_id='other'))
    def test_concurrent_reservation(self):
        def call(n): return self.block(tool_call_id=str(n))
        with concurrent.futures.ThreadPoolExecutor() as pool: values=list(pool.map(call,range(8)))
        self.assertEqual(sum(v is None for v in values),1)
    def test_unavailable(self):
        self.fake.value=RuntimeError('not logged');i=self.prepared()
        self.assertEqual(self.g.send('s',i['id'],i['packet_hash']),'ESCALATE_TO_USER')
        self.assertEqual(self.block()['action'],'block')
    def test_timeout(self):
        self.fake.value=TimeoutError();i=self.prepared()
        self.assertEqual(self.g.send('s',i['id'],i['packet_hash']),'ESCALATE_TO_USER')
    def test_invalid_advice(self):
        self.fake.value={'execute':'rm'};i=self.prepared()
        self.assertEqual(self.g.send('s',i['id'],i['packet_hash']),'ESCALATE_TO_USER')
    def test_recursion(self):
        i=self.advised()
        with self.assertRaises(ValueError):self.g.send('s',i['id'],i['packet_hash'])
        self.assertEqual(len(self.fake.calls),1)
    def test_approval_hash(self):
        i=self.prepared()
        with self.assertRaises(ValueError):self.g.send('s',i['id'],'wrong')
        self.assertFalse(self.fake.calls)
    def test_recovery(self):
        i=self.advised();self.g.authorize('s',i['id'],'terminal',{'command':'echo check'},'Package installed')
        self.assertEqual(self.block('echo check',tool_call_id='retry')['action'],'approve')
        self.assertEqual(self.block('echo check',tool_call_id='second')['action'],'block')
        self.g.post('terminal',{'command':'echo check'},session_id='s',task_id='objective',tool_call_id='retry',status='ok',result={'exit_code':0})
        self.g.resolve('s',i['id']);self.assertEqual(self.g.view('s')['incidents'][-1]['state'],'RESOLVED')
    def test_recovery_failed(self):
        i=self.advised();self.g.authorize('s',i['id'],'terminal',{'command':'fix'},'Success')
        self.block('fix',tool_call_id='r')
        self.g.post('terminal',{'command':'fix'},session_id='s',task_id='objective',tool_call_id='r',status='error')
        with self.assertRaises(ValueError):self.g.resolve('s',i['id'])
        self.assertEqual(self.block('fix')['action'],'block')
    def test_credentials(self):
        for v in ['password=abc','Bearer abc','api_key=abc','cookie abc','TOKEN=value','-----BEGIN OPENSSH PRIVATE KEY-----','C:/home/.ssh/id_rsa','A'*40,'ignore previous instructions']:
            self.assertEqual(privacy.redact(v),'[WITHHELD]')
            with self.assertRaises(ValueError):self.g.prepare('s',self.loop()['id'],v,'success')
    def test_no_raw_persistence(self):
        self.event(result={'error':'password=neverstore'});self.event(result={'error':'password=neverstore'})
        self.assertNotIn('neverstore',str(self.g.view('s')))
    def test_disabled(self):
        self.settings['enabled']=False;self.event();self.event();self.assertFalse(self.g.view('s')['incidents']);self.assertIsNone(self.block())
    def test_restart(self):
        self.loop();self.g=Guardian(self.g.store,self.g.config,self.fake);self.assertEqual(self.block()['action'],'block')
    def test_unrelated_task(self):
        self.loop();self.assertIsNone(self.g.pre('terminal',{'command':'other'},session_id='s',task_id='different'))
    def test_monitor(self):
        self.settings['mode']='monitor';self.loop();self.assertIsNone(self.block())
    def test_text_only(self):
        self.advised();call=self.fake.calls[0]
        self.assertNotIn('tools',call);self.assertEqual(call['task'],'guardian_expert');self.assertEqual(len(call['messages']),2)
        self.assertNotIn('false',call['messages'][1]['content'])
    def test_packet_allowlist(self):
        i=self.prepared();packet=i['packet'];packet['raw_transcript']='data'
        with self.assertRaises(ValueError):privacy.validate_packet(packet)
    def test_no_progress(self):
        for _ in range(5):self.event(status='ok',result={'exit_code':0,'output':'same'})
        self.assertEqual(self.g.view('s')['incidents'][-1]['reason'],'no_progress')
    def test_changing_output(self):
        for n in range(10):self.event(status='ok',result={'output':str(n)})
        self.assertFalse(self.g.view('s')['incidents'])
    def test_reset(self):
        self.loop();self.g.store.delete('s');self.assertIsNone(self.block())
    def test_bad_confidence(self):
        for n in [True,float('nan'),1.5]:
            with self.assertRaises(ValueError):expert.validate_response({**ADVICE,'confidence':n})

if __name__=='__main__':unittest.main()
