# Version 0.1.4: safe consultation failure diagnostics

Consultations that fail or are rejected retain only an allowlisted failure category: timeout, provider_error, invalid_json, invalid_response or response_withheld. Raw rejected model text and exception messages remain excluded from incident history. Privacy detection expressions and validation limits are unchanged; PrivacyBoundaryError remains a ValueError subtype.

Eight new frontend simulation checks cover safe failure categories and absence of rejected responses from stored incident data. This brings the frontend simulation set to 25 checks. These are not the full development suite.

Package build and Python compilation completed. Desktop installation scan, frontend simulations and live consultation on this version are pending. No complete-readiness claim is made. The user retains a frontend-only testing constraint.
