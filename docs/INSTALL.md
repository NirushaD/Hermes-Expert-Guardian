# Hermes Expert Guardian 0.5.1

## Follow an incident to completion

1. Open Expert Guardian. The left column lists only chats with at least one open incident, using their readable names. Chats with no incidents or only resolved incidents are hidden. Advice received without verified closure still counts as open. Use **Find a chat by name** to filter them. Expand a chat to see its incidents, statuses and dates. The focused chat is expanded initially. Duplicate names retain readable dates and numbers; internal keys are never displayed.
2. Select an incident in the tree. The right column loads its details, six numbered stages, current status and next actor. No incident is selected implicitly. Selecting an incident only loads information; sending a review or authorizing an action still requires the relevant explicit button. Use **Refresh tree** or **Reload incident** when needed; status also refreshes automatically.
3. In **Review the problem**, describe the public problem and intended outcome, then select **Prepare Expert review**.
4. Read the exact summary under **Approve what Expert will receive**, then select **Approve summary and get advice**. Loading, polling and selection never approve or send a packet. Expert routing is configured in Hermes auxiliary models.
5. Review advice against local evidence. If an exact corrective attempt is available, use **Ask Hermes to prepare the action** for help, then enter its tool and command (or argument object), success criteria and evidence confirmation. **Approve one corrective attempt** asks Hermes to run only that operation; native approval still applies. Exact recovery requires Enforce mode.
6. After a successful corrective result, independently check the outcome, record what you verified, tick the confirmation and select **Confirm resolved**. **Still unresolved** records that the outcome is not achieved and offers investigation without granting another retry.
7. Advisory reviews appear within their linked incident. Advice can release the previous block so Hermes can continue, but the incident remains **Advice received — outcome not verified** until explicit user verification. Closing an older incident does not clear a newer active incident's detector evidence.
8. Uncertain advice, provider failures and failed attempts explain the next investigation step. They cannot be closed through a claimed success note that bypasses corrective-result requirements.

The page reloads status every five seconds. Closed incidents retain the checked outcome and history. Readable incident history and maintenance controls are expandable; **Delete this chat’s Guardian history** is maintenance, not completion. General advice unrelated to an incident and maintenance are collapsed under **Other Guardian tools**.

## Expert conversation settings

In Settings → Plugins → Expert Guardian → Agent settings, enable `expert_conversations` for multi-round advice. `conversation_max_rounds` limits total Expert replies per review (1–6, default 3). `conversation_approve_each_round` defaults to true, requiring preview approval for each follow-up. Turn it off to inherit the main preview/automatic sending policy. Sanitisation is mandatory on every round and cannot be disabled. Conversation mode defaults to off.

Hermes gathers requested evidence locally and sends a follow-up diagnostic through the review tool. Only sanitised summaries and sanitised previous Expert replies form the external conversation; raw transcripts and file contents are not appended automatically. Preview remains advisable for sensitive work because no anonymiser guarantees detection of every private detail.

## New advisory reviews

Building locally does not publish the Git installation URL below or update an installed plugin. The local ZIP in `dist/` contains the runtime tree; ZIP-import UI support is not claimed. Earlier installation scan evidence applies to earlier releases.

Enable the agent and Desktop halves for the correct profile. Enable `expert_enabled`, select Expert in Hermes auxiliary-model settings, and set `local_summary_model` to the exact locally served model ID. The local endpoint defaults to `http://127.0.0.1:1234/v1/chat/completions`; only literal loopback HTTP endpoints are supported, with no proxy, redirect or cloud fallback. Your local server must actually serve a local model.

Set `review_sending_policy=automatic`, `automatic_loop_reviews=true` and `model_requested_reviews=true` for unattended reviews. Defaults retain preview sending with automatic triggers off. Normal Hermes approvals apply to continued processing.

Type `Guardian review: assess our current problem and continue after advice`, or select the session in settings and click **Request Expert advice**. The agent prepares a diagnostic, the local model anonymises it, Expert advises, and the agent assesses the advice before continuing. With preview sending, select the review, inspect its displayed packet and click **Approve summary and get advice**. If no composer accepts the submitted turn, open that session and ask Hermes to continue its pending review.

Budget defaults: 3 reviews per session and a 60-second cooldown. Failed and cancelled requests count. A crash in preparation/sending is not automatically retried; cancel before deliberately requesting another. Automatic loop notices depend on the primary model following the instruction to call `guardian_review`.

Pattern removal and local anonymisation cannot guarantee removal of every personal fact or unlabeled secret. Preview sensitive packets. Raw diagnostic input is not persisted; validated packets/advice remain in history. Live Desktop, installed dispatch and real model/provider acceptance are not established for this build.

Full workflow and limits: https://github.com/NirushaD/Hermes-Expert-Guardian/blob/main/docs/REVIEWS.md

## Legacy incident recovery workflow (0.1.x)

The exact-operation recovery path is now guided within each incident. Its mandatory preview/operation approvals remain distinct from advisory processing under ordinary Hermes approvals.

Runtime-only plugin package. Default: monitor-only, expert escalation disabled.

Install through Hermes Desktop → Settings → Plugins → Manage plugins → Install from Git:

https://github.com/NirushaD/Hermes-Expert-Guardian/tree/main/release/hermes-expert-guardian

This is the supported Git subdirectory syntax. The repository root retains development tests and evidence. The installer scans all files in this runtime subtree under its standard community-source policy. No scanner exclusions or overrides are required.

Enable the agent plugin for the intended profile and the Desktop interface. Keep Manual approvals and monitor mode during initial testing. In Desktop → Model → Auxiliary models → Expert, select your preferred provider and model. Guardian supplies no provider/model defaults; Hermes uses its normal fallback routing when no selection is saved. Review the destination before approving a packet. Hermes manages authentication. Existing saved guardian_expert selections remain effective. This does not replace Review or the primary model.

In Guardian, select the affected task chat and open an incident. Enter a minimal public description and intended outcome, prepare the review and inspect the exact summary before approving cloud submission. Do not paste sensitive material. Egress is always manually approved and tied to the preview hash.

Advice has no tools or agent access. Review it against verified evidence, enter the tool name, command (or arguments) and success criteria, then approve one attempt. Native approval is requested before execution. Verify success before resolving. Failure, uncertain advice or unavailable providers leave retries blocked in Enforce mode.

Enforce mode vetoes tool dispatch in the affected scope after deterministic repetition thresholds. Monitor mode reports incidents without vetoing calls. Start with harmless local commands in a fresh session. Existing Telegram bridge handlers and configuration are untouched.

This remains a development release. Live Desktop, hosted-process, provider and Telegram coexistence acceptance tests remain outstanding. Semantic contradiction detection and arbitrary equivalent-shell-command detection are not implemented. Task/file scoping can split incidents; rewrites and polling detection are conservative. Host callback failures and host provider timeout/retry behavior remain host boundaries. Secret detection cannot identify every arbitrary unlabeled secret; review each packet.

Disable/uninstall the agent plugin and Desktop half through Desktop, then restart its backend. Reset a session to release its blocks and delete its history. Optional retained plugin data lives only in the profile's plugin-data/hermes-expert-guardian directory. No service, launcher or infrastructure configuration is installed.

Full source, tests, security review, compatibility limits and scan evidence:

https://github.com/NirushaD/Hermes-Expert-Guardian

