# Hermes Expert Guardian 0.1.3

Runtime-only plugin package. Default: monitor-only, expert escalation disabled.

Install through Hermes Desktop → Settings → Plugins → Manage plugins → Install from Git:

https://github.com/NirushaD/Hermes-Expert-Guardian/tree/main/release/hermes-expert-guardian

This is the supported Git subdirectory syntax. The repository root retains development tests and evidence. The installer scans all files in this runtime subtree under its standard community-source policy. No scanner exclusions or overrides are required.

Enable the agent plugin for the intended profile and the Desktop interface. Keep Manual approvals and monitor mode during initial testing. Configure the Expert Guardian auxiliary-model slot in Desktop to use openai-codex / gpt-6.1-sol, with Hermes managing authentication. This does not replace Review or the primary model.

In the Guardian settings page, enter the affected session and incident IDs. Refresh incidents, enter a minimal public description and intended outcome, and prepare a diagnostic preview. Refresh again and review the exact packet before approving cloud submission. Do not paste sensitive material. Egress is always manually approved and tied to the preview hash.

Advice has no tools or agent access. Review it against verified evidence, enter the exact corrective operation JSON and success criteria, then authorize one attempt. Native approval is requested before execution. Verify success before resolving. Failure, uncertain advice or unavailable providers leave retries blocked in Enforce mode.

Enforce mode vetoes tool dispatch in the affected scope after deterministic repetition thresholds. Monitor mode reports incidents without vetoing calls. Start with harmless local commands in a fresh session. Existing Telegram bridge handlers and configuration are untouched.

This remains a development release. Live Desktop, hosted-process, provider and Telegram coexistence acceptance tests remain outstanding. Semantic contradiction detection and arbitrary equivalent-shell-command detection are not implemented. Task/file scoping can split incidents; rewrites and polling detection are conservative. Host callback failures and host provider timeout/retry behavior remain host boundaries. Secret detection cannot identify every arbitrary unlabeled secret; review each packet.

Disable/uninstall the agent plugin and Desktop half through Desktop, then restart its backend. Reset a session to release its blocks and delete its history. Optional retained plugin data lives only in the profile's plugin-data/hermes-expert-guardian directory. No service, launcher or infrastructure configuration is installed.

Full source, tests, security review, compatibility limits and scan evidence:

https://github.com/NirushaD/Hermes-Expert-Guardian

