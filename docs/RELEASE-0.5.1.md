# Expert Guardian 0.5.1 — open-incident chats only

The left-hand tree now shows only chats with at least one unresolved incident. Chats with no incidents or only RESOLVED incidents are hidden, including the focused chat. REVIEWED incidents remain open until the user verifies and closes them. Completing the last open incident removes its chat from the tree while retaining the closure confirmation on the right. Automatic refresh updates the filter. An empty tree says No chats with open incidents. Incident history and all approval rules are unchanged.

Validation: all 84 tests pass, including frontend cases for empty/closed-only chats, unverified reviews, closure of the last incident and newly opened incidents arriving on refresh. No provider calls or real corrective operations are used in these checks.
