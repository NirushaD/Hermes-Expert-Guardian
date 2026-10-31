# Version 0.1.2 changes awaiting frontend acceptance

- Registers the supported transform_tool_result hook and adds a generated Guardian incident notice directly to the relevant tool result. This supplies evidence in the same turn instead of relying only on pre_llm_call context.
- Refuses recovery authorization unless Guardian is enabled in Enforce mode. The native approval key includes the incident and exact operation fingerprint. Duplicate terminal callbacks cannot replace the first recovery outcome.
- Normalizes literal argv for a bounded set of POSIX read-only commands. Expansions, shell operators, comments, escape sequences and unknown commands retain exact fingerprints. This is not general shell equivalence.
- Adds a typed local contradiction rule: patching a file that an error-classified read_file result verified missing creates an incident. File contents cannot establish this evidence. This is not natural-language contradiction detection or a network interface mapping validator.
- Adds frontend-triggered local safeguard simulations. They use an in-memory store and a fake expert, execute no real tools and make no cloud calls. UI labels explicitly distinguish simulations from live acceptance tests.
- Improves visible input borders and lets the user select the active session through the documented Desktop SDK.

Default mode remains Monitor and cloud escalation remains disabled. No claim of complete infrastructure safety or readiness is made until live enforcement, native approval, expert-provider and messaging acceptance checks are complete.
