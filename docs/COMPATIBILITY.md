# Compatibility assessment — 1 November 2026

Inspected installed source commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8`. Its pyproject version is the placeholder `0.0.0`, so the commit is the meaningful runtime identity. The Desktop application executable version was not established; frontend runtime smoke testing remains required.

| Surface | Evidence and status |
|---|---|
| Python plugin registration | Installed `hermes_cli/plugins.py`: register_hook and register_auxiliary_task; real registration probe passes |
| Enforcement | `_get_pre_tool_call_directive_details` recognizes block and approve; native block resolver tested with actual Guardian hook |
| post_tool_call | Observational; result/status/identity fields verified in installed model_tools.py; never used as a veto |
| pre_llm_call | Returns context for the next parent turn; not a dispatch block |
| Auxiliary expert | Documented ctx.llm facade; auxiliary task owned by plugin; host auth and no tool parameter; facade probe passes |
| Desktop | Unified desktop/plugin.js plus dashboard backend supported; official Desktop surface admission passes; live UI untested |
| Windows | Python 3.14.7 local unit tests; explicit SQLite close fixes Windows lock handling |
| LM Studio | Uses ordinary tool lifecycle; no LM Studio connection exercised |
| Codex | Existing root Review provider/model observed; actual external call deliberately not made |
| Telegram bridge | Existing enabled plugin observed; Guardian registers no platform/message handlers and changes no bridge settings; simultaneous live operation untested |
| Manual approval | Desktop profile `approvals.mode: manual` observed; recovery returns supported approve directive; live approval UX untested |
| Host isolation | Official admission classifies package host-ready; full hosted RPC/UI round trip untested |

Actual settings: Desktop profile primary `lmstudio / google/gemma-4-26b-a4b-qat`; root primary and Review `openai-codex / gpt-6.1-sol`. No explicit Desktop auxiliary review configuration was present. Intended 30 agent steps, 15 subagent turns, one parallel subagent, 180 seconds and enabled redaction were not established from explicit saved keys. They are not reported as verified effective settings. No defaults or intended values were written back.

## Material limits

- Exact structured operation fingerprints with outer command whitespace normalization are implemented. Arbitrary shell-equivalence detection is not: resolving Linux interface aliases or equivalent remote scripts safely requires domain-specific adapters.
- Different failed approaches are grouped by session plus task/objective and file target. Without an explicit objective, a changing task_id or different file target may split the same real-world issue; broad objectives can group unrelated commands. The plugin is a loop guard, not a complete command sandbox. Wrappers, indirect scripts and tools that omit lifecycle hooks can bypass operation-level grouping. Subagent session state is separate, not a shared global incident.
- Contradictions between natural-language assumptions and verified infrastructure facts are **not implemented**. Reliably extracting trusted facts and binding assumptions to operations needs a typed evidence adapter; no claim of semantic contradiction enforcement is made.
- Rewrites are conservatively detected from write_file/patch counts per target, not semantic configuration analysis. Shell-based edits are ordinary command fingerprints. Polling exemptions cover process/status/wait and structured running/pending; other long-running workflows may need threshold tuning.
- Successful tool exit is not proof of objective completion. The user verifies success against criteria. Evidence consistency is also explicitly reviewed by the user; automatic expert-command evidence validation is not implemented.
- One consultation and one corrective tool call are enforced; multi-command shell strings are still one tool call. Native approval is requested for every recovery. Existing Hermes approval allowlists remain host policy; Guardian does not rewrite them.
- Cloud approval is manual and consultations are user-triggered after automatic detection/blocking. Automatic-send mode is absent. This intentionally limits autonomous expert escalation in the initial release.
- A timeout is passed to the supported host API. Host provider retry/fallback and queueing semantics can exceed wall-clock timeout; no claim of hard cancellation of host requests. Provider transport can retry a single logical consultation. Failures leave blocks intact.
- Incident persistence survives turns/restarts. on_session_end is turn-scoped, so clearing there would defeat enforcement. Terminal session closure cleanup is unavailable here; explicit reset and 30-day inactive resolved-record expiry are provided. Unresolved blocks are retained. Maximum 512 session records, 64 events/incidents per session, 128 pending calls; reaching capacity requires user cleanup and blocks in Enforce mode.
- Reset deliberately releases blocks and deletes history. Mode/enable settings are user controls, not security barriers against code running with local account privileges.
- No live Desktop UI, real Codex connection, bridge integration, or Proxmox test has been performed. This is a tested development release, not a claim of complete production acceptance.

The installed runtime also has built-in tool-loop guardrails (`agent/agent_init.py` loads `agent.tool_loop_guardrails`). Guardian does not disable or replace those. Native guardrails and approvals continue independently.

Official references (installed files, rather than web latest, governed implementation):

- https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
- https://hermes-agent.nousresearch.com/docs/developer-guide/observer-hooks
- https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access
- https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk
- https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation

Delegation is deliberately unused: it creates child agents with inherited tools. The smallest safe alternative is the supported single text-only auxiliary completion used here.
