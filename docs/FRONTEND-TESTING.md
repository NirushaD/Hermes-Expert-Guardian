# Frontend acceptance results — 1 November 2026

Installed Hermes Desktop v0.22.2, existing default profile. All local installation and runtime interaction in this session used the Desktop frontend; no CLI/API substitute, isolated profile, scanner override or force reinstall was used. Repository Git operations only were performed outside the frontend.

Installed plugin: Expert Guardian 0.1.1, pinned to reviewed release commit 679dd46b190a12b7df3415960f210677244bfd40. Both Agent and Desktop switches visibly enabled after installation. Existing desktop-telegram-bridge 0.5.0 remained enabled; Manual approval mode remained displayed.

## Installer issue corrected

Desktop repository review initially failed with a missing release-subdirectory error even with the exact commit entered. Review inspected the repository's stale default branch. The existing feat/expert-guardian branch was fast-forwarded, without force, to the identical reviewed main commit. Repository review then recognized both the agent plugin and Desktop UI, and normal installation completed successfully. Main remains the build branch. GitHub's default-branch setting itself has not changed.

## Frontend checks passed

- Guardian settings page rendered and its incident-history backend responded for a synthetic test identifier, reporting empty incidents and mode monitor.
- A fresh chat used the user's pinned LM Studio Qwen3.6 35B A3B model. It attempted three identical read_file calls against a deliberately nonexistent test file. No terminal, shell, SSH, network tools, file writes or delegation were requested.
- The Guardian incident viewer recorded identical_failure after exactly two attempts, with zero expert escalations. Monitor mode allowed the requested subsequent call. The chat model's prose claimed no Guardian incident occurred; the persisted plugin state contradicted that claim and was used as the test evidence.
- A diagnostic description containing a clearly synthetic credential was refused by the backend with a privacy-constraint notification.
- Replacing it with a short public description generated the allowlisted diagnostic preview. The packet contained classifications and counters, without the raw file path, command, terminal output or unrelated history.
- Refresh showed AWAIT_EGRESS_APPROVAL and escalations 0. No cloud expert request or corrective operation was initiated.

## State left for the user

Plugin installed and enabled, Monitor mode unchanged, expert escalation not enabled. The harmless test chat and its incident/preview are retained for inspection. No history was deleted, no production configuration was edited, and no Proxmox action occurred.

## Not covered

Live Enforce-mode vetoes, native recovery approval/denial, actual Codex consultation, provider timeout, and successful expert-guided recovery were not exercised in this frontend session. Existing automated evidence covers selected API/state-machine behavior but does not replace these live acceptance checks. Telegram bridge remained enabled; a live Telegram message exchange was not performed.

## Version 0.1.2 acceptance pending

Implementation commit 88494fd733d10b33be9afdd6d0136af0e324a1eb is published on main. Python compilation and JavaScript syntax checks passed; the complete test suite, installer security scan and frontend simulations have not been run for this version. The 32-test and safe-scanner results above apply to 0.1.1 only.

Frontend continuation was blocked by Windows input automation: after reconnecting to the observed Hermes window, the Raise/click attempt failed with `GetCursorPos failed: Access is denied. (0x80070005)`. No 0.1.2 installation or live acceptance test was completed. The installed version remains 0.1.1. Version 0.1.2 must not be described as ready until its outstanding checks pass.
