"""Release gates for concurrency, fail-closed recovery and provider-neutral routing."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from types import SimpleNamespace

from guardian.integration import register
from guardian.selftest import run
from guardian.service import Guardian
from guardian.state import Store
from guardian import expert


ADVICE = dict(root_cause="Public fixture typo", confidence=.95, verified_facts=[],
              additional_evidence_required=[], recommended_corrective_action="Read public fixture",
              commands=[], risks=[], rollback_considerations="No writes", user_approval_required=True,
              unresolved=False)


class ReleaseGates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls = []
        class Expert:
            def complete(inner, **kwargs):
                self.calls.append(kwargs)
                return SimpleNamespace(text=json.dumps(ADVICE))
        self.settings = {"mode": "enforce", "expert_enabled": True}
        self.guardian = Guardian(Store(Path(self.tmp.name) / "state.db"),
                                 lambda k, d: self.settings.get(k, d), Expert())
        self.args = {"path": "public-fixture.txt"}

    def prepared(self):
        for _ in range(2):
            self.guardian.post("read_file", self.args, session_id="release", status="error",
                               result={"error": "Synthetic missing fixture"})
        item = self.guardian.view("release")["incidents"][0]
        self.guardian.prepare("release", item["id"], "Public fixture typo", "Read succeeds")
        return self.guardian.view("release")["incidents"][0]

    def armed(self):
        item = self.prepared()
        self.guardian.send("release", item["id"], item["packet_hash"])
        self.guardian.authorize("release", item["id"], "read_file", self.args, "Read succeeds")
        return item

    def test_all_frontend_engine_checks(self):
        result = run()
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(len(result["checks"]), 42)
        self.assertEqual((result["real_tools_executed"], result["cloud_requests"]), (0, 0))

    def test_neutral_registration_preserves_user_routing_key(self):
        class Context:
            def register_auxiliary_task(inner, key, **kwargs):
                inner.key, inner.metadata = key, kwargs
            def register_hook(inner, name, callback):
                pass
        context = Context()
        register(context)
        self.assertEqual(context.key, "guardian_expert")
        self.assertEqual(context.metadata["display_name"], "Expert")
        self.assertEqual(context.metadata["defaults"], {"timeout": 60})

    def test_concurrent_sends_make_one_logical_consultation(self):
        item = self.prepared()
        def send(_):
            try:
                return self.guardian.send("release", item["id"], item["packet_hash"])
            except ValueError:
                return "refused"
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(send, range(8)))
        self.assertEqual(results.count("PROPOSED_FIX"), 1)
        self.assertEqual(results.count("refused"), 7)
        self.assertEqual(len(self.calls), 1)

    def test_changed_preview_invalidates_old_approval(self):
        item = self.prepared()
        self.guardian.prepare("release", item["id"], "Different public evidence", "Read succeeds")
        with self.assertRaises(ValueError):
            self.guardian.send("release", item["id"], item["packet_hash"])
        self.assertEqual(self.calls, [])

    def test_expert_disabled_never_sends(self):
        item = self.prepared()
        self.settings["expert_enabled"] = False
        with self.assertRaises(ValueError):
            self.guardian.send("release", item["id"], item["packet_hash"])
        self.assertEqual(self.calls, [])

    def test_recovery_without_call_identity_does_not_execute(self):
        self.armed()
        result = self.guardian.pre("read_file", self.args, session_id="release")
        self.assertEqual(result["action"], "block")
        self.assertFalse(self.guardian.view("release")["incidents"][0].get("consumed"))

    def test_concurrent_recovery_only_one_native_approval(self):
        self.armed()
        def pre(n):
            return self.guardian.pre("read_file", self.args, session_id="release", tool_call_id=str(n))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            directives = list(pool.map(pre, range(8)))
        self.assertEqual(sum(d["action"] == "approve" for d in directives), 1)
        self.assertEqual(sum(d["action"] == "block" for d in directives), 7)

    def test_denied_recovery_cannot_be_promoted_by_duplicate_callback(self):
        item = self.armed()
        self.guardian.pre("read_file", self.args, session_id="release", tool_call_id="once")
        self.guardian.post("read_file", self.args, session_id="release", tool_call_id="once", status="cancelled")
        self.guardian.post("read_file", self.args, session_id="release", tool_call_id="once", status="ok",
                           result={"success": True})
        with self.assertRaises(ValueError):
            self.guardian.resolve("release", item["id"])
        self.assertFalse(self.guardian.view("release")["incidents"][0]["retry_ok"])

    def test_recovery_success_requires_explicit_resolution(self):
        item = self.armed()
        self.guardian.pre("read_file", self.args, session_id="release", tool_call_id="once")
        self.guardian.post("read_file", self.args, session_id="release", tool_call_id="once", status="ok",
                           result={"success": True})
        self.assertEqual(self.guardian.view("release")["incidents"][0]["state"], "ESCALATE_TO_USER")
        self.assertEqual(self.guardian.pre("read_file", self.args, session_id="release")["action"], "block")
        self.guardian.resolve("release", item["id"])
        self.assertEqual(self.guardian.view("release")["incidents"][0]["state"], "RESOLVED")

    def test_state_error_blocks_in_enforce(self):
        class BrokenStore:
            def session(inner, identity):
                raise RuntimeError("Synthetic state failure")
        self.guardian.store = BrokenStore()
        self.assertEqual(self.guardian.pre("read_file", self.args, session_id="release")["action"], "block")

    def test_process_death_rolls_back_uncommitted_state(self):
        self.prepared()
        # A separate worker dies inside a write transaction. The saved incident
        # must survive; this never launches or terminates a Hermes process.
        worker = """import os, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
db.execute('BEGIN IMMEDIATE')
db.execute('DELETE FROM sessions')
os._exit(17)
"""
        result = subprocess.run([sys.executable, "-c", worker, self.guardian.store.path],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 17)
        reopened = Guardian(Store(self.guardian.store.path), self.guardian.config, self.guardian.llm)
        self.assertEqual(reopened.pre("read_file", self.args, session_id="release")["action"], "block")
        self.assertEqual(len(reopened.view("release")["incidents"]), 1)

    def test_missing_session_identity_blocks_in_enforce(self):
        self.assertEqual(self.guardian.pre("read_file", self.args)["action"], "block")

    def test_rejected_sensitive_response_never_persists(self):
        item = self.prepared()
        self.guardian.llm = SimpleNamespace(complete=lambda **kwargs:
            SimpleNamespace(text=json.dumps(dict(ADVICE, root_cause="password=synthetic-rejected-value"))))
        self.guardian.send("release", item["id"], item["packet_hash"])
        record = self.guardian.view("release")["incidents"][0]
        self.assertEqual(record["expert_failure"], "response_withheld")
        self.assertNotIn("synthetic-rejected-value", json.dumps(record))

    def test_pending_material_evidence_blocks_even_positive_verdict(self):
        item = self.prepared()
        self.guardian.llm = SimpleNamespace(complete=lambda **kwargs: SimpleNamespace(text=json.dumps(
            dict(ADVICE, additional_evidence_required=["Verify the target mapping before acting"])) ))
        self.assertEqual(self.guardian.send("release", item["id"], item["packet_hash"]), "ESCALATE_TO_USER")
        with self.assertRaises(ValueError):
            self.guardian.authorize("release", item["id"], "read_file", self.args, "Read succeeds")

    def test_empty_diagnosis_or_action_rejected(self):
        for field in ("root_cause", "recommended_corrective_action"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                expert.validate_response(dict(ADVICE, **{field: "   "}))

    def test_contract_distinguishes_proposal_from_verified_resolution(self):
        self.armed()
        instructions = self.calls[0]["messages"][0]["content"]
        self.assertIn("does not execute it or resolve the incident", instructions)
        self.assertIn("Never suppress a material evidence gap", instructions)
        self.assertIn("a nonempty list blocks recovery", instructions)

    def test_wrapped_typed_timeout_is_classified_without_exception_text(self):
        try:
            import httpx
        except ImportError:
            self.skipTest("Transport library available in Hermes Python")
        item = self.prepared()
        def timed_out(**kwargs):
            try:
                raise httpx.ReadTimeout("Synthetic transport detail never retained")
            except httpx.ReadTimeout as cause:
                raise RuntimeError("Synthetic wrapper never retained") from cause
        self.guardian.llm = SimpleNamespace(complete=timed_out)
        self.guardian.send("release", item["id"], item["packet_hash"])
        record = self.guardian.view("release")["incidents"][0]
        self.assertEqual(record["expert_failure"], "timeout")
        self.assertNotIn("never retained", json.dumps(record))

    def test_timeout_words_do_not_misclassify_generic_error(self):
        self.assertFalse(expert.is_timeout(RuntimeError("Timeout mentioned in untrusted provider text")))
