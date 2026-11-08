# Security review

## 0.3.0 conversation extension

Follow-ups require explicit conversation enablement and a matching prior round number, are capped at six Expert replies including the first, and pass local anonymisation on every new diagnostic. Only validated summaries and sanitised copies of prior Expert replies are retained as outbound conversation history. The entire history is revalidated before sending. Preview approval defaults on for each follow-up and binds to the complete packet. There is no privacy bypass setting. Duplicate/stale rounds cannot create additional logical consultations. These controls reduce disclosure risk; arbitrary personal facts and unlabeled secrets remain beyond any guarantee of detection.

## 0.2.0 advisory review boundary

The [new workflow](REVIEWS.md) uses a separate policy from legacy recovery below. Bounded diagnostics go only to an explicitly configured literal loopback HTTP endpoint, with proxies/redirects disabled and no cloud fallback. Identifier patterns are removed before local summarisation and again afterward; only validated structured summary fields reach Expert. Raw diagnostics, local raw responses and exception text are not persisted by Guardian. The local server's logging and internal routing remain outside this boundary.

Automatic sending is configurable and off by default (`preview`). Patterns and model anonymisation cannot guarantee removal of every name, personal fact or unlabeled secret. Automatic sending carries residual disclosure risk; preview permits inspection and hash-bound approval. Expert has no tools. Advice returns to the local agent as untrusted data under normal Hermes approvals. A valid loop review releases only its linked incident to REVIEWED so the agent can gather evidence or try a revised approach. It does not establish successful resolution. The older exact-operation controls remain available separately.

Session identity comes from host context, not model arguments. SQLite transactions bound concurrency and budgets. Restart does not resend in-flight consultations; cancellation cannot retract an already sent packet. New tests are synthetic; historical scanner and native-runtime results do not certify this changed release.

## Historical 0.1.x assessment

Review scope: local source review, synthetic tests, installed SDK manifest/registration/native-directive/facade probes. No external security audit or production penetration test.

## Outbound boundary

Raw tool args/results are reduced locally to SHA256 fingerprints and generated classifications. They are never included in diagnostic packets. The packet allows exactly problem, intended_outcome, failure_type, failed_attempts, verified_facts, uncertain, question. No session ID, command, file content, terminal transcript or conversation history is sent. Public descriptions require a user gesture, length checks, sensitive-word/path/private-key detection, opaque-string screening, exact preview and hash-matched send approval. Whole fields are withheld rather than attempting partial redaction.

Arbitrary short unlabeled secrets cannot be identified deterministically from text. Therefore no automatic egress is offered and users must review the exact preview. A user can still approve a description containing a secret that the conservative scanner does not recognize. This limitation precludes a claim of perfect secret detection. Tool output prompt injection cannot reach the expert because raw output is excluded; user-supplied descriptions are explicitly framed as untrusted data.

The cloud request contains only two text messages. ctx.llm is a single completion facade whose API has no tools argument. Actual installed facade invocation was tested with an injected fake provider, verifying no tools parameter is forwarded. It does not instantiate an agent, delegate, execute expert commands, read auth.json/.env, or access SSH, browser, filesystem or Proxmox tools. Host-owned authentication may legitimately be used by Hermes to send the request; Guardian does not extract or copy it. The user can change auxiliary routing in Desktop; verify the configured model before sending.

## Responses and recovery

Strict field/type/bounds validation rejects malformed, oversized, suspicious or uncertain advice without echoing raw invalid output. Confidence below 0.8, unresolved=true, or any outstanding additional_evidence_required stops recovery. Blank diagnosis/action fields are rejected. The Expert contract distinguishes diagnostic uncertainty from an approved correction awaiting execution; incident resolution is never granted by an Expert response. A response is advisory only. Every corrective operation requires user review of evidence, exact operation fingerprint authorization, a nonempty success criterion, and a native approve directive. The corrective call is consumed atomically before approval; denied approval cannot re-arm it. Only explicit user verification after a successful tool outcome resolves the incident.

## Persistence and concurrency

SQLite BEGIN IMMEDIATE transactions serialize hook and Desktop workers. Persisted data contains session IDs, incident IDs, counters, timestamps, fingerprint metadata, approvals, sanitized packets and validated advice. Exact corrective args are hashed rather than stored. These data remain potentially sensitive operational metadata; protect the profile directory with normal account ACLs. Fingerprints are not encryption and common commands can be guessed. No telemetry, separate log stream, background service or analytics is added.

Retention is 30 days for inactive resolved sessions, with bounded record counts. Unresolved safety state is not silently expired. Explicit reset deletes a session's logical records; SQLite deletion is not guaranteed forensic secure erasure. Backups, provider logs and Hermes host logs are outside plugin retention control.

The official security scan reports `dump_all_env` at privacy.py:6 because the sensitive-path rejection regex contains `.env`. Inspection confirms this is a literal detection pattern, not environment enumeration. No environment or credential-file reader exists in the plugin.

## Remaining risk and acceptance gates

Hermes hook dispatch isolates errors and can have host-imposed callback timeouts. Guardian returns block on its own initialization/state failures in Enforce mode, but cannot guarantee enforcement if Hermes never invokes its callback, kills the plugin host, or fails open outside the plugin. This is a host boundary, not something a standalone plugin can repair by instructions.

Before production enablement: validate Desktop UI and profile scoping in an isolated profile; verify native approval denial and existing always-allow policy; exercise host-process death and restart; review auxiliary provider fallback behavior and packet visibility; test Telegram bridge co-existence. Use harmless local commands only. Automatic egress, semantic contradiction detection, typed evidence adapters and strict provider wall-clock cancellation remain future work.

## Version 0.1.1 packaging correction

The original scanner caution was reproduced as an actual Desktop installation block. Runtime code now declares individual redaction expressions before compiling the same regex body and flags. Security tests remain in the repository and are excluded only from the generated runtime package, not from scanning policy. The runtime-only Git source passes the standard install gate with zero findings. See INSTALL-SCAN.md for evidence and the repository-default-branch caveat.
