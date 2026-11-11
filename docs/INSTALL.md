# Hermes Expert Guardian 0.3.2

Click **Refresh incidents** to populate **Select an incident**. Each option shows the incident ID, reason and state. A sole active incident is selected automatically; multiple active incidents require selection. Selection fills the Incident ID and displays its packet when available. Legacy send approval remains tied to that session, incident and packet hash; refreshing or choosing an incident never sends it.

For a pending review, click **Load / refresh reviews for this session**, select it from the review list and inspect the displayed anonymous packet. A single pending review is selected automatically. **Approve reviewed summary and continue** is enabled only for a loaded AWAIT_SEND packet in the selected session. If the backend exposes no reviews, restart Hermes to load its updated backend. No approval sends automatically on loading or selection.

## Expert conversation settings

In Settings → Plugins → Expert Guardian → Agent settings, enable `expert_conversations` for multi-round advice. `conversation_max_rounds` limits total Expert replies per review (1–6, default 3). `conversation_approve_each_round` defaults to true, requiring preview approval for each follow-up. Turn it off to inherit the main preview/automatic sending policy. Sanitisation is mandatory on every round and cannot be disabled. Conversation mode defaults to off.

Hermes gathers requested evidence locally and sends a follow-up diagnostic through the review tool. Only sanitised summaries and sanitised previous Expert replies form the external conversation; raw transcripts and file contents are not appended automatically. Preview remains advisable for sensitive work because no anonymiser guarantees detection of every private detail.

## New advisory reviews

Building locally does not publish the Git installation URL below or update an installed plugin. The local ZIP in `dist/` contains the runtime tree; ZIP-import UI support is not claimed. Earlier installation scan evidence applies to earlier releases.

Enable the agent and Desktop halves for the correct profile. Enable `expert_enabled`, select Expert in Hermes auxiliary-model settings, and set `local_summary_model` to the exact locally served model ID. The local endpoint defaults to `http://127.0.0.1:1234/v1/chat/completions`; only literal loopback HTTP endpoints are supported, with no proxy, redirect or cloud fallback. Your local server must actually serve a local model.

Set `review_sending_policy=automatic`, `automatic_loop_reviews=true` and `model_requested_reviews=true` for unattended reviews. Defaults retain preview sending with automatic triggers off. Normal Hermes approvals apply to continued processing.

Type `Guardian review: assess our current problem and continue after advice`, or select the session in settings and click **Request Expert review and continue**. The agent prepares a diagnostic, the local model anonymises it, Expert advises, and the agent assesses the advice before continuing. With preview sending, refresh incidents, inspect the chosen review's packet, enter its Review ID and click **Approve reviewed summary and continue**. If no composer accepts the submitted turn, open that session and ask Hermes to continue its pending review.

Budget defaults: 3 reviews per session and a 60-second cooldown. Failed and cancelled requests count. A crash in preparation/sending is not automatically retried; cancel before deliberately requesting another. Automatic loop notices depend on the primary model following the instruction to call `guardian_review`.

Pattern removal and local anonymisation cannot guarantee removal of every personal fact or unlabeled secret. Preview sensitive packets. Raw diagnostic input is not persisted; validated packets/advice remain in history. Live Desktop, installed dispatch and real model/provider acceptance are not established for this build.

Full workflow and limits: https://github.com/NirushaD/Hermes-Expert-Guardian/blob/main/docs/REVIEWS.md

## Legacy incident recovery workflow (0.1.x)

The instructions below describe the older exact-operation recovery controls, which remain available separately. Their mandatory preview/operation approvals do not apply to the new advisory workflow.

Runtime-only plugin package. Default: monitor-only, expert escalation disabled.

Install through Hermes Desktop → Settings → Plugins → Manage plugins → Install from Git:

https://github.com/NirushaD/Hermes-Expert-Guardian/tree/main/release/hermes-expert-guardian

This is the supported Git subdirectory syntax. The repository root retains development tests and evidence. The installer scans all files in this runtime subtree under its standard community-source policy. No scanner exclusions or overrides are required.

Enable the agent plugin for the intended profile and the Desktop interface. Keep Manual approvals and monitor mode during initial testing. In Desktop → Model → Auxiliary models → Expert, select your preferred provider and model. Guardian supplies no provider/model defaults; Hermes uses its normal fallback routing when no selection is saved. Review the destination before approving a packet. Hermes manages authentication. Existing saved guardian_expert selections remain effective. This does not replace Review or the primary model.

In the Guardian settings page, enter the affected session and incident IDs. Refresh incidents, enter a minimal public description and intended outcome, and prepare a diagnostic preview. Refresh again and review the exact packet before approving cloud submission. Do not paste sensitive material. Egress is always manually approved and tied to the preview hash.

Advice has no tools or agent access. Review it against verified evidence, enter the exact corrective operation JSON and success criteria, then authorize one attempt. Native approval is requested before execution. Verify success before resolving. Failure, uncertain advice or unavailable providers leave retries blocked in Enforce mode.

Enforce mode vetoes tool dispatch in the affected scope after deterministic repetition thresholds. Monitor mode reports incidents without vetoing calls. Start with harmless local commands in a fresh session. Existing Telegram bridge handlers and configuration are untouched.

This remains a development release. Live Desktop, hosted-process, provider and Telegram coexistence acceptance tests remain outstanding. Semantic contradiction detection and arbitrary equivalent-shell-command detection are not implemented. Task/file scoping can split incidents; rewrites and polling detection are conservative. Host callback failures and host provider timeout/retry behavior remain host boundaries. Secret detection cannot identify every arbitrary unlabeled secret; review each packet.

Disable/uninstall the agent plugin and Desktop half through Desktop, then restart its backend. Reset a session to release its blocks and delete its history. Optional retained plugin data lives only in the profile's plugin-data/hermes-expert-guardian directory. No service, launcher or infrastructure configuration is installed.

Full source, tests, security review, compatibility limits and scan evidence:

https://github.com/NirushaD/Hermes-Expert-Guardian

