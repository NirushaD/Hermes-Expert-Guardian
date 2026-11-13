# Expert Guardian 0.4.0 — guided incident journey

Built and tested locally on 13 November 2026. This release has not been installed in the user's Hermes profile or published.

## User flow

The focused task chat loads initially. A list shows readable incident reasons, statuses, times and the next actor. Open an incident to follow Review problem → Approve summary → Get advice → Take action → Verify result → Closed. A sole open incident is selected automatically; multiple open incidents require deliberate selection. Status reloads every five seconds. Changing chats or incidents clears unsubmitted form data and verification confirmations.

Each incident shows only actions appropriate to its current state. Exact outbound summaries and validated advice are readable sections. Corrective recovery uses separate tool, command/arguments and success-criteria fields, with an option to ask Hermes to prepare the action for review. Evidence confirmation and native operation approval remain mandatory; the browser submits the authorized operation to the exact task chat. If the composer is unavailable, the page explains how to continue there manually.

Related advisory consultations appear inside their incident, including their rounds and pending packet approvals. General advice remains separately available in an expandable section. Technical data, local safeguard simulations, settings guidance and history deletion are under expandable details.

## Completion and failure behavior

Advice does not mark success. An advisory incident in REVIEWED remains visible as unverified after its previous block is released. Closure requires the user's checked-outcome note. Exact-operation recovery continues to require a successful corrective tool result; a note cannot bypass a failed or unattempted operation. The UI also requires a verification checkbox. Existing direct legacy service callers can still resolve a successful corrective result without a note for compatibility.

Still unresolved records the incomplete outcome, keeps the incident open and offers investigation without granting more corrective attempts or resetting budgets. Failed requests, uncertain advice and failed attempts display their next investigation path. Resolved incidents retain the checked outcome and transition history. Closing an older advisory incident preserves detector evidence belonging to a newer active incident in the same scope. Stale stop actions cannot change a completed incident.

Approvals retain the exact session, incident/review identity and packet hash. Failed actions invalidate the loaded snapshot. Slow responses from other chats, and older failed loads, cannot replace a newer view. A mutation lock prevents duplicate action submission before the UI rerenders.

## Validation

- `python -m unittest discover -s tests -v`: 77 tests passed, none skipped, with FastAPI/HTTPX supplied from an isolated workspace test-dependency directory.
- The frontend interaction harness covers the full corrective journey, linked and general reviews, multiple pending selection, exact approval hashes, failed approvals, failed correction, provider timeout, unresolved outcomes, automatic refresh, cross-chat slow responses, stale load failures, invalid arguments, Monitor-mode recovery restriction and composer fallback.
- A real FastAPI TestClient test follows incident load → preview → stale-hash rejection → advice → exact authorization → native approval hook → corrective result → unresolved → verified closure. Provider responses are mocked; no cloud consultation or real corrective command is executed.
- The suite includes all 42 local safeguard simulations, session isolation, privacy checks, concurrency and bounded review budgets.
- Python compilation, JavaScript syntax and runtime/source package identity checks passed. `python package.py` creates the runtime tree and `dist/hermes-expert-guardian-0.4.0.zip`.

The development shell initially lacked FastAPI and HTTPX. Test-only dependencies were downloaded into `.reference/test-deps`, outside the runtime package; no runtime dependencies or system Python packages were changed. To reproduce the complete run in this shell:

```powershell
$env:PYTHONPATH = (Resolve-Path '.reference/test-deps').Path
python -m unittest discover -s tests -v
python -m compileall -q guardian dashboard
node --check desktop/plugin.js
python package.py
```

## Pre-publication host checks

Before publication, all 77 tests also passed using the installed Hermes Python. The isolated host SDK probe passed manifest loading, registration, native blocking, text-only consultation and native approval resolution (approved, denied, timeout and gate error), with zero real tools and cloud requests. The standard Hermes installation scanner rated the runtime package safe, with three low-severity literal loopback-address findings; see [scanner evidence](install-scan-0.4.0.json). No scanner override was used for this check.

## Remaining acceptance

The browser/desktop control services were disconnected (native pipe unavailable; browser access host unavailable). Live screen rendering, installed Hermes dispatch, actual Expert connectivity and real native approval dialogs were therefore not exercised for this release. Frontend tests use a React-hook harness rather than a browser renderer. These isolated host checks do not establish live UI or provider acceptance. No installed configuration, incident history, permissions or provider selection was changed.
