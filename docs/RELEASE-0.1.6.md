# Version 0.1.6: explicit proposal contract and typed transport failures

Clarifies that the Expert assesses diagnostic uncertainty when proposing a correction. Pending execution or user verification alone does not imply an unknown cause. The Expert must never suppress material evidence gaps, pretend to independently inspect the system, or override approvals. Incident resolution still requires a successful actual tool outcome and explicit user verification.

Recovery now additionally requires an empty additional_evidence_required list. Blank diagnoses and corrective actions are rejected. Existing unresolved, confidence, privacy, per-packet approval and native approval gates remain intact.

Typed HTTP transport timeout causes are classified as timeout without retaining exception text. Generic errors containing timeout words are not trusted as typed timeouts. No provider, authentication or routing override was added.

Two new frontend simulations exercise pending-evidence rejection, for 42 total checks. Expanded full-suite tests cover the proposal contract, missing evidence, blank advice and wrapped timeouts. Real delayed-loopback host transport and live Desktop acceptance results are recorded separately.

Validation before Desktop replacement: 50 complete-suite tests pass under installed Hermes Python, with no skips. The installed SDK/native approval resolver probe passes. Actual plugin-guard-v11 install-time scan: safe, zero findings, ALLOWED, community trust, force false. Python compilation, JavaScript syntax and package build pass. ZIP SHA256: 15b9b564540cc303d4d46d2b2d3eaddc2fa99d9f651bb4874cebb8450936e2ef.

The real delayed-loopback HTTP test passes through Hermes call planning, HTTP client, retries and exception handling: 5-second per-request budget, 7-second server delay, 3 HTTP attempts, 23.35 seconds overall, one logical consultation. Guardian records timeout, retains the block and refuses a second consultation. The harness uses a disposable profile, synthetic loopback-only authentication, and an outbound socket guard. Only launcher/update/environment activation is suppressed; transport and timeouts are not mocked. The initial harness run encountered host dependency preparation; the corrected test suppresses that bootstrap to use the already installed interpreter. No default-profile settings are modified.

Live Desktop installation, the 42 frontend checks, and actual native recovery approval/denial remain pending for this release.
