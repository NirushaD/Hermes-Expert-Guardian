import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import fastapi
        except ImportError:
            raise unittest.SkipTest("FastAPI unavailable outside Hermes; run using Hermes Python")
        path = Path(__file__).resolve().parents[1] / "dashboard" / "plugin_api.py"
        spec = importlib.util.spec_from_file_location("guardian_backend_test", path)
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    def test_empty_session_rejected(self):
        from fastapi import HTTPException
        with patch.object(self.module.integration, "create"), self.assertRaises(HTTPException):
            self.module.action({"action": "send", "session": ""})

    def test_model_controls_not_registered(self):
        # Only browser/backend routes expose egress and recovery authorization.
        from guardian.integration import register
        class Context:
            def __init__(self): self.hooks = []
            def register_hook(self, name, callback): self.hooks.append(name)
            def register_auxiliary_task(self, *args, **kwargs): pass
        ctx = Context()
        register(ctx)
        self.assertEqual(set(ctx.hooks), {"pre_tool_call", "post_tool_call", "pre_llm_call", "transform_tool_result"})

    def test_evidence_confirmation_required(self):
        from fastapi import HTTPException
        with patch.object(self.module.integration, "create") as create, self.assertRaises(HTTPException):
            self.module.action({"session": "s", "incident": "i", "action": "authorize"})
        create.return_value.authorize.assert_not_called()


    def test_http_guided_recovery_through_verified_closure(self):
        import tempfile
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from guardian.service import Guardian
        from guardian.state import Store
        from tests.test_guardian import Fake
        app = FastAPI()
        app.include_router(self.module.router)
        with tempfile.TemporaryDirectory() as scratch:
            g = Guardian(Store(Path(scratch)/'state.db'), lambda k,d: {'mode':'enforce','expert_enabled':True}.get(k,d), Fake())
            for _ in range(2):
                g.post('terminal', {'command':'public-check'}, session_id='s', status='error')
            with patch.object(self.module.integration, 'create', return_value=g), TestClient(app) as client:
                item = client.get('/incident?session=s').json()['incidents'][0]
                identity = {'session':'s','incident':item['id']}
                def action(kind, **extra):
                    return client.post('/action',json={**identity,'action':kind,**extra})
                self.assertEqual(action('resolve',verification='Claimed success').status_code,400)
                self.assertEqual(action('prepare',description='Public check fails',outcome='Check succeeds').status_code,200)
                packet = client.get('/incident?session=s').json()['incidents'][0]
                self.assertEqual(action('send',packet_hash='stale').status_code,400)
                self.assertEqual(action('send',packet_hash=packet['packet_hash']).json()['state'],'PROPOSED_FIX')
                self.assertEqual(action('authorize',tool='terminal',args={'command':'public-fix'},criteria='Check succeeds',evidence_reviewed=True).status_code,200)
                self.assertEqual(g.pre('terminal',{'command':'public-fix'},session_id='s',tool_call_id='attempt')['action'],'approve')
                g.post('terminal',{'command':'public-fix'},session_id='s',tool_call_id='attempt',status='ok',result={'exit_code':0})
                self.assertEqual(action('unresolved').status_code,200)
                self.assertTrue(client.get('/incident?session=s').json()['incidents'][0]['outcome_unresolved'])
                self.assertEqual(action('resolve',verification='The follow-up check matched the expected output').status_code,200)
                closed = client.get('/incident?session=s').json()['incidents'][0]
                self.assertEqual(closed['state'],'RESOLVED')
                self.assertTrue(closed['user_verified'])
                self.assertEqual(action('deny').status_code,400,'A stale stop action must not reopen a closed incident')
                self.assertEqual(action('unresolved').status_code,400)

    def test_handoff_api_validates_selected_record(self):
        from fastapi import HTTPException
        with patch.object(self.module.integration,'create') as create:
            response=self.module.action({'session':'s','action':'handoff','intent':'continue_review','review_id':'selected-review'})
            self.assertEqual(response,{'ok':True})
            create.return_value.handoff.assert_called_once_with('s','continue_review','selected-review')
        with patch.object(self.module.integration,'create') as create:
            create.return_value.handoff.side_effect=ValueError('Stale selection')
            with self.assertRaises(HTTPException):
                self.module.action({'session':'s','action':'handoff','intent':'continue_review','review_id':'stale-review'})

    def test_incident_tree_index_route(self):
        with patch.object(self.module.integration,'create') as create:
            create.return_value.store.incident_index.return_value=[{'session':'chat-key','incidents':[]}]
            self.assertEqual(self.module.incidents(),{'sessions':[{'session':'chat-key','incidents':[]}]})
            create.return_value.store.incident_index.assert_called_once_with()

    def test_dismiss_api_requires_explicit_confirmation(self):
        from fastapi import HTTPException
        with patch.object(self.module.integration,'create') as create:
            with self.assertRaises(HTTPException):
                self.module.action({'session':'s','incident':'i','action':'dismiss','reason':'Not relevant'})
            create.return_value.dismiss.assert_not_called()
            self.assertEqual(self.module.action({'session':'s','incident':'i','action':'dismiss','reason':'Not relevant','confirmed':True}),{'ok':True})
            create.return_value.dismiss.assert_called_once_with('s','i','Not relevant')
