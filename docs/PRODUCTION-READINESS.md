# Production acceptance status — 2 November 2026

Candidate: Guardian 0.1.6, runtime source commit 421ac95598b7579b0e109d07dd9311afd5c31318. Desktop inventory lists 0.1.6 at the exact approved pin; a complete restart loaded the new backend, verified by 42 frontend passes on 2 November. Installed runtime: Hermes d923a5eb487a17c0a68801bba9ef0f56c81040a8, Desktop 0.22.2, Windows.

Status: accepted for the documented supported scope on this installed Hermes configuration. Automated, installation, live recovery/resolution and live denial/second-attempt gates passed. This is not a blanket certification across every provider, host version or arbitrary command.

| Gate | Result | Evidence |
|---|---|---|
| Complete local suite with Hermes Python | PASS, 50 tests, no skips | unittest discover -s tests -v |
| Shipped frontend simulations | PASS on 0.1.6: 42 frontend checks, zero tools/cloud | FRONTEND-TESTING.md |
| Runtime-only package/source identity | PASS | ReleaseTests in full suite |
| Actual installation security scanner | safe, zero findings, ALLOWED | install-scan-0.1.6.json; plugin-guard-v11; community source; force false |
| Standard Desktop Git installation | PASS on 0.1.6: exact pin, no force override, clean backend restart verified | FRONTEND-TESTING.md |
| Installed SDK registration and real veto resolver | PASS | tests/runtime_probe.py |
| Installed native approval resolver | PASS for approve, deny, timeout, error with mocked human responses | tests/runtime_probe.py; temporary profile; zero real tool/provider calls |
| SQLite rollback after worker process death | PASS | test_process_death_rolls_back_uncommitted_state |
| Concurrent send and retry reservations | PASS | ReleaseGates; one logical consultation/one native approval |
| Expert remains text-only and host-routed | PASS | runtime probe and neutral-registration tests |
| Configurable Expert picker | PASS | Actual Hermes provider/model controls inspected |
| Live post-consultation veto | PASS on 0.1.6 | Expanded real second-attempt tool error shows Guardian incident 115eedc6df7a and ESCALATE_TO_USER |
| Live successful recovery/native approval UI | PASS on 0.1.6, including explicit user resolution | Real native Run, expanded fixture output, consumed/retry_finished/retry_ok true; user clicked verification and refreshed state is RESOLVED/user_verified true for ec92443fe893; one consultation |
| Live native denial and blocked second corrective attempt | PASS on 0.1.6 | Actual native Reject returned Action denied by user; separate second request returned Guardian veto; consumed/retry_finished true, retry_ok false, one consultation |
| Existing Telegram bridge live round trip | PASS on 0.1.5; not repeated on 0.1.6 | Exact GUARDIAN_BRIDGE_015_OK reply in a new test topic; bridge settings untouched |
| Real host HTTP timeout/retry acceptance | PASS, controlled delayed loopback transport | transport-timeout-0.1.6.json: 3 HTTP attempts, 23.35 seconds, one logical consultation, typed timeout, blocks retained |

The user explicitly authorized local automated checks in addition to frontend testing on this date, superseding the earlier frontend-only constraint. All local release gates use synthetic data and temporary databases/profiles. No default-profile settings are altered by those scripts. The worker-death test terminates only its own disposable Python worker, not Hermes or another application.

The user has now restored Enforce and Expert enabled and selected the intended Expert destination. A fresh public-fixture incident and approved consultation were exercised; the real response remained explicitly unresolved. Any new outbound packet still needs explicit review/approval. Existing unresolved incidents must not be reset or force-promoted to obtain a successful test. Native security approval prompts require user interaction under the computer-use rules.

Supported scope is deterministic, bounded loop prevention and manually approved advisory escalation. It is not a command sandbox or a guarantee about arbitrary equivalent scripts, natural-language infrastructure assumptions, or host callbacks that never execute. Host retry/fallback policy and transport cancellation remain host boundaries. Do not weaken privacy, scanning, unresolved-advice checks or human approvals to close a test gate.


Version 0.1.6 clarifies diagnostic uncertainty versus pending approved execution and additionally blocks proposals with outstanding evidence prerequisites. No Expert response resolves an incident; successful execution and explicit verification remain required. This contract correction is not evidence of live recovery until the actual UI workflow passes. The controlled timeout probe does not claim a live outage of every selectable external provider.

Desktop continuation encountered GetCursorPos access denied. The user was asked to unlock and foreground Hermes; no alternative OS automation, security-setting bypass or direct default-profile mutation was attempted.


On 2 November the actual native-approved corrective read succeeded. The expanded tool card returned HERMES_GUARDIAN_RECOVERY_OK; refreshed Guardian state recorded consumed=true, retry_finished=true and retry_ok=true, retaining ESCALATE_TO_USER until explicit user verification. Real denial and resolution are still acceptance gates; no blanket readiness claim is made.


The user physically verified the successful result and clicked resolve. Refreshed frontend history confirms ec92443fe893 is RESOLVED with user_verified=true, consumed=true, retry_ok=true and escalations=1. The separate denial case remains pending.


## Final live acceptance, 2 November

For incident 115eedc6df7a, refreshed state confirmed the manually authorized exact read at SINGLE_RETRY. The real native prompt appeared and the user physically clicked Reject. Expanded actual tool output reported BLOCKED: Action denied by user; no file content was returned. A separately requested second-attempt acceptance check used the same exact operation and was refused before execution, with no new native prompt. Expanded actual tool output contained Guardian incident 115eedc6df7a: identical_failure; ESCALATE_TO_USER. Final refreshed state: consumed=true, retry_finished=true, retry_ok=false, escalations=1. The earlier success remained RESOLVED/user_verified=true/retry_ok=true. Enforce mode remained saved. No incident history was deleted or denial promoted to success.

These results close the outstanding real recovery/resolution and native denial/second-attempt gates. No runtime change was needed for this continuation. Existing bridge round-trip evidence remains explicitly versioned at 0.1.5; 0.1.6 did not change bridge code or settings, but this is not a claim of a fresh 0.1.6 Telegram run. No Proxmox or server action was performed for these tests.
