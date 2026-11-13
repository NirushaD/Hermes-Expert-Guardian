# Expert Guardian 0.4.1 — readable names and internal routing

All Guardian screens now display chat names rather than session keys. The searchable chat picker uses Hermes's supported `session.list` API and the same title/preview fallback as Hermes. Duplicate names are distinguished by date and a readable chat number; unnamed chats use Untitled chat. Failed title loading shows a readable warning and never reveals the raw key. Renames refresh automatically. Profile changes invalidate previous chat and incident snapshots.

Incident references, review selectors, expanded summaries, history, maintenance results and user-visible composer handoffs no longer display backend IDs, hashes or raw state records. Exact outbound approval packets and useful action/evidence content remain available. Internal IDs remain unchanged for stable session routing, review selection and packet approval.

Readable composer messages are bound to the exact selected incident or review by an authenticated, state-validated handoff. The reference is delivered once through internal model context, not embedded in the visible user turn. Cross-session and invalid-state handoffs are rejected; handoffs grant no authority or extra attempts. Pause notices and model continuation guidance use plain language and keep routing details internal.

Validation: all 81 tests passed under the installed Hermes Python. Frontend scenarios cover visible and expanded UI, duplicate/unnamed chats, renames, lookup failures, internal exact-ID routing, identifier-free composer messages and all previous recovery/approval cases. Service/API tests cover one-time handoffs, invalid-state and cross-session rejection, and readable pause notices. The isolated Hermes SDK/native approval probe passed with zero real tools or cloud calls. JavaScript syntax passed. The standard installation scanner rated the package safe with three low-severity literal loopback-address findings.

Live visual inspection remains unavailable because the computer/browser automation services are disconnected. Automated interaction tests use a React-hook harness. Provider calls are mocked. No external model consultation is part of validation.
