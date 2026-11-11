# Test evidence — 1 November 2026

## 0.3.1 approval page regression — 12 November 2026

The Node frontend interaction harness exercises the actual settings component with a mocked React/SDK surface. It verifies pending-review selection, visible packet previews, unrelated actions preserving the preview, session-bound approval, whitespace handling, stale-packet refusal, old-backend diagnostics, and preventing repeated approval. It does not contact Expert. This complements backend hash/state validation rather than replacing it.

## 0.3.0 conversation checks — 9 November 2026

Full suite: **67 tests, OK, 2 skips** under system Python. Runtime packaging and byte-identity tests pass; JavaScript syntax and Python compilation checks pass. Conversation tests cover default-off policy, sanitised history roles, local preparation for each round, preview/hash binding to history, round limits, stale/concurrent duplicate requests, preparation failure, disabling pending follow-ups, history identifier rejection and placeholder collisions. Calls use fake local summaries and mocked Expert responses. These do not establish real anonymisation quality, provider connectivity or live Desktop acceptance. The runtime package is rebuilt as 0.3.0; earlier results below remain historical.

## 0.2.0 build validation — 9 November 2026

System Python regression run reports **60 tests, OK, 2 skips**. FastAPI backend tests are unavailable in this interpreter; the optional HTTP transport exception test is also skipped. The new review tests mock provider calls and exercise the registered handler with host identity, manual/chat requests, loop notices, local endpoint restrictions, sanitisation, preview approval, concurrency, budgets, cancellation and failure handling. JavaScript module syntax and Python compilation checks pass. The runtime-only package is rebuilt and byte-identity regression checks pass. No cloud requests or installed configuration changes were made.

The existing installed-runtime probe now also checks `guardian_review` registration, but it has not been rerun against an installed Hermes interpreter for this build. Real Desktop composer delivery, local model anonymisation and Expert connectivity remain live acceptance work. Historical results below describe prior builds.

## Historical results

Final installed-Hermes interpreter run: **29 tests passed**, 2.291 seconds. Standard system Python run: 26 passed, backend test class skipped because FastAPI is not installed there. FastAPI tests all passed under Hermes Python.

Commands:

```powershell
python -m unittest discover -s tests -q
python -m compileall -q guardian dashboard
node --check desktop/plugin.js
# With Hermes Python:
python tests/runtime_probe.py --runtime <installed-hermes-agent-source>
python -m unittest discover -s tests -q
```

Installed-SDK probe result: manifest pass, registration pass, native block directive pass, text-only facade pass, production_modified false. Uses a throwaway profile inside .reference, never the production HERMES_HOME. Direct installed PluginContext, PluginManager and manifest parser are exercised. The native directive resolver invokes Guardian's registered pre-tool hook. The PluginLlm facade receives a fake provider callback; no tools parameter is forwarded. These are API probes, not a full Desktop/host-process execution test.

Official `hermes_cli.plugin_validate.validate_plugin_dir` admission: passes manifest, config schema, loadability, dependency admission, isolated capability probe, declared hooks/tools/middleware, collisions, security scan, core-override check and Desktop surface check. Machine-readable report: admission-results.json. One caution: literal sensitive-path `.env` matching is flagged by the scanner as `dump_all_env`; there is no environment dump code.

Coverage includes: two identical failures; three approaches; failed-then-successful retry; configuration rewrites; polling and changing-output false positives; session isolation; eight concurrent pre-tool reservations; unavailable provider; timeout exception; invalid advice; no recursive consultation; absent/stale packet approval; successful recovery and explicit verification; failed retry; credential/private-key/path/token/injection withholding; disabled mode; monitor mode; persisted restart block; unrelated task; strict outbound field allowlist; no-progress detection; user reset; invalid confidence; missing session rejection; evidence confirmation required; no agent control tools registered.

Not tested as live integrations: actual provider timeout elapsed behavior, Expert OAuth network path, Desktop rendering/navigation, hosted RPC lifetime, live approval UI/denial, existing Telegram bridge co-execution, LM Studio responses, final session-close cleanup. These remain acceptance gates. No Proxmox, SSH, firewall, routing, DHCP, storage or reboot commands were executed. No real credentials were transmitted. All model responses were synthetic.

The first run found SQLite connection handles remaining open on Windows and the conservative scanner rejecting a plugin-generated question containing the word secrets. Both were fixed before the passing runs. Official admission initially exposed eager state access unsupported by its recording context; hook state initialization is now lazy and admission passes.

## Version 0.1.1 follow-up

The original caution finding blocked actual Desktop installation; development admission was insufficient. The runtime-only release now passes the actual standard install-time gate with safe verdict and zero findings, with no overrides. See INSTALL-SCAN.md and the versioned JSON evidence. All 32 tests pass under Hermes Python. The original security fixtures remain intact in the development tree.
