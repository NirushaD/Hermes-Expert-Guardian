"""Explicit frontend-triggered simulations; no real tools, provider or profile data."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace
import json
from .service import Guardian
from . import detection, privacy


class MemoryStore:
    def __init__(self):
        self.records = {}

    @contextmanager
    def session(self, identity):
        data = deepcopy(self.records.get(identity, {"events": [], "incidents": [], "pending": {}, "objective": ""}))
        yield data
        self.records[identity] = data


def run():
    """Exercise shipped engine code with synthetic observations and a fake expert."""
    checks = []

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})

    advice = {"root_cause": "Synthetic missing resource", "confidence": .9,
              "verified_facts": [], "additional_evidence_required": [],
              "recommended_corrective_action": "Read the public fixture", "commands": [],
              "risks": [], "rollback_considerations": "No changes", "user_approval_required": True,
              "unresolved": False}
    requests = []

    class FakeExpert:
        def complete(self, **kwargs):
            requests.append(kwargs)
            return SimpleNamespace(text=json.dumps(advice))

    settings = {"mode": "enforce", "expert_enabled": True}
    guardian = Guardian(MemoryStore(), lambda k, d: settings.get(k, d), FakeExpert())
    arguments = {"path": "public-fixture.txt"}
    for _ in range(2):
        guardian.post("read_file", arguments, session_id="simulation", task_id="goal",
                      status="error", result={"error": "Synthetic missing resource"})
    item = guardian.view("simulation")["incidents"][0]
    check("two identical failures", item["attempts"] == 2)
    check("retry veto directive", guardian.pre("read_file", arguments, session_id="simulation", task_id="goal")["action"] == "block")
    check("session isolation", guardian.pre("read_file", arguments, session_id="other", task_id="goal") is None)
    notice = guardian.transform("read_file", arguments, result={"error": "Synthetic"}, session_id="simulation", task_id="goal")
    check("immediate model notice", json.loads(notice)["guardian_notice"]["incident_id"] == item["id"])
    settings["mode"] = "monitor"
    check("monitor permits tools", guardian.pre("read_file", arguments, session_id="simulation", task_id="goal") is None)
    try:
        guardian.authorize("simulation", item["id"], "read_file", arguments, "Read succeeds")
        check("monitor cannot arm recovery", False)
    except ValueError:
        check("monitor cannot arm recovery", True)
    settings["mode"] = "enforce"
    check("sensitive text withheld", privacy.redact("password=synthetic") == "[WITHHELD]")
    guardian.prepare("simulation", item["id"], "Synthetic repeated missing resource", "Read succeeds")
    item = guardian.view("simulation")["incidents"][0]
    try:
        guardian.send("simulation", item["id"], "unapproved")
        check("exact packet approval", False)
    except ValueError:
        check("exact packet approval", not requests)
    guardian.send("simulation", item["id"], item["packet_hash"])
    check("text-only fake request", len(requests) == 1 and "tools" not in requests[0])
    try:
        guardian.send("simulation", item["id"], item["packet_hash"])
        check("one consultation", False)
    except ValueError:
        check("one consultation", len(requests) == 1)
    guardian.authorize("simulation", item["id"], "read_file", arguments, "Read succeeds")
    first = guardian.pre("read_file", arguments, session_id="simulation", task_id="goal", tool_call_id="once")
    second = guardian.pre("read_file", arguments, session_id="simulation", task_id="goal", tool_call_id="again")
    check("one recovery plus native approval directive", first["action"] == "approve" and second["action"] == "block")
    guardian.post("read_file", arguments, session_id="simulation", task_id="goal", tool_call_id="once", result={"success": True})
    guardian.resolve("simulation", item["id"])
    check("explicit success verification", guardian.view("simulation")["incidents"][0]["state"] == "RESOLVED")
    check("literal read-only command normalization", detection.operation("terminal", {"command": "cat  'public file'"}) == detection.operation("terminal", {"command": 'cat "public file"'}))
    check("shell comments preserve exact identity", detection.operation("terminal", {"command": "cat file #note"}) != detection.operation("terminal", {"command": "cat file '#note'"}))
    guardian.post("read_file", arguments, session_id="evidence", status="error", result={"error": "File not found: public-fixture.txt"})
    contradiction = guardian.pre("patch", arguments, session_id="evidence")
    check("typed missing-file contradiction veto", contradiction and contradiction["action"] == "block" and guardian.view("evidence")["incidents"][0]["reason"] == "contradiction")
    for error_name, error in (("unavailable", RuntimeError("Synthetic unavailable")), ("timeout", TimeoutError("Synthetic timeout"))):
        class FailingExpert:
            def complete(self, **kwargs):
                raise error
        guardian.llm = FailingExpert()
        for _ in range(2):
            guardian.post("read_file", arguments, session_id=error_name, status="error", result={"error": "Synthetic error"})
        failure = guardian.view(error_name)["incidents"][0]
        guardian.prepare(error_name, failure["id"], "Synthetic local failure", "Read succeeds")
        failure = guardian.view(error_name)["incidents"][0]
        guardian.send(error_name, failure["id"], failure["packet_hash"])
        check(error_name + " stops safely", guardian.view(error_name)["incidents"][0]["state"] == "ESCALATE_TO_USER")
    return {"simulation_only": True, "real_tools_executed": 0, "cloud_requests": 0,
            "passed": all(c["passed"] for c in checks), "checks": checks}
