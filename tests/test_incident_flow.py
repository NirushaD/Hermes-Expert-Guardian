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
