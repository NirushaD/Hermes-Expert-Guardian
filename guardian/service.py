"""Incident enforcement and bounded recovery. Desktop controls are never model tools."""
import copy
import time
import uuid
from . import detection, expert, privacy

ACTIVE = {"BLOCK_RETRIES", "AWAIT_EGRESS_APPROVAL", "EXPERT_CONSULTATION", "PROPOSED_FIX",
          "AWAIT_ACTION_APPROVAL", "SINGLE_RETRY", "ESCALATE_TO_USER"}


class Guardian:
    def __init__(self, store, config=lambda key, default: default, llm=None):
        self.store, self.config, self.llm = store, config, llm

    def enabled(self):
        return self.config("enabled", True) is True

    def enforce(self):
        return self.config("mode", "monitor") == "enforce"

    def limit(self, key, default):
        value = self.config(key, default)
        return max(2, min(50, value)) if type(value) is int else default

    @staticmethod
    def scope(data, task, tool, args):
        return privacy.digest([data["objective"] or task or tool,
                               args.get("path", args.get("file_path", ""))])

    @staticmethod
    def find(data, identity):
        return next(i for i in data["incidents"] if i["id"] == identity)

    def pre(self, tool_name, args, session_id="", task_id="", tool_call_id="", **_):
        if not self.enabled():
            return None
        if not session_id:
            return {"action": "block", "message": "Guardian requires session identity"} if self.enforce() else None
        try:
            with self.store.session(session_id) as data:
                scope = self.scope(data, task_id, tool_name, args)
                op = detection.operation(tool_name, args)
                if self.enforce() and len(data["incidents"]) >= 64:
                    return {"action": "block", "message": "Guardian incident capacity reached; user must reset session"}
                incident = next((i for i in reversed(data["incidents"]) if i["state"] in ACTIVE and
                                 (i["scope"] == scope or i.get("retry_op") == op)), None)
                if self.enforce() and incident:
                    if tool_call_id and incident["state"] == "SINGLE_RETRY" and incident.get("retry_op") == op and not incident.get("consumed"):
                        incident["consumed"] = True
                        incident["retry_call"] = tool_call_id
                        incident["state"] = "AWAIT_ACTION_APPROVAL"
                        # Every recovery goes through native human approval, regardless of risk classifier.
                        return {"action": "approve", "message": "Guardian: approve this single corrective attempt"}
                    return {"action": "block", "message": f"Guardian incident {incident['id']}: {incident['reason']}; {incident['state']}. Open Expert Guardian settings."}
                if self.enforce() and any(p["op"] == op for p in data["pending"].values()):
                    return {"action": "block", "message": "Guardian: identical operation already in flight"}
                if tool_call_id:
                    if len(data["pending"]) >= 128:
                        return {"action": "block", "message": "Guardian pending-call capacity reached; reset session in settings"} if self.enforce() else None
                    data["pending"][tool_call_id] = {"op": op, "time": time.time()}
            return None
        except Exception:
            return {"action": "block", "message": "Guardian state unavailable; user intervention required"} if self.enforce() else None

    def post(self, tool_name, args, result=None, status="ok", session_id="", task_id="", tool_call_id="", **_):
        if not self.enabled() or not session_id:
            return
        with self.store.session(session_id) as data:
            data["pending"].pop(tool_call_id, None)
            scope = self.scope(data, task_id, tool_name, args)
            op = detection.operation(tool_name, args)
            active = next((i for i in reversed(data["incidents"]) if i["state"] in ACTIVE and
                           (i["scope"] == scope or (tool_call_id and i.get("retry_call") == tool_call_id))), None)
            if active:
                if active.get("consumed") and active.get("retry_call") == tool_call_id:
                    active["state"] = "ESCALATE_TO_USER"  # Explicit success verification is still required.
                    active["retry_ok"] = status == "ok" and not detection.failed(result, status)
                return
            if status in ("blocked", "cancelled"):
                return
            # Process status/poll tools and running jobs are excluded from no-progress classification.
            if tool_name in {"process", "process_status", "wait"} or (isinstance(result, dict) and result.get("status") in {"running", "pending"}):
                return
            event = {"scope": scope, "op": op, "sig": detection.signature(result),
                     "failure": detection.failed(result, status), "rewrite": tool_name in {"write_file", "patch"},
                     "time": time.time()}
            events = [e for e in data["events"] if time.time()-e["time"] < 1800]
            # A changed successful result clears the failed approach window only for its own operation.
            if not event["failure"] and not event["rewrite"] and any(e["op"] == op and e["sig"] != event["sig"] for e in events):
                events = [e for e in events if e["op"] != op]
            events.append(event)
            data["events"] = events[-64:]
            why = detection.reason(data["events"], event, self.limit("identical_failures", 2),
                                   self.limit("unsuccessful_approaches", 3), self.limit("no_progress", 5))
            if why:
                data["incidents"].append({"id": uuid.uuid4().hex[:12], "scope": scope, "reason": why,
                    "state": "BLOCK_RETRIES", "attempts": sum(e["scope"] == scope for e in events),
                    "escalations": 0, "time": time.time(), "transitions": ["NORMAL", "SUSPECTED_LOOP", "LOOP_CONFIRMED", "BLOCK_RETRIES"]})
                # Capacity is enforced before dispatch; never evict an unresolved block.
                if len(data["incidents"]) > 64:
                    data["incidents"] = data["incidents"][:64]

    def view(self, session):
        with self.store.session(session) as data:
            return copy.deepcopy({"incidents": data["incidents"], "objective": data["objective"], "mode": self.config("mode", "monitor")})

    def prepare(self, session, identity, description, outcome):
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if item["escalations"] or item["state"] not in {"BLOCK_RETRIES", "AWAIT_EGRESS_APPROVAL"}:
                raise ValueError("Incident cannot be escalated again")
            item["packet"] = privacy.packet(item, description, outcome)
            item["packet_hash"] = privacy.digest(item["packet"])
            item["state"] = "AWAIT_EGRESS_APPROVAL"
            item["transitions"] += ["PREPARE_DIAGNOSTIC", "AWAIT_EGRESS_APPROVAL"]
            return copy.deepcopy(item["packet"])

    def send(self, session, identity, packet_hash):
        if not self.enabled() or not self.config("expert_enabled", False):
            raise ValueError("Expert escalation is disabled")
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if item["state"] != "AWAIT_EGRESS_APPROVAL" or item["escalations"] or item["packet_hash"] != packet_hash:
                raise ValueError("Fresh packet approval required")
            payload = copy.deepcopy(item["packet"])
            privacy.validate_packet(payload)
            item["escalations"] = 1
            item["state"] = "EXPERT_CONSULTATION"
            item["egress_approved"] = True
        try:
            timeout = self.config("expert_timeout", 60)
            timeout = max(5, min(180, timeout)) if type(timeout) is int else 60
            advice = expert.consult(self.llm, payload, timeout)
            state = "PROPOSED_FIX" if advice["confidence"] >= .8 and not advice["unresolved"] else "ESCALATE_TO_USER"
        except Exception:
            advice, state = None, "ESCALATE_TO_USER"
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if item["state"] == "EXPERT_CONSULTATION":
                item["advice"], item["state"] = advice, state
                item["transitions"] += ["EXPERT_CONSULTATION", state]
        return state

    def authorize(self, session, identity, tool, args, success_criteria):
        privacy.safe_text(success_criteria)
        if not success_criteria.strip():
            raise ValueError("Explicit success criteria required")
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if item["state"] != "PROPOSED_FIX" or item.get("consumed"):
                raise ValueError("No recovery available")
            item["retry_op"] = detection.operation(tool, args)
            item["criteria"] = success_criteria
            item["state"] = "SINGLE_RETRY"
            item["action_approved"] = True
            item["transitions"] += ["AWAIT_ACTION_APPROVAL", "SINGLE_RETRY"]

    def resolve(self, session, identity):
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if not item.get("retry_ok"):
                raise ValueError("No successful corrective result to verify")
            item["state"] = "RESOLVED"
            item["user_verified"] = True
            data["events"] = [e for e in data["events"] if e["scope"] != item["scope"]]

    def context(self, session_id="", **_):
        if not self.enabled() or not session_id:
            return None
        items = self.view(session_id)["incidents"]
        active = [i for i in items if i["state"] in ACTIVE]
        if active:
            return {"context": "Expert Guardian: " + str([{k: i[k] for k in ("id", "reason", "state")} for i in active]) +
                    ". Open plugin settings for user-controlled escalation. Advice: " + str([i.get("advice") for i in active])}
