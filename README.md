# Hermes Expert Guardian 0.3.0

**New: bounded Expert conversations.** Enable `expert_conversations` in Agent settings for locally anonymised follow-ups within a review. Set `conversation_max_rounds` (1–6, default 3 including the first reply) and `conversation_approve_each_round` (default on). Every outbound round and its retained conversation history pass the privacy boundary. See [conversation settings](docs/REVIEWS.md).

**New: on-demand and automatic advisory reviews.** Type `Guardian review: assess our current problem and continue after advice`, or use **Request Expert review and continue** in settings. Hermes prepares the problem, the configured local model anonymises it, Expert advises, and Hermes continues under normal approvals. Enable automatic sending and loop/model triggers for unattended consultations. See [review setup, behaviour and limits](docs/REVIEWS.md). This build does not install or publish itself.

A conservative, installable **development release**, implemented against the installed Hermes Agent commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8` on Windows 11. This is not a certification that every requirement of the original specification is complete. Read [limitations](docs/COMPATIBILITY.md) before enforcement.

Default: **monitor-only**, expert escalation disabled. Source is published on `main`. Frontend acceptance evidence and remaining limits are recorded in [frontend testing](docs/FRONTEND-TESTING.md). No infrastructure or credential changes are part of this plugin. Version 0.1.1 separates the installable runtime from development-only tests and scanner evidence.

The Python plugin records bounded operation/result fingerprints per session and objective. After two matching failures, three failed operations in one scope, three configuration rewrites, or five unchanged observations, Enforce mode returns Hermes' supported `{"action":"block","message":"..."}` directive before further dispatch. Native Hermes interprets this as a veto and returns the message as the tool result. Parent context also receives incident state. This is implemented enforcement, not a model instruction. Monitor mode permits execution.

The text-only expert call uses `ctx.llm.complete(task="guardian_expert", ...)`. The plugin registers that auxiliary task as **Expert**, without hard-coded provider or model defaults. Select your preferred configured provider and model in Hermes auxiliary-model settings; otherwise Hermes applies its normal host fallback routing. Existing saved task settings remain effective. It never creates an AIAgent or delegates. The host owns authentication. Expert receives a validated diagnostic packet. New reviews support preview or automatic sending; the older incident recovery workflow requires per-packet approval.

## Development and checks

Requires Python 3.11–3.14 and no additional runtime dependencies beyond Hermes. Desktop backend uses Hermes' existing FastAPI installation.

```powershell
python -m unittest discover -s tests -v
python -m compileall -q guardian dashboard
python package.py
```

For an installed SDK compatibility probe, use its Python with `tests/runtime_probe.py --runtime <hermes-agent source directory>`. The probe uses a temporary HERMES_HOME, synthetic data and a mocked provider. See [test evidence](docs/TESTING.md).

## Legacy incident recovery: installation and testing

1. Review this source and [security review](docs/SECURITY.md). Keep Manual approvals enabled.
2. Use the runtime-only source on `main`: **https://github.com/NirushaD/Hermes-Expert-Guardian/tree/main/release/hermes-expert-guardian**. Hermes supports GitHub subdirectory URLs and scans the selected subtree. Security tests remain in this development repository, with their original synthetic hostile strings intact.
3. Open Hermes Desktop → Settings → Plugins → Manage plugins → Install from Git and enter that full URL. The selected subtree contains `plugin.yaml` and `__init__.py`. The ZIP in `dist/` contains the same runtime-only layout; it is a source archive, not a claimed ZIP-import UI. No scanning override is needed. See [installation scan evidence](docs/INSTALL-SCAN.md).
4. Enable the **agent plugin** for the intended Desktop profile, then enable its Desktop half if separately listed. Restart the backend through Desktop if its auxiliary-model list has not refreshed.
5. Open Settings → Plugins → Expert Guardian → Agent settings. Keep mode `monitor` initially. Thresholds clamp to 2–50. Enable `expert_enabled` only when ready for per-packet approvals.
6. In Desktop auxiliary-model settings choose **Expert** and select your preferred configured provider and model, using Hermes authentication. This is a new auxiliary slot; it does not change Review or the primary model. Do not enter credentials into Guardian descriptions.
7. The Guardian settings page accepts the affected session ID and incident ID. Refresh incidents, enter a minimal public problem and intended outcome, Prepare diagnostic preview, then Refresh incidents again. Review `packet` and click Approve sending preview to Expert. Approval is tied to `packet_hash`; stale approval is refused.
8. Review validated advice and independently compare it with verified evidence. Enter an exact corrective operation as `{"tool":"terminal","args":{"command":"..."}}` plus explicit success criteria. Authorize one attempt. Ask the primary agent to perform that exact operation; the native approval gate is requested again. All corrective operations require approval, including high-risk operations.
9. After an `ok` tool result, the incident remains stopped pending your verification. Only click resolve once the success criteria are met. Errors, denial, invalid advice, low confidence, uncertainty, and unavailable providers leave the incident blocked.
10. Switch to `enforce` only after testing harmless cases in an isolated session. Existing Telegram bridge registrations and settings are untouched.

## Settings and controls

Manifest-generated controls include monitoring thresholds, Expert enablement, timeout and [new review settings](docs/REVIEWS.md). Legacy recovery retains one consultation and one exact corrective attempt per incident. New advisory reviews use a session budget and selectable preview/automatic sending. Expert selection uses Hermes auxiliary-model settings.

The Desktop page provides incident history, packet preview, send approval/denial, recovery authorization, explicit success verification, and reset/history deletion for a session. Session IDs are entered explicitly to avoid selecting the wrong active profile/session. An API objective action exists for integrations, but there is no objective control on the current page. Run local safeguard simulations (no cloud) executes 42 bounded engine checks in the Hermes frontend. These simulations do not replace the complete development suite or live native approval acceptance. The first approved consultation is the live connection check.

## Rollback and uninstall

Disable the **agent plugin** in Manage plugins for the relevant profile; a Desktop-only toggle removes UI and does not guarantee removal of Python hooks. Disable/uninstall both halves through Desktop and restart the backend to retire any in-flight worker. No service, launcher, icon, profile, bridge, or authentication configuration is replaced. Restore the prior plugin version through Manage plugins if desired.

Before uninstalling, use Reset session and delete history if desired. After uninstall, retained data is only `<profile HERMES_HOME>/plugin-data/hermes-expert-guardian/guardian.sqlite3`; delete that plugin-owned directory through the file manager after the backend stops if all history should be removed. Do not delete the profile. The registered auxiliary slot disappears when the plugin unloads; an explicitly saved auxiliary override may remain in Hermes settings.

Read [compatibility](docs/COMPATIBILITY.md), [security](docs/SECURITY.md), and [test results](docs/TESTING.md) for material limits.
