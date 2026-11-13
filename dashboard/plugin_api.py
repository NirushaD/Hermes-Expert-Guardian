"""Authenticated, profile-scoped Desktop API. No control is registered as an agent tool."""
import importlib.util
from pathlib import Path
import sys
from fastapi import APIRouter, HTTPException

# Hermes loads backend files as standalone modules; load our own package with relative imports.
root = Path(__file__).resolve().parents[1]
name = "_expert_guardian_backend"
if name not in sys.modules:
    spec = importlib.util.spec_from_file_location(name, root / "guardian" / "__init__.py",
                                                submodule_search_locations=[str(root / "guardian")])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
integration = importlib.import_module(name + ".integration")
router = APIRouter()


@router.get("/incident")
def incident(session: str):
    return integration.create().view(session)


@router.get("/incidents")
def incidents():
    return {"sessions": integration.create().store.incident_index()}


@router.post("/action")
def action(body: dict):
    try:
        if len(str(body)) > 16000:
            raise ValueError("Oversized action")
        service = integration.create()
        session = body["session"]
        if not isinstance(session, str) or not session or len(session) > 200:
            raise ValueError("Session required")
        kind = body["action"]
        identity = body.get("incident", "")
        if kind == "draft_incident":
            return {"drafts":service.start_incident_drafts(session,identity,retry=True)}
        if kind == "handoff":
            service.handoff(session, body["intent"], body.get("review_id") or identity)
            return {"ok": True}
        if kind == "request_review":
            from importlib import import_module
            return import_module(name + ".review").Reviews(service).request(session)
        if kind == "send_review":
            from importlib import import_module
            return import_module(name + ".review").Reviews(service).send(session, body["review_id"], body["packet_hash"])
        if kind == "cancel_review":
            with service.store.session(session) as data:
                item = next(r for r in data.get("reviews", []) if r["id"] == body["review_id"])
                item["state"] = "CANCELLED"
                item.pop("packet", None)
                item.pop("advice", None)
                item.pop("history", None)
            return {"ok": True}
        if kind == "prepare":
            return service.prepare(session, identity, body["description"], body["outcome"])
        if kind == "send":
            return {"state": service.send(session, identity, body["packet_hash"])}
        if kind == "authorize":
            if body.get("evidence_reviewed") is not True:
                raise ValueError("User must confirm consistency with verified evidence")
            service.authorize(session, identity, body["tool"], body["args"], body["criteria"])
        elif kind == "resolve":
            service.resolve(session, identity, body.get("verification", ""))
        elif kind == "dismiss":
            if body.get("confirmed") is not True:
                raise ValueError("Confirm closing without review")
            service.dismiss(session, identity, body["reason"])
        elif kind == "unresolved":
            service.unresolved(session, identity)
        elif kind == "reset":
            from importlib import import_module
            import_module(name + ".incident_drafts").forget(service,session)
            service.store.delete(session)
        elif kind == "objective":
            from importlib import import_module
            import_module(name + ".privacy").safe_text(body["objective"])
            with service.store.session(session) as data:
                if any(i["state"] not in {"RESOLVED", "DISMISSED"} for i in data["incidents"]):
                    raise ValueError("Reset unresolved incident explicitly before changing objective")
                data["objective"] = body["objective"]
        elif kind == "deny":
            with service.store.session(session) as data:
                item = service.find(data, identity)
                if item["state"] not in {"BLOCK_RETRIES", "AWAIT_EGRESS_APPROVAL"}:
                    raise ValueError("Incident is not awaiting escalation approval")
                item["state"] = "ESCALATE_TO_USER"
                item["transitions"].append("ESCALATE_TO_USER")
        elif kind == "test":
            from importlib import import_module
            return import_module(name + ".selftest").run()
        elif kind not in {"authorize"}:
            raise ValueError("Unknown action")
        return {"ok": True}
    except (ValueError, KeyError, StopIteration, TypeError):
        raise HTTPException(status_code=400, detail="Action refused. Check incident state and privacy constraints.") from None
