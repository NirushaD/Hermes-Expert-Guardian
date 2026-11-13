"""Incident enforcement and bounded recovery. Desktop controls are never model tools."""
import copy
import json
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
        if tool_name == "guardian_review":
            return None  # Advisory tool has its own session/policy/budget checks.
        if not self.enabled():
            return None
        if not session_id:
            return {"action": "block", "message": "Guardian requires session identity"} if self.enforce() else None
        try:
            with self.store.session(session_id) as data:
                scope = self.scope(data, task_id, tool_name, args)
                op = detection.operation(tool_name, args)
                evidence = data.get("file_evidence", {}).get(privacy.digest(args.get("path", args.get("file_path", ""))))
                if tool_name == "patch" and evidence and evidence["exists"] is False and time.time()-evidence["time"] < 1800:
                    if not any(i["scope"] == scope and i["state"] in ACTIVE for i in data["incidents"]):
                        data["incidents"].append({"id": uuid.uuid4().hex[:12], "scope": scope, "reason": "contradiction",
                            "state": "BLOCK_RETRIES", "attempts": 1, "escalations": 0, "time": time.time(),
                            "transitions": ["NORMAL", "LOOP_CONFIRMED", "BLOCK_RETRIES"]})
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
                        return {"action": "approve", "message": "Guardian: approve this single corrective attempt",
                                "rule_key": "guardian:" + incident["id"] + ":" + op}
                    return {"action": "block", "message": f"Guardian incident {incident['id']}: {incident['reason']}; {incident['state']}. " + self.review_instruction(incident)}
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
        if tool_name == "guardian_review":
            return
        if not self.enabled() or not session_id:
            return
        with self.store.session(session_id) as data:
            data["pending"].pop(tool_call_id, None)
            scope = self.scope(data, task_id, tool_name, args)
            op = detection.operation(tool_name, args)
            active = next((i for i in reversed(data["incidents"]) if i["state"] in ACTIVE and
                           (i["scope"] == scope or (tool_call_id and i.get("retry_call") == tool_call_id))), None)
            if active:
                if active.get("consumed") and active.get("retry_call") == tool_call_id and not active.get("retry_finished"):
                    active["retry_finished"] = True
                    active["state"] = "ESCALATE_TO_USER"  # Explicit success verification is still required.
                    active["retry_ok"] = status == "ok" and not detection.failed(result, status)
                return
            if status in ("blocked", "cancelled"):
                return
            # Typed local evidence adapter: a patch requires a file to exist.
            # Only an error-classified read with the tool's exact missing-file
            # error establishes absence. Ordinary file text never establishes it.
            target = args.get("path", args.get("file_path"))
            if tool_name in {"read_file", "write_file"} and isinstance(target, str):
                decoded = result
                if isinstance(result, str):
                    try:
                        decoded = json.loads(result)
                    except ValueError:
                        decoded = None
                missing = (tool_name == "read_file" and status == "error" and isinstance(decoded, dict)
                           and isinstance(decoded.get("error"), str) and decoded["error"].startswith("File not found:"))
                if missing or (status == "ok" and not detection.failed(result, status)):
                    evidence = data.setdefault("file_evidence", {})
                    evidence[privacy.digest(target)] = {"exists": not missing, "time": time.time()}
                    data["file_evidence"] = dict(list(evidence.items())[-64:])
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
            return copy.deepcopy({"incidents": data["incidents"], "reviews": data.get("reviews", []), "objective": data["objective"], "mode": self.config("mode", "monitor")})

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
        failure_code = None
        try:
            timeout = self.config("expert_timeout", 60)
            timeout = max(5, min(180, timeout)) if type(timeout) is int else 60
            advice = expert.consult(self.llm, payload, timeout)
            state = "PROPOSED_FIX" if (advice["confidence"] >= .8 and not advice["unresolved"]
                                      and not advice["additional_evidence_required"]) else "ESCALATE_TO_USER"
        except expert.ResponseRejected as error:
            advice, state = None, "ESCALATE_TO_USER"
            failure_code = error.code
        except TimeoutError:
            advice, state = None, "ESCALATE_TO_USER"
            failure_code = "timeout"
        except Exception as error:
            advice, state = None, "ESCALATE_TO_USER"
            failure_code = "timeout" if expert.is_timeout(error) else "provider_error"
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if item["state"] == "EXPERT_CONSULTATION":
                item["advice"], item["state"] = advice, state
                if failure_code:
                    item["expert_failure"] = failure_code
                item["transitions"] += ["EXPERT_CONSULTATION", state]
        return state

    def authorize(self, session, identity, tool, args, success_criteria):
        if not self.enabled() or not self.enforce():
            raise ValueError("Recovery requires enabled Enforce mode")
        if not isinstance(tool, str) or not tool or not isinstance(args, dict):
            raise ValueError("Exact tool name and argument object required")
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

    def resolve(self, session, identity, verification=""):
        privacy.safe_text(verification, 800)
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if item["state"] == "RESOLVED":
                raise ValueError("Incident already resolved")
            if item["state"] == "REVIEWED":
                if not verification.strip():
                    raise ValueError("Describe the verified advisory outcome")
            elif not item.get("retry_ok"):
                raise ValueError("No successful corrective result to verify")
            item["state"] = "RESOLVED"
            item["user_verified"] = True
            item["verification"] = verification.strip()
            item["resolved_at"] = time.time()
            item["outcome_unresolved"] = False
            item["transitions"].append("RESOLVED")
            # Closing an older advisory incident must not clear a newer loop's evidence.
            if not any(i["id"] != identity and i["scope"] == item["scope"] and i["state"] in ACTIVE
                       for i in data["incidents"]):
                data["events"] = [e for e in data["events"] if e["scope"] != item["scope"]]

    def unresolved(self, session, identity):
        with self.store.session(session) as data:
            item = self.find(data, identity)
            if item["state"] != "REVIEWED" and not (item.get("retry_ok") and item["state"] != "RESOLVED"):
                raise ValueError("Incident is not awaiting outcome verification")
            if not item.get("outcome_unresolved"):
                item["transitions"].append("OUTCOME_STILL_UNRESOLVED")
            item["outcome_unresolved"] = True
            item["user_verified"] = False

    def context(self, session_id="", **_):
        if not self.enabled() or not session_id:
            return None
        # A deliberate user phrase creates a manual request; the model tool cannot
        # manufacture this permission through its own arguments.
        message = _.get("user_message", "")
        if isinstance(message, str) and message.strip().lower().startswith("guardian review:"):
            from .review import Reviews
            try:
                Reviews(self).request(session_id)
            except ValueError:
                return {"context": "Guardian manual review request refused: check settings, cooldown or session review budget. Do not retry automatically."}
        view = self.view(session_id)
        items = view["incidents"]
        requests = [r for r in view["reviews"] if r["state"] in {"REQUESTED", "AWAIT_SEND", "ADVICE_READY"} and not r.get("delivered")]
        review_context = ""
        if self.config("model_requested_reviews", False):
            review_context += " If stuck or needing independent advice, call guardian_review with a focused diagnostic."
        if requests:
            review_context += " Guardian reviews: " + json.dumps([
                {"review_id": r["id"], "state": r["state"]} for r in requests])
            review_context += " Call guardian_review with review_id to prepare or retrieve advice, then continue the task."
        active = [i for i in items if i["state"] in ACTIVE]
        if active:
            return {"context": "Expert Guardian: " + str([{k: i[k] for k in ("id", "reason", "state")} for i in active]) +
                    ". " + self.review_instruction(active[-1]) + " Advice: " + str([i.get("advice") for i in active]) + review_context}
        if review_context:
            return {"context": review_context}

    def review_instruction(self, item):
        if self.config("expert_enabled", False) and self.config("automatic_loop_reviews", False) and item["state"] == "BLOCK_RETRIES":
            return ("Call guardian_review with incident_id=" + item["id"] +
                    " and a focused diagnostic of the task, evidence and failed approaches. Do not repeat the failed operation.")
        return "Open plugin settings for user-controlled escalation."

    def transform(self, tool_name, args, result=None, session_id="", task_id="", **_):
        """Attach generated incident facts to the same tool result the model receives."""
        if tool_name == "guardian_review" or not self.enabled() or not session_id:
            return None
        with self.store.session(session_id) as data:
            scope = self.scope(data, task_id, tool_name, args)
            active = [i for i in data["incidents"] if i["scope"] == scope and i["state"] in ACTIVE]
            if not active:
                return None
            item = active[-1]
            notice = {"incident_id": item["id"], "reason": item["reason"], "state": item["state"],
                      "attempts": item["attempts"], "mode": self.config("mode", "monitor"),
                      "message": "Guardian detected repetition. " + self.review_instruction(item)}
            if isinstance(result, dict):
                return json.dumps({**result, "guardian_notice": notice})
            if isinstance(result, str):
                try:
                    decoded = json.loads(result)
                    if isinstance(decoded, dict):
                        return json.dumps({**decoded, "guardian_notice": notice})
                except ValueError:
                    pass
                return result + "\n\nExpert Guardian incident notice: " + json.dumps(notice)
            return json.dumps({"result": result, "guardian_notice": notice}, default=str)
