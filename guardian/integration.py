"""Only documented Hermes plugin APIs; no monkey patches."""
from .service import Guardian
from .state import Store
from pathlib import Path

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
        description="Guardian: approved diagnostic packets only; text-only independent advice",
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
    # on_session_end is turn-scoped in this runtime: never erase safety state there.
