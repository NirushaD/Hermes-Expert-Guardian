"""Local-only drafting: bounded inputs, asynchronous claims and safe UI data."""
import json
from pathlib import Path
from contextlib import closing
import queue
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from guardian.service import Guardian
from guardian.state import Store
from guardian import incident_drafts as drafts
from guardian.integration import _draft_after_hook

DRAFT={'problem_statement':'The public fixture could not be read after repeated attempts; the cause is not established.',
       'expected_outcome':'The expected public fixture is read successfully and its content is checked.'}


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'guardian.db')
        self.settings={'mode':'enforce','local_summary_model':'local-test','expert_enabled':False}
        self.g=Guardian(self.store,lambda k,d:self.settings.get(k,d),draft_history=lambda *_:{'history_available':False})
        self.jobs=queue.Queue(maxsize=32)
        self.queue_patch=patch.object(drafts,'_QUEUE',self.jobs)
        self.queue_patch.start();self.addCleanup(self.queue_patch.stop)
        self.start_patch=patch.object(drafts,'_start')
        self.start_patch.start();self.addCleanup(self.start_patch.stop)
        self.local=patch.object(drafts,'local_json',return_value=dict(DRAFT)).start()
        self.addCleanup(patch.stopall)

    def loop(self,session='s',error='Public fixture not found'):
        for _ in range(2):
            self.g.post('read_file',{'path':'public-fixture'},session_id=session,status='error',
                        user_task='Read the public documentation fixture',result={'error':error})
        return self.g.view(session)['incidents'][-1]

    def generate(self):
        job=self.jobs.get_nowait()
        try:drafts.generate(job)
        except Exception:drafts._fail(job,'local_generation_failed')
        return job

    def test_creation_records_trigger_and_hook_queues_without_waiting_for_model(self):
        item=self.loop()
        self.assertEqual(item['draft_status'],'PENDING')
        self.assertTrue(item['problem_statement']);self.assertTrue(item['expected_outcome'])
        _draft_after_hook(self.g,'s')
        self.assertEqual(self.jobs.qsize(),1)
        self.local.assert_not_called()
        self.assertEqual(self.g.pre('read_file',{'path':'public-fixture'},session_id='s')['action'],'block')
        self.generate()
        ready=self.g.view('s')['incidents'][0]
        self.assertEqual(ready['draft_status'],'READY')
        self.assertEqual(ready['problem_statement'],DRAFT['problem_statement'])
        self.assertEqual(ready['expected_outcome'],DRAFT['expected_outcome'])
        self.assertEqual(ready['state'],'BLOCK_RETRIES')
        self.assertEqual(self.g.view('s')['reviews'],[])
        self.assertEqual(ready['draft_evidence'],'recent_tool_context')

    def test_multiple_hook_calls_claim_only_one_job(self):
        self.loop()
        self.g.start_incident_drafts('s');self.g.start_incident_drafts('s')
        self.assertEqual(self.jobs.qsize(),1)
        self.generate();self.g.start_incident_drafts('s')
        self.assertTrue(self.jobs.empty())

    def test_missing_model_falls_back_to_trigger_without_network(self):
        self.settings['local_summary_model']=''
        item=self.loop();self.g.start_incident_drafts('s')
        current=self.g.view('s')['incidents'][0]
        self.assertEqual(current['draft_status'],'UNAVAILABLE')
        self.assertEqual(current['draft_error'],'local_model_not_configured')
        self.local.assert_not_called()
        self.assertTrue(current['problem_statement'])
        self.assertEqual(current['id'],item['id'])

    def test_prepared_packet_is_not_modified_by_late_draft(self):
        item=self.loop();self.g.start_incident_drafts('s')
        self.g.prepare('s',item['id'],'User reviewed problem','User defined outcome')
        before=self.g.view('s')['incidents'][0]
        self.generate();after=self.g.view('s')['incidents'][0]
        self.assertEqual(after['packet'],before['packet'])
        self.assertEqual(after['packet_hash'],before['packet_hash'])
        self.assertEqual(after['state'],'AWAIT_EGRESS_APPROVAL')
        self.assertEqual(after['draft_status'],'READY')

    def test_close_before_or_during_generation_cannot_reopen_incident(self):
        item=self.loop();self.g.start_incident_drafts('s')
        self.g.dismiss('s',item['id'],'Not relevant')
        self.generate();self.local.assert_not_called()
        self.assertEqual(self.g.view('s')['incidents'][0]['draft_status'],'CANCELLED')
        self.loop('other');self.g.start_incident_drafts('other')
        identity=self.g.view('other')['incidents'][0]['id']
        def close(*args,**kwargs):
            self.g.dismiss('other',identity,'Not relevant')
            return DRAFT
        self.local.side_effect=close
        self.generate()
        self.assertEqual(self.g.view('other')['incidents'][0]['state'],'DISMISSED')
        self.assertEqual(self.g.view('other')['incidents'][0]['draft_status'],'CANCELLED')

    def test_deleted_history_is_not_recreated_by_queued_job(self):
        self.loop();self.g.start_incident_drafts('s')
        self.store.delete('s');self.generate()
        self.assertEqual(self.store.incident_index(),[])
        self.local.assert_not_called()

    def test_invalid_or_sensitive_response_stores_only_failure_category(self):
        for response in [{'wrong':'shape'}, {'problem_statement':'password=example','expected_outcome':'Works'},
                         {'problem_statement':'','expected_outcome':'Works'}]:
            self.store.delete('s');item=self.loop();self.g.start_incident_drafts('s')
            self.local.return_value=response;self.generate()
            current=self.g.view('s')['incidents'][0]
            self.assertEqual(current['draft_status'],'FAILED')
            self.assertEqual(current['draft_error'],'local_generation_failed')
            self.assertNotIn('password=example',str(current))
            self.assertEqual(current['state'],'BLOCK_RETRIES')

    def test_transport_failure_is_bounded_and_explicit_retry_can_succeed(self):
        item=self.loop();self.g.start_incident_drafts('s')
        self.local.side_effect=TimeoutError('private provider diagnostic')
        self.generate()
        self.assertNotIn('private provider diagnostic',str(self.g.view('s')))
        self.local.side_effect=None
        self.g.start_incident_drafts('s',item['id'],retry=True);self.generate()
        self.assertEqual(self.g.view('s')['incidents'][0]['draft_status'],'READY')

    def test_queue_capacity_is_bounded(self):
        while not self.jobs.full():self.jobs.put_nowait(None)
        self.loop();self.g.start_incident_drafts('s')
        current=self.g.view('s')['incidents'][0]
        self.assertEqual(current['draft_status'],'FAILED')
        self.assertEqual(current['draft_error'],'queue_full')
        self.local.assert_not_called()

    def test_profile_paths_deduplicate_separately_and_context_is_session_scoped(self):
        self.loop('s',error='First public fixture missing')
        other=Guardian(Store(Path(self.temp.name)/'other.db'),lambda k,d:self.settings.get(k,d))
        for _ in range(2):other.post('terminal',{},session_id='s',status='error',user_task='Different objective',result={'error':'Different public failure'})
        self.g.start_incident_drafts('s');other.start_incident_drafts('s')
        self.assertEqual(self.jobs.qsize(),2)
        self.generate();diagnostic=self.local.call_args.args[2]
        self.assertIn('First public fixture',diagnostic)
        self.assertNotIn('Different objective',diagnostic)

    def test_raw_failure_is_transient_and_sanitized_before_local_request(self):
        item=self.loop(error='password=never-store-this-value')
        self.assertNotIn('never-store-this-value',str(self.g.view('s')))
        self.g.start_incident_drafts('s');self.generate()
        self.assertNotIn('never-store-this-value',self.local.call_args.args[2])
        self.assertNotIn(item['id'],self.local.call_args.args[2])

    def test_legacy_incident_uses_history_and_does_not_auto_retry(self):
        item=self.loop()
        with self.store.session('s') as data:
            for key in ['draft_status','problem_statement','expected_outcome','trigger_explanation']:
                data['incidents'][0].pop(key,None)
            data['incidents'][0]['time']=100
        history=[]
        self.g.draft_history=lambda session,when:history.append((session,when)) or {'history_available':True,'reported_task':'Historical task evidence'}
        self.g.start_incident_drafts('s')
        self.assertTrue(self.jobs.empty())
        self.g.start_incident_drafts('s',item['id']);self.generate()
        self.assertEqual(history,[('s',100)])
        self.assertIn('Historical task evidence',self.local.call_args.args[2])
        self.assertEqual(self.g.view('s')['incidents'][0]['draft_evidence'],'historical_tool_context')

    def test_history_reader_is_read_only_time_bounded_and_chat_scoped(self):
        path=Path(self.temp.name)/'history.db'
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('CREATE TABLE messages (session_id TEXT,role TEXT,content TEXT,tool_name TEXT,timestamp REAL,active INTEGER)')
            db.executemany('INSERT INTO messages VALUES (?,?,?,?,?,1)',[
                ('s','user','Read the public fixture',None,80),('s','tool','Public fixture not found','read_file',95),
                ('s','user','Wrong future goal',None,200),('s','tool','Wrong future error','terminal',200),
                ('other','tool','Wrong other chat','terminal',95)])
        result=drafts.read_history(path,'s',100)
        self.assertTrue(result['history_available'])
        self.assertIn('public fixture',json.dumps(result))
        self.assertNotIn('Wrong',json.dumps(result))
        with closing(sqlite3.connect(path)) as db, db:self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0],5)

    def test_unload_returns_queued_work_to_pending(self):
        import threading
        self.loop();self.g.start_incident_drafts('s')
        with patch.object(drafts,'_STOP',threading.Event()):
            drafts.shutdown()
            self.assertTrue(self.jobs.empty())
            self.assertEqual(self.g.view('s')['incidents'][0]['draft_status'],'PENDING')
            self.assertEqual(self.g.start_incident_drafts('s'),[])
