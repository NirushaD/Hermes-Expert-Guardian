"""Only documented Hermes plugin APIs; no monkey patches."""
from .service import Guardian
from .state import Store
from pathlib import Path
import json
from .review import Reviews

ID = "hermes-expert-guardian"


def create(ctx=None):
    if ctx is None:
        from hermes_cli.plugins_state import PluginState
        from hermes_cli.config import load_config_readonly
        from agent.plugin_llm import PluginLlm
        state = PluginState(ID)
        def config(key, default):
            return (load_config_readonly().get("plugins", {}).get("entries", {}).get(ID, {})
                    .get("settings", {}).get(key, default))
        llm = PluginLlm(plugin_id=ID)
    else:
        state, config, llm = ctx.state, ctx.get_config, ctx.llm
    data_dir = Path(state.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return Guardian(Store(data_dir / "guardian.sqlite3"), config, llm)


def register(ctx):
    ctx.register_auxiliary_task("guardian_expert", display_name="Expert",
        description="Guardian: validated diagnostic packets only; text-only independent advice",
        defaults={"timeout": 60})
    # Lazy initialization keeps plugin discovery and admission read-only.
    def pre(**kwargs):
        try:
            return create(ctx).pre(**kwargs)
        except Exception:
            if ctx.get_config("mode", "monitor") == "enforce":
                return {"action": "block", "message": "Guardian initialization failed; user intervention required"}
    def post(**kwargs):
        return create(ctx).post(**kwargs)
    def context(**kwargs):
        return create(ctx).context(**kwargs)
    def transform(**kwargs):
        return create(ctx).transform(**kwargs)
    ctx.register_hook("pre_tool_call", pre)
    ctx.register_hook("post_tool_call", post)
    ctx.register_hook("pre_llm_call", context)
    ctx.register_hook("transform_tool_result", transform)
    if hasattr(ctx, "register_tool"):
        def review(args, **kwargs):
            try:
                service = create(ctx)
                # Identity comes only from Hermes, never from model-controlled arguments.
                session = kwargs.get("session_id", "")
                if not isinstance(session, str) or not session:
                    raise ValueError("Host session identity required")
                reviews = Reviews(service)
                if args.get("followup") is True:
                    result = reviews.followup(session, args.get("review_id", ""), args.get("diagnostic", ""),
                                              args.get("expected_round"))
                else:
                    result = reviews.run(
                        session, args.get("diagnostic", "Retrieve review advice"),
                        request_id=args.get("review_id", ""), incident_id=args.get("incident_id", ""),
                        task=kwargs.get("task_id", ""))
                if result["state"] == "ADVICE_READY":
                    with service.store.session(session) as data:
                        item = next(r for r in data["reviews"] if r["id"] == result["review_id"])
                        item["delivered"] = True
                return json.dumps(result)
            except Exception:
                return json.dumps({"state": "REFUSED", "error": "Review unavailable; check Guardian policy, session budget and pending reviews. Do not repeat automatically."})
        ctx.register_tool(name="guardian_review", toolset="guardian", handler=review,
            description="Request independent advice using a locally anonymised diagnostic, or retrieve an existing review. Continue with normal tools and approvals after assessing advice.",
            schema={"name": "guardian_review", "description": "Consult Expert when stuck or when the user requests a review. Supply task, outcome, observations, attempted approaches and question. Never include secrets. Use review_id for pending manual requests and incident_id for loops. If enabled and clarification is needed, continue a conversation using review_id, followup=true, expected_round from the last response and a new diagnostic. Omit followup to retrieve existing advice without sending.",
                    "parameters": {"type": "object", "properties": {
                        "diagnostic": {"type": "string", "maxLength": 16000},
                        "review_id": {"type": "string"}, "incident_id": {"type": "string"},
                        "followup": {"type": "boolean"}, "expected_round": {"type": "integer", "minimum": 1, "maximum": 6}},
                        "additionalProperties": False}})
    # on_session_end is turn-scoped in this runtime: never erase safety state there.
