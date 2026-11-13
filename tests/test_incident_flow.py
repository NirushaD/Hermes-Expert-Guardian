"""Outcome verification for the guided incident journey."""
from pathlib import Path
import tempfile
import unittest

from guardian.service import Guardian
from guardian.state import Store
from guardian.review import Reviews
from tests.test_guardian import Fake
from tests.test_reviews import SUMMARY


class IncidentFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'state.db')
        self.settings = dict(mode='enforce', expert_enabled=True, automatic_loop_reviews=True,
                             review_sending_policy='automatic', review_cooldown=0)
        self.g = Guardian(self.store, lambda k,d: self.settings.get(k,d), Fake())

    def loop(self):
        for _ in range(2):
            self.g.post('terminal', {'command':'public-check'}, session_id='s', status='error')
        return self.g.view('s')['incidents'][-1]

    def reviewed(self):
        item = self.loop()
        Reviews(self.g, lambda *_: dict(SUMMARY)).run('s', 'Public diagnostic', incident_id=item['id'])
        return self.g.view('s')['incidents'][-1]

    def test_advisory_outcome_requires_verification_and_survives_reopen(self):
        item = self.reviewed()
        self.assertEqual(item['state'], 'REVIEWED')
        self.assertNotIn('user_verified', item)
        with self.assertRaises(ValueError):
            self.g.resolve('s', item['id'])
        self.g.resolve('s', item['id'], 'Package check returned the expected version')
        reopened = Guardian(Store(self.store.path)).view('s')['incidents'][-1]
        self.assertEqual(reopened['state'], 'RESOLVED')
        self.assertTrue(reopened['user_verified'])
        self.assertEqual(reopened['verification'], 'Package check returned the expected version')
        self.assertEqual(reopened['transitions'][-1], 'RESOLVED')
        with self.assertRaises(ValueError):
            self.g.resolve('s', item['id'], 'Duplicate')

    def test_still_unresolved_keeps_advisory_incident_open(self):
        item = self.reviewed()
        self.g.unresolved('s', item['id'])
        current = self.g.view('s')['incidents'][-1]
        self.assertEqual(current['state'], 'REVIEWED')
        self.assertTrue(current['outcome_unresolved'])
        self.assertFalse(current['user_verified'])
        self.g.resolve('s', item['id'], 'A later check confirmed the intended outcome')
        self.assertFalse(self.g.view('s')['incidents'][-1]['outcome_unresolved'])
        with self.assertRaises(ValueError):
            self.g.unresolved('s', item['id'])

    def test_evidence_note_cannot_bypass_failed_or_unattempted_recovery(self):
        item = self.loop()
        with self.assertRaises(ValueError):
            self.g.resolve('s', item['id'], 'A claim without a corrective result')
        with self.assertRaises(ValueError):
            self.g.unresolved('s', item['id'])
        self.g.prepare('s', item['id'], 'Public problem', 'Expected result')
        prepared = self.g.view('s')['incidents'][-1]
        self.g.send('s', item['id'], prepared['packet_hash'])
        self.g.authorize('s', item['id'], 'terminal', {'command':'public-fix'}, 'Check succeeds')
        self.g.pre('terminal', {'command':'public-fix'}, session_id='s', tool_call_id='one')
        self.g.post('terminal', {'command':'public-fix'}, session_id='s', tool_call_id='one', status='error')
        with self.assertRaises(ValueError):
            self.g.resolve('s', item['id'], 'Claimed success')
        self.assertFalse(self.g.view('s')['incidents'][-1]['retry_ok'])

    def test_verification_rejects_sensitive_or_oversized_notes(self):
        item = self.reviewed()
        for note in ['password=example', 'x' * 801, None]:
            with self.subTest(note_type=type(note).__name__), self.assertRaises(ValueError):
                self.g.resolve('s', item['id'], note)
        self.assertNotIn('verification', self.g.view('s')['incidents'][-1])

    def test_closing_older_review_does_not_clear_new_incident_evidence(self):
        older = self.reviewed()
        newer = self.loop()
        self.assertNotEqual(older['id'], newer['id'])
        with self.store.session('s') as data:
            before = list(data['events'])
        self.g.resolve('s', older['id'], 'Earlier outcome checked separately')
        with self.store.session('s') as data:
            self.assertEqual(data['events'], before)
        self.assertEqual(self.g.view('s')['incidents'][-1]['state'], 'BLOCK_RETRIES')
        self.assertEqual(self.g.pre('terminal', {'command':'public-check'}, session_id='s')['action'], 'block')

    def test_handoff_uses_exact_review_once_without_new_consultation(self):
        item = self.reviewed()
        review_id = item['review_id']
        self.g.handoff('s', 'continue_review', review_id)
        context = self.g.context(session_id='s')['context']
        self.assertIn(review_id, context)
        self.assertIn('internal routing only', context)
        self.assertIn('continue_review', context)
        self.assertNotIn('Guardian selected action', (self.g.context(session_id='s') or {}).get('context',''))
        self.assertEqual(len(self.g.view('s')['reviews']), 1)

    def test_handoff_refuses_wrong_state_unknown_intent_and_other_session(self):
        item = self.loop()
        for session, intent, identity in [('s','execute_action',item['id']),('other','investigate',item['id']),('s','unknown',item['id'])]:
            with self.subTest(intent=intent), self.assertRaises((ValueError,StopIteration)):
                self.g.handoff(session,intent,identity)
        with self.store.session('s') as data:
            self.assertNotIn('ui_handoff',data)
        self.g.handoff('s','investigate',item['id'])
        self.assertIn(item['id'],self.g.context(session_id='s')['context'])

    def test_pause_message_has_no_backend_identifiers_or_state_codes(self):
        item = self.loop()
        message=self.g.pre('terminal',{'command':'public-check'},session_id='s')['message']
        self.assertIn('Repeated failures',message)
        self.assertNotIn(item['id'],message)
        self.assertNotIn('BLOCK_RETRIES',message)
        self.assertNotIn('identical_failure',message)

    def test_incident_index_is_read_only_and_omits_full_records(self):
        item=self.loop()
        self.g.prepare('s',item['id'],'Public test problem','Expected outcome')
        with self.store.session('s') as data:
            original=dict(data)
        index=self.store.incident_index()
        self.assertEqual(len(index),1)
        self.assertEqual(index[0]['session'],'s')
        self.assertEqual(index[0]['incidents'][0]['id'],item['id'])
        self.assertEqual(index[0]['incidents'][0]['state'],'AWAIT_EGRESS_APPROVAL')
        for key in ['packet','packet_hash','scope','advice','retry_op']:
            self.assertNotIn(key,index[0]['incidents'][0])
        self.assertEqual(self.store.incident_index(),index)
        with self.store.session('s') as data:
            self.assertEqual(data,original)

    def test_incident_index_tracks_separate_chats_and_resolution(self):
        item=self.reviewed()
        for _ in range(2):
            self.g.post('terminal',{'command':'other-check'},session_id='other',status='error')
        self.g.resolve('s',item['id'],'Verified the expected outcome')
        indexed={entry['session']:entry['incidents'] for entry in self.store.incident_index()}
        self.assertEqual(indexed['s'][0]['state'],'RESOLVED')
        self.assertEqual(indexed['other'][0]['state'],'BLOCK_RETRIES')
