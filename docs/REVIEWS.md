# On-demand and automatic reviews — 0.3.0

## Conversation settings

The plugin's manifest-generated **Agent settings** screen includes:

| Setting | Default | Effect |
|---|---|---|
| `expert_conversations` | false | Allow follow-up exchanges inside a review |
| `conversation_max_rounds` | 3 | Total Expert replies including the first; clamped to 1–6 |
| `conversation_approve_each_round` | true | Require preview approval for each follow-up; false inherits `review_sending_policy` |

Privacy checks are mandatory and have no off switch. Hermes can gather evidence requested by Expert, then call `guardian_review` with `review_id`, `followup=true`, `expected_round` matching the last result's `round`, and a fresh diagnostic. The plugin anonymises it locally and builds a conversation from only validated prior summaries and newly sanitised Expert replies. Every message is validated again before external submission. Raw Hermes conversation history is never appended. Existing placeholders are preserved; new identifiers avoid collisions with placeholders already present. Numbering is not a permanent identity mapping across independently prepared diagnostics.

Expert receives preceding sanitised user/assistant messages followed by the new summary. Hermes receives the new reply and remaining-round count. It should stop once advice is sufficient and continue the task normally. The tool does not run a nested autonomous agent loop or give Expert tools. External provider routing/retries remain host-owned.

Follow-ups share the initial review's session-budget slot, with a separate round cap. The cooldown applies to new reviews, not follow-ups. Stale round numbers, concurrent duplicates, disabled conversations, pending rounds and exhausted limits refuse more sending. Failed preparation consumes the attempted round and stops the conversation without silent retry. Separately active loop blocks remain intact; a new incident requires a new incident review rather than being released by an older conversation's follow-up.

Preview hashes cover the new summary and sanitised history. Reducing the round limit or disabling conversations before approving a pending follow-up prevents sending. Cancelling discards retained conversation history and stops later processing; it cannot retract already sent messages. Session reset deletes review history as before.

Anonymisation is best effort on every round. Names, personal facts and unlabeled secrets cannot be guaranteed absent by pattern checks and a local model. Keep preview approval enabled for sensitive work. Live model/Desktop acceptance remains outstanding for this build.

Guardian provides the `guardian_review` Hermes tool. It returns Expert advice into the calling conversation so the local agent can assess it and continue. The original incident preview / exact corrective operation workflow remains available separately.

## Configure

Enable the agent and Desktop plugin for the intended profile. Set `expert_enabled=true`, choose the Expert provider/model in Hermes auxiliary-model settings, and set `local_summary_model` to the exact model ID served by your local LM Studio or other OpenAI-compatible server. `local_summary_url` defaults to `http://127.0.0.1:1234/v1/chat/completions`. Only HTTP endpoints with literal loopback IP addresses and that path are accepted. Authentication, proxies, redirects and external fallback are unavailable on this private summarisation route. The local server itself must serve a local model; Guardian cannot inspect its internal routing.

Choose `review_sending_policy=automatic` for unattended consultations. The default is `preview`, requiring approval of the exact stored packet hash. Enable `automatic_loop_reviews` for detector-triggered requests and `model_requested_reviews` to let Hermes ask for advice before a loop occurs. Defaults leave both off. Building the package does not change installed settings. Normal Hermes permissions and approvals continue to apply.

`max_reviews` defaults to 3 per session (range 2–50); `review_cooldown` defaults to 60 seconds (range 0–3600). Failed and cancelled preparations consume budget. Session history reset replenishes budget and also releases incident blocks. Do not use reset as an automatic retry mechanism.

## Request and continue

Type `Guardian review: assess the problem we are working on and continue after advice` in chat. This explicit user prefix creates a manual request even with model-requested reviews disabled. Or use **Request Expert advice** in settings after selecting the task chat by name. Neither requires an incident.

The Desktop button submits a real user turn to that exact session using the documented composer API. If no composer accepts it, the request stays queued and the UI tells you to open the session and continue. There is no broadcast or gateway injection. Textual requests use the pre-turn hook and do not require Desktop.

Hermes calls `guardian_review` with the pending `review_id` and a focused diagnostic from its current task context. The plugin removes common identifier patterns, asks the configured local model for an anonymous structured summary, sanitises again, validates, and sends only that packet to Expert. Diagnostic input is limited to 16,000 characters; each outbound field is limited to 800. Raw diagnostic input is never persisted. The local summary has no tools, external fallback or unrelated file access.

With preview sending, open the incident’s linked review (or select a general review in Ask Expert), inspect the displayed summary, then click **Approve summary and get advice**. The button submits a turn to retrieve advice. With automatic sending, the tool returns advice during the existing tool loop; no background wake-up is needed.

On a loop, Guardian's tool-result notice and blocked-operation message tell Hermes to call `guardian_review` with the incident ID and diagnostic. When enabled, the model can also call directly when it needs advice. These triggers depend on the primary model following instructions; Guardian does not force a cloud call from a hook or guarantee the model recognises every uncertainty. Network calls run in the advisory tool, outside short-lived hooks.

Advice instructs Hermes to compare with local evidence, revise its approach, gather missing evidence and verify progress. A loop consultation releases only its associated incident to `REVIEWED` and clears that scope's old detector window. This permits ordinary processing, not a claim of success. The incident remains visible as unverified. After checking the subsequent outcome, the user can record a verification note and explicitly close it; Still unresolved retains it for investigation without granting further attempts. Uncertain advice permits evidence gathering too; confidence grants no authority. New repeated failures can create another incident, bounded by budget. A manual review of an existing blocked incident should also supply its `incident_id`.

## Failure, cancellation and privacy limits

Unavailable local models, invalid summaries, rejected responses and provider failures return bounded failure results without persisting transport errors or raw responses. Failures retain loop blocks. Cancel a selected review to stop further processing; cancellation cannot retract a sent request. A crash during PREPARING or SENDING leaves a pending record and is not automatically retried. Cancel it before deliberately requesting another.

Stable placeholders preserve repeated identifiers within each sanitisation pass. Patterns and model anonymisation cannot guarantee detection of every personal fact, name, organisation or unlabeled secret. Use preview for sensitive tasks; automatic sending accepts residual disclosure risk. Expert receives reported observations, not independently verified facts. Its output remains untrusted advisory data. Expert routing retains Hermes-owned authentication and fallback behaviour.

## Validation

Regression tests cover manual requests without incidents, chat requests, loop notices, session isolation, endpoint validation, redaction, preview hashes, concurrent consultation deduplication, budgets, cancellation, failures and tool delivery. Provider calls are mocked. Live Desktop composer acceptance, local anonymisation quality, Expert connectivity and installed-runtime dispatch remain separate acceptance checks.


## Automatic incident descriptions (0.7.0)

Detector incidents receive a trigger explanation immediately. After the hook returns its normal decision, a bounded local-only worker drafts problem_statement and expected_outcome using the configured local summary endpoint/model. The local draft has no tools and no cloud fallback, and it does not consume the Expert review budget. Two workers and a 32-job queue bound concurrency and memory. Calls retain the existing loopback/path/proxy/redirect restrictions and a 60-second timeout.

Inputs are limited, locally sanitized task and tool observations held transiently. For older incidents, the backend can read only a bounded pre-incident window in that exact chat's profile database, read-only. No raw history or tool output is persisted in Guardian's records or appended to an external packet. Generated fields are sanitized and validated before storage; identifier removal remains best effort. Missing evidence is explicitly uncertain. Only detector metadata is used when historical evidence is unavailable.

The UI prefills drafts without overwriting user edits or an already prepared approval packet. Existing incidents draft when selected. Generation failures retain useful trigger-based text and offer an explicit retry; no repeated automatic retry loop is used. Interrupted queued work can be retried after two minutes. Closing an incident discards pending draft results, and deleting its history prevents workers from recreating it. Plugin unload stops new worker jobs and returns unstarted work to pending.
