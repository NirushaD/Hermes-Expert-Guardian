# Production acceptance status — 1 November 2026

Candidate: Guardian 0.1.6, runtime source commit 421ac95598b7579b0e109d07dd9311afd5c31318. Desktop inventory lists 0.1.6 at the exact approved pin; a complete restart loaded the new backend, verified by 42 frontend passes on 2 November. Installed runtime: Hermes d923a5eb487a17c0a68801bba9ef0f56c81040a8, Desktop 0.22.2, Windows.

Status: acceptance incomplete; do not interpret automated passes as a blanket production certification.

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
| Latest-version live post-consultation veto | PASS on 0.1.5 | Expanded real tool error shows Guardian incident f141f3b843f5 and ESCALATE_TO_USER |
| Live successful recovery/native approval UI | PENDING | New 0.1.5 real advice had confidence 0.98 and unresolved true; retry correctly stayed blocked |
| Latest-version live Telegram round trip | PASS on 0.1.5 | Exact GUARDIAN_BRIDGE_015_OK reply in a new test topic; bridge settings untouched |
| Real host HTTP timeout/retry acceptance | PASS, controlled delayed loopback transport | transport-timeout-0.1.6.json: 3 HTTP attempts, 23.35 seconds, one logical consultation, typed timeout, blocks retained |

The user explicitly authorized local automated checks in addition to frontend testing on this date, superseding the earlier frontend-only constraint. All local release gates use synthetic data and temporary databases/profiles. No default-profile settings are altered by those scripts. The worker-death test terminates only its own disposable Python worker, not Hermes or another application.

The user has now restored Enforce and Expert enabled and selected the intended Expert destination. A fresh public-fixture incident and approved consultation were exercised; the real response remained explicitly unresolved. Any new outbound packet still needs explicit review/approval. Existing unresolved incidents must not be reset or force-promoted to obtain a successful test. Native security approval prompts require user interaction under the computer-use rules.

Supported scope is deterministic, bounded loop prevention and manually approved advisory escalation. It is not a command sandbox or a guarantee about arbitrary equivalent scripts, natural-language infrastructure assumptions, or host callbacks that never execute. Host retry/fallback policy and transport cancellation remain host boundaries. Do not weaken privacy, scanning, unresolved-advice checks or human approvals to close a test gate.


Version 0.1.6 clarifies diagnostic uncertainty versus pending approved execution and additionally blocks proposals with outstanding evidence prerequisites. No Expert response resolves an incident; successful execution and explicit verification remain required. This contract correction is not evidence of live recovery until the actual UI workflow passes. The controlled timeout probe does not claim a live outage of every selectable external provider.

Desktop continuation encountered GetCursorPos access denied. The user was asked to unlock and foreground Hermes; no alternative OS automation, security-setting bypass or direct default-profile mutation was attempted.
