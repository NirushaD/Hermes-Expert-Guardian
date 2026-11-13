# Expert Guardian 0.7.1 — room for local-model reasoning

Increase the bounded incident-draft response budget from 650 to 2048 tokens. The installed local reasoning model exhausted the smaller budget before returning JSON for an older incident, while the larger budget produced both validated fields (1,331 response tokens in the targeted check). Keep the same 60-second local transport timeout, queue bounds, privacy checks and no-cloud-fallback route.

Classify a provider finish_reason of length before decoding content, reject partial output, and show a specific response-limit message instead of implying that the local model is unavailable. New regression tests cover null content after token exhaustion, the transport token limit, and the worker's bounded error state.

All 108 tests pass. Standard scan: safe with four low-severity loopback-address findings. A targeted local-only replay using the older incident's bounded historical evidence passed validation; no raw evidence or model response was printed or persisted outside the normal incident draft. Installed-service verification follows deployment. The automatic drafting behavior and safeguards are documented in RELEASE-0.7.0.md.
