# Version 0.1.4: safe consultation failure diagnostics

Consultations that fail or are rejected retain only an allowlisted failure category: timeout, provider_error, invalid_json, invalid_response or response_withheld. Raw rejected model text and exception messages remain excluded from incident history. Privacy detection expressions and validation limits are unchanged; PrivacyBoundaryError remains a ValueError subtype.

Eight new frontend simulation checks cover safe failure categories and absence of rejected responses from stored incident data. This brings the frontend simulation set to 25 checks. These are not the full development suite.

Package build and Python compilation completed. The standard Desktop Git installation succeeded in the default profile, pinned to c0c71eba1b28ef5cc695ff420377294922df28fe, with Force reinstall off. After restarting Desktop, all 25 frontend simulations passed, reporting zero real tools and zero cloud requests. The installer UI did not expose a separate scanner verdict or finding count. Live successful recovery on this version remains pending. No complete-readiness claim is made. The user retains a frontend-only testing constraint.
