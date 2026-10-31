# Hermes Expert Guardian 0.1.1

A conservative, installable **development release**, implemented against the installed Hermes Agent commit `d923a5eb487a17c0a68801bba9ef0f56c81040a8` on Windows 11. This is not a certification that every requirement of the original specification is complete. Read [limitations](docs/COMPATIBILITY.md) before enforcement.

Default: **monitor-only**, expert escalation disabled. Source is published on `main`. No production installation, infrastructure action, credential change or cloud request has been performed. Version 0.1.1 separates the installable runtime from development-only tests and scanner evidence.

The Python plugin records bounded operation/result fingerprints per session and objective. After two matching failures, three failed operations in one scope, three configuration rewrites, or five unchanged observations, Enforce mode returns Hermes' supported `{"action":"block","message":"..."}` directive before further dispatch. Native Hermes interprets this as a veto and returns the message as the tool result. Parent context also receives incident state. This is implemented enforcement, not a model instruction. Monitor mode permits execution.

The text-only expert call uses `ctx.llm.complete(task="guardian_expert", ...)`. The plugin registers that auxiliary task with Codex defaults (`openai-codex`, `gpt-6.1-sol`). It never creates an AIAgent or delegates. The host owns authentication. No tool schemas, files, sessions, or credential values are passed to this call. Consultations start only after a user previews and approves the packet in Desktop.

## Development and checks

Requires Python 3.11–3.14 and no additional runtime dependencies beyond Hermes. Desktop backend uses Hermes' existing FastAPI installation.

```powershell
python -m unittest discover -s tests -v
python -m compileall -q guardian dashboard
python package.py
```

For an installed SDK compatibility probe, use its Python with `tests/runtime_probe.py --runtime <hermes-agent source directory>`. The probe uses a temporary HERMES_HOME, synthetic data and a mocked provider. See [test evidence](docs/TESTING.md).

## Installation for testing

1. Review this source and [security review](docs/SECURITY.md). Keep Manual approvals enabled.
2. Use the runtime-only source on `main`: **https://github.com/NirushaD/Hermes-Expert-Guardian/tree/main/release/hermes-expert-guardian**. Hermes supports GitHub subdirectory URLs and scans the selected subtree. Security tests remain in this development repository, with their original synthetic hostile strings intact.
3. Open Hermes Desktop → Settings → Plugins → Manage plugins → Install from Git and enter that full URL. The selected subtree contains `plugin.yaml` and `__init__.py`. The ZIP in `dist/` contains the same runtime-only layout; it is a source archive, not a claimed ZIP-import UI. No scanning override is needed. See [installation scan evidence](docs/INSTALL-SCAN.md).
4. Enable the **agent plugin** for the intended Desktop profile, then enable its Desktop half if separately listed. Restart the backend through Desktop if its auxiliary-model list has not refreshed.
5. Open Settings → Plugins → Expert Guardian → Agent settings. Keep mode `monitor` initially. Thresholds clamp to 2–50. Enable `expert_enabled` only when ready for per-packet approvals.
6. In Desktop auxiliary-model settings choose **Expert Guardian**, verify provider `openai-codex` and model `gpt-6.1-sol`, using the existing Hermes authentication. This is a new auxiliary slot; it does not change Review or the primary model. Do not enter credentials into Guardian descriptions.
7. The Guardian settings page accepts the affected session ID and incident ID. Refresh incidents, enter a minimal public problem and intended outcome, Prepare diagnostic preview, then Refresh incidents again. Review `packet` and click Approve sending preview to Codex. Approval is tied to `packet_hash`; stale approval is refused.
8. Review validated advice and independently compare it with verified evidence. Enter an exact corrective operation as `{"tool":"terminal","args":{"command":"..."}}` plus explicit success criteria. Authorize one attempt. Ask the primary agent to perform that exact operation; the native approval gate is requested again. All corrective operations require approval, including high-risk operations.
9. After an `ok` tool result, the incident remains stopped pending your verification. Only click resolve once the success criteria are met. Errors, denial, invalid advice, low confidence, uncertainty, and unavailable providers leave the incident blocked.
10. Switch to `enforce` only after testing harmless cases in an isolated session. Existing Telegram bridge registrations and settings are untouched.

## Settings and controls

Manifest-generated controls: enabled, monitor/enforce, identical failures, unsuccessful approaches, no-progress threshold, expert enabled, timeout (5–180 seconds). The maximum is fixed at one expert consultation and one corrective attempt per incident. Egress approval is mandatory; automatic sending is intentionally unavailable. Provider/model selection uses the supported auxiliary-model settings rather than duplicate text fields.

The Desktop page provides incident history, packet preview, send approval/denial, recovery authorization, explicit success verification, and reset/history deletion for a session. Session IDs are entered explicitly to avoid selecting the wrong active profile/session. An API objective action exists for integrations, but there is no objective control on the current page. A dedicated connection-test button and loop-test button are not implemented; use the synthetic tests before rollout. The first approved consultation is the live connection check.

## Rollback and uninstall

Disable the **agent plugin** in Manage plugins for the relevant profile; a Desktop-only toggle removes UI and does not guarantee removal of Python hooks. Disable/uninstall both halves through Desktop and restart the backend to retire any in-flight worker. No service, launcher, icon, profile, bridge, or authentication configuration is replaced. Restore the prior plugin version through Manage plugins if desired.

Before uninstalling, use Reset session and delete history if desired. After uninstall, retained data is only `<profile HERMES_HOME>/plugin-data/hermes-expert-guardian/guardian.sqlite3`; delete that plugin-owned directory through the file manager after the backend stops if all history should be removed. Do not delete the profile. The registered auxiliary slot disappears when the plugin unloads; an explicitly saved auxiliary override may remain in Hermes settings.

Read [compatibility](docs/COMPATIBILITY.md), [security](docs/SECURITY.md), and [test results](docs/TESTING.md) for material limits.
