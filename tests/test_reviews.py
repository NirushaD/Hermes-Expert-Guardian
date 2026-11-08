import concurrent.futures
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from guardian.service import Guardian
from guardian.state import Store
from guardian.review import Reviews, local_summary, sanitise, validate_summary
from guardian import privacy
from tests.test_guardian import ADVICE, Fake


SUMMARY = dict(problem="Package installation fails", intended_outcome="Package installed",
               observations="The operation returned an error", attempted_approaches="Two installation attempts",
               uncertainties="The dependency state is unknown", question="Which evidence should be checked next?")


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = dict(expert_enabled=True, mode="enforce", model_requested_reviews=True,
                             automatic_loop_reviews=True, review_sending_policy="automatic", review_cooldown=0)
        self.fake = Fake()
        self.g = Guardian(Store(Path(self.tmp.name)/"state.db"), lambda k,d:self.settings.get(k,d), self.fake)
        self.summaries = []
        def summary(config, diagnostic):
            self.summaries.append(diagnostic)
            return dict(SUMMARY)
        self.reviews = Reviews(self.g, summary)

    def test_manual_without_incident_and_advice_returned(self):
        self.settings["model_requested_reviews"] = False
        request = self.reviews.request("a")
        result = self.reviews.run("a", "Private local task context", request["review_id"])
        self.assertEqual(result["state"], "ADVICE_READY")
        self.assertEqual(result["advice"], ADVICE)
        outbound = self.fake.calls[0]["messages"][1]["content"]
        self.assertNotIn("Private local task context", outbound)
        self.assertEqual(json.loads(outbound)["summary"], SUMMARY)
        self.assertEqual(self.g.view("a")["incidents"], [])

    def test_preview_requires_exact_hash_and_can_resume(self):
        self.settings["review_sending_policy"] = "preview"
        result = self.reviews.run("a", "Task context")
        self.assertEqual(result["state"], "AWAIT_SEND")
        self.assertFalse(self.fake.calls)
        item = self.g.view("a")["reviews"][0]
        with self.assertRaises(ValueError): self.reviews.send("a", item["id"], "stale")
        self.assertEqual(self.reviews.send("a", item["id"], item["packet_hash"])["state"], "ADVICE_READY")
        result = self.reviews.run("a", "retrieve", request_id=item["id"])
        self.assertEqual(result["state"], "ADVICE_READY")
        self.assertEqual(len(self.fake.calls), 1)
        with self.assertRaises(ValueError): self.reviews.send("a", item["id"], item["packet_hash"])

    def test_loop_releases_only_its_incident_and_repeated_failures_detected(self):
        for session in ["a", "b"]:
            for _ in range(2):
                self.g.post("terminal", {"command":"fail"}, session_id=session, status="error")
        incident = self.g.view("a")["incidents"][0]
        result = self.reviews.run("a", "Two attempts failed", incident_id=incident["id"])
        self.assertEqual(result["state"], "ADVICE_READY")
        self.assertEqual(self.g.view("a")["incidents"][0]["state"], "REVIEWED")
        self.assertEqual(self.g.view("b")["incidents"][0]["state"], "BLOCK_RETRIES")
        for _ in range(2): self.g.post("terminal", {"command":"fail"}, session_id="a", status="error")
        self.assertEqual(self.g.view("a")["incidents"][-1]["state"], "BLOCK_RETRIES")

    def test_preparation_failure_never_sends_or_persists_raw_text(self):
        def fail(*args): raise RuntimeError("sensitive details")
        result = Reviews(self.g, fail).run("a", "private transcript")
        self.assertEqual(result["state"], "FAILED")
        self.assertFalse(self.fake.calls)
        stored = json.dumps(self.g.view("a"))
        self.assertNotIn("private transcript", stored)
        self.assertNotIn("sensitive details", stored)

    def test_invalid_local_summary_and_expert_failure(self):
        self.assertEqual(Reviews(self.g, lambda *a:{"problem":"bad"}).run("a", "context")["state"], "FAILED")
        self.assertFalse(self.fake.calls)
        self.fake.value = TimeoutError("private transport details")
        self.assertEqual(self.reviews.run("a", "context")["state"], "FAILED")
        self.assertNotIn("private transport details", json.dumps(self.g.view("a")))

    def test_deduplication_and_budget(self):
        request = self.reviews.request("a")
        self.assertEqual(self.reviews.request("a"), request)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _:self.reviews.run("a", "context", request["review_id"]), range(2)))
        self.assertEqual(len(self.fake.calls), 1)
        self.reviews.run("a", "context")
        self.reviews.run("a", "context")
        with self.assertRaises(ValueError): self.reviews.run("a", "context")

    def test_policy_and_session_isolation(self):
        request = self.reviews.request("a")
        with self.assertRaises(StopIteration): self.reviews.run("b", "context", request["review_id"])
        self.settings["model_requested_reviews"] = False
        with self.assertRaises(ValueError): self.reviews.run("b", "context")
        self.assertIsNone(self.g.pre("guardian_review", {}, session_id="a"))

    def test_identifier_removal_and_packet_validation(self):
        text = "Contact jane@example.com at 192.168.1.2 or https://private.example.com\npassword=fixture\nC:\\Users\\Jane\\project"
        cleaned = sanitise(text)
        for identifier in ["jane@example.com", "192.168.1.2", "private.example.com", "fixture", "Jane"]:
            self.assertNotIn(identifier, cleaned)
        with self.assertRaises(ValueError): validate_summary({**SUMMARY, "extra":"bad"})
        with self.assertRaises(ValueError):
            privacy.validate_packet({"review_version":1,"summary":{**SUMMARY,"problem":"user@example.com"}})
        anonymised = sanitise("192.168.1.2 talks to 192.168.1.3 and 192.168.1.2")
        self.assertEqual(anonymised, "[HOST_1] talks to [HOST_2] and [HOST_1]")
        self.assertEqual(sanitise(anonymised), anonymised)
        self.assertEqual(sanitise("[HOST_1] talks to 10.0.0.1"), "[HOST_1] talks to [HOST_2]")

    def test_chat_manual_request_and_loop_notice(self):
        context = self.g.context("a", user_message="Guardian review: assess our current problem")
        self.assertIn("guardian_review", context["context"])
        self.assertEqual(self.g.view("a")["reviews"][0]["trigger"], "manual")
        for _ in range(2): self.g.post("terminal", {"command":"fail"}, session_id="b", status="error")
        notice = json.loads(self.g.transform("terminal", {"command":"fail"}, {}, session_id="b"))
        self.assertIn("guardian_review", notice["guardian_notice"]["message"])

    def test_registered_tool_uses_host_identity_and_delivers_once(self):
        from guardian.integration import register
        class Context:
            def register_auxiliary_task(self, *args, **kwargs): pass
            def register_hook(self, *args): pass
            def register_tool(inner, **kwargs): inner.tool = kwargs
        ctx = Context()
        register(ctx)
        request = self.reviews.request("a")
        handler = ctx.tool["handler"]
        with patch("guardian.integration.create", return_value=self.g), patch("guardian.review.local_summary", return_value=SUMMARY):
            refused = json.loads(handler({"diagnostic":"context", "session_id":"a"}))
            self.assertEqual(refused["state"], "REFUSED")
            result = json.loads(handler({"diagnostic":"context", "review_id":request["review_id"]}, session_id="a"))
        self.assertEqual(result["state"], "ADVICE_READY")
        self.assertTrue(self.g.view("a")["reviews"][0]["delivered"])
        self.assertNotIn(request["review_id"], (self.g.context("a") or {}).get("context", ""))

    def test_cancel_during_consultation_does_not_release_loop(self):
        self.settings["review_sending_policy"] = "preview"
        for _ in range(2): self.g.post("terminal", {"command":"fail"}, session_id="a", status="error")
        incident = self.g.view("a")["incidents"][0]
        self.reviews.run("a", "context", incident_id=incident["id"])
        item = self.g.view("a")["reviews"][0]
        def consult(*args):
            with self.g.store.session("a") as data: data["reviews"][0]["state"] = "CANCELLED"
            return ADVICE
        with patch("guardian.review.expert.consult", side_effect=consult), self.assertRaises(ValueError):
            self.reviews.send("a", item["id"], item["packet_hash"])
        self.assertEqual(self.g.view("a")["incidents"][0]["state"], "BLOCK_RETRIES")

    def test_local_route_refuses_cloud_hostname_credentials_and_redirects(self):
        for endpoint in ["https://example.com/v1/chat/completions", "http://localhost/v1/chat/completions",
                         "http://127.0.0.1@evil.com/v1/chat/completions", "http://127.0.0.1/other"]:
            config = lambda k,d: {"local_summary_url":endpoint,"local_summary_model":"local"}.get(k,d)
            with patch("guardian.review.build_opener") as opener, self.assertRaises(ValueError):
                local_summary(config, "context")
            opener.assert_not_called()
        from guardian.review import NoRedirect
        with self.assertRaises(ValueError): NoRedirect().redirect_request(None)

    def test_local_http_request_has_no_tools_and_uses_sanitised_input(self):
        encoded = json.dumps({"choices":[{"message":{"content":json.dumps(SUMMARY)}}]}).encode()
        config = lambda k,d: {"local_summary_model":"local"}.get(k,d)
        with patch("guardian.review.build_opener") as factory:
            factory.return_value.open.return_value.__enter__.return_value.read.return_value = encoded
            self.assertEqual(local_summary(config, "user@example.com"), SUMMARY)
            request = factory.return_value.open.call_args.args[0]
            body = json.loads(request.data)
            self.assertNotIn("tools", body)
            self.assertNotIn("user@example.com", body["messages"][1]["content"])

    def test_conversations_disabled_by_default(self):
        first = self.reviews.run("a", "initial")
        with self.assertRaises(ValueError):
            self.reviews.followup("a", first["review_id"], "new evidence", 1)
        self.assertEqual(len(self.fake.calls), 1)

    def test_conversation_reuses_only_sanitised_history_and_new_summary(self):
        self.settings.update(expert_conversations=True, conversation_approve_each_round=False)
        self.fake.value = {**ADVICE, "root_cause":"Check reported host admin@example.com"}
        first = self.reviews.run("a", "private initial context")
        self.fake.value = ADVICE
        second = self.reviews.followup("a", first["review_id"], "private follow-up context", 1)
        self.assertEqual(second["round"], 2)
        self.assertEqual(second["followups_remaining"], 1)
        self.assertEqual(len(self.summaries), 2)
        messages = self.fake.calls[-1]["messages"]
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
        outbound = json.dumps(messages)
        for private in ["private initial context", "private follow-up context", "admin@example.com"]:
            self.assertNotIn(private, outbound)
        self.assertEqual(json.loads(messages[1]["content"])["summary"], SUMMARY)
        self.assertIn("[EMAIL_1]", messages[2]["content"])

    def test_conversation_preview_hash_covers_history_and_current_round(self):
        self.settings.update(expert_conversations=True)
        first = self.reviews.run("a", "initial")
        previous_hash = self.g.view("a")["reviews"][0]["packet_hash"]
        second = self.reviews.followup("a", first["review_id"], "new evidence", 1)
        self.assertEqual(second["state"], "AWAIT_SEND")
        self.assertEqual(len(self.fake.calls), 1)
        item = self.g.view("a")["reviews"][0]
        self.assertNotEqual(item["packet_hash"], previous_hash)
        self.assertEqual(item["packet"]["review_version"], 2)
        with self.assertRaises(ValueError): self.reviews.send("a", item["id"], previous_hash)
        self.assertEqual(self.reviews.send("a", item["id"], item["packet_hash"])["state"], "ADVICE_READY")

    def test_conversation_round_limit_and_stale_round(self):
        self.settings.update(expert_conversations=True, conversation_approve_each_round=False, conversation_max_rounds=2)
        first = self.reviews.run("a", "initial")
        second = self.reviews.followup("a", first["review_id"], "new evidence", 1)
        self.assertEqual(second["followups_remaining"], 0)
        with self.assertRaises(ValueError): self.reviews.followup("a", first["review_id"], "duplicate", 1)
        with self.assertRaises(ValueError): self.reviews.followup("a", first["review_id"], "extra", 2)
        self.assertEqual(len(self.fake.calls), 2)

    def test_concurrent_followups_make_only_one_new_call(self):
        self.settings.update(expert_conversations=True, conversation_approve_each_round=False)
        first = self.reviews.run("a", "initial")
        def followup(_):
            try: return self.reviews.followup("a", first["review_id"], "new evidence", 1)
            except ValueError: return {"state":"REFUSED"}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(followup, range(2)))
        self.assertEqual(len(self.fake.calls), 2)
        self.assertEqual(sum(r["state"] == "ADVICE_READY" for r in results), 1)

    def test_followup_local_failure_and_disabled_pending_send(self):
        self.settings.update(expert_conversations=True)
        first = self.reviews.run("a", "initial")
        broken = Reviews(self.g, lambda *args: {"invalid":"private data"})
        self.assertEqual(broken.followup("a", first["review_id"], "private context", 1)["state"], "FAILED")
        self.assertEqual(len(self.fake.calls), 1)
        self.assertNotIn("private context", json.dumps(self.g.view("a")))
        other = self.reviews.run("b", "initial")
        self.reviews.followup("b", other["review_id"], "new evidence", 1)
        item = self.g.view("b")["reviews"][0]
        self.settings["expert_conversations"] = False
        with self.assertRaises(ValueError): self.reviews.send("b", item["id"], item["packet_hash"])
        self.assertEqual(len(self.fake.calls), 2)

    def test_conversation_history_validation_rejects_identifiers(self):
        packet = {"review_version":2, "summary":SUMMARY,
                  "history":[{"summary":SUMMARY, "advice":{**ADVICE, "root_cause":"user@example.com"}}]}
        with self.assertRaises(ValueError): privacy.validate_packet(packet)
        packet["history"][0]["advice"] = ADVICE
        privacy.validate_packet(packet)
        packet["history"] *= 6
        with self.assertRaises(ValueError): privacy.validate_packet(packet)


if __name__ == "__main__": unittest.main()
