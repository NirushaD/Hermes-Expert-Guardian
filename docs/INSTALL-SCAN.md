# Desktop installation security verification — 0.1.1

Inspected installed Hermes commit d923a5eb487a17c0a68801bba9ef0f56c81040a8, scanner plugin-guard-v11. Reproduced the previous commit from a Git archive, with community-source trust, scanning enabled, force=False, no decision callback and no reviewed catalog pin.

| Candidate | Verdict | Findings | Standard installation gate |
|---|---|---|---|
| 0.1.0 repository root | caution | 2 | BLOCKED |
| 0.1.1 runtime subtree | safe | 0 | ALLOWED |

Machine-readable evidence: install-scan-before.json and install-scan-after.json. The actual installer entry point `_scan_plugin_tree` is exercised in tests/install_scan.py, independently of development admission. It delegates to tools.plugin_guard.scan_plugin and should_allow_plugin_install. A caution finding is not automatically accepted by Desktop, even though development admission only warns.

Both original findings are false positives. The credential-detection regex was interpreted as an environment-dump shell pipeline because a literal alternative ended in env followed by an alternation separator. This expression only tests user text; it never reads an environment or executes a shell. The injection finding is an inert synthetic hostile string passed into a rejection test; it is not an instruction or executable payload.

The refactor declares the detection expressions in an explicit tuple and compiles their alternation. Compared with the old source, the resulting regex body and compilation flags are identical. The opaque-string check, structured outbound validation, approval gates, text-only provider adapter, loop detection and Telegram integration behavior are unchanged.

The generated release/hermes-expert-guardian subtree contains only the runtime entry point, manifest, package metadata, license, installation guide, guardian modules, Desktop interface and backend. Original security tests remain in tests/test_guardian.py. No strings are encoded, security tests removed, scanner settings changed, exclusions added to Hermes or overrides used. tests/test_release.py verifies every runtime file matches the development source and no development fixtures enter the release subtree.

Verification: 32 tests passed under Hermes Python; runtime-only payload passed installed-SDK registration, native block directive and text-only facade probes; release admission passed with no warnings; both JavaScript entry points passed syntax checks. No production profile installation or external expert request was performed.

Install source:
https://github.com/NirushaD/Hermes-Expert-Guardian/tree/main/release/hermes-expert-guardian

Important branch-resolution limitation: the inspected Hermes installer strips the branch component from GitHub tree URLs and clones the repository default branch unless given an exact revision. At verification time the remote default was still feat/expert-guardian. Use main as the repository default or explicitly pin the published main commit using Hermes' supported revision input. This release does not modify Hermes to work around that behavior. Published-main verification must use the exact main revision so it cannot accidentally scan the old default branch.
