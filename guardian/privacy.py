"""No raw tool outputs or commands cross the diagnostic boundary."""
import hashlib
import json
import re

# Detection expressions, never file reads or shell commands. Keep each
# expression individually reviewable rather than embedding a long alternation.
SENSITIVE_PATTERNS = (
    r"password", r"passwd", r"passphrase", r"secret", r"token", r"bearer",
    r"cookie", r"api[_-]?key", r"credential", r"private.key",
    r"\.ssh", r"\.env", r"auth\.json", r"BEGIN .*KEY",
    r"ignore .*instructions", r"system prompt", r"https?://[^\s]+@",
)
SENSITIVE = re.compile("(" + "|".join(SENSITIVE_PATTERNS) + ")", re.IGNORECASE)
OPAQUE = re.compile(r"[A-Za-z0-9+/=_-]{32,}")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def safe_text(value, limit=800):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError("Text exceeds privacy boundary")
    if SENSITIVE.search(value) or OPAQUE.search(value):
        raise ValueError("Sensitive or uncertain text withheld; enter a minimal public description")
    return value


def redact(value):
    """Conservative whole-field redaction; never persist raw incident evidence."""
    try:
        return safe_text(value)
    except ValueError:
        return "[WITHHELD]"


def packet(incident, description, outcome):
    # Evidence consists solely of locally generated classifications and opaque identifiers.
    data = {"problem": safe_text(description), "intended_outcome": safe_text(outcome),
            "failure_type": incident["reason"], "failed_attempts": incident["attempts"],
            "verified_facts": ["Tool outcomes triggered a deterministic local threshold."],
            "uncertain": ["Root cause and infrastructure state are unverified."],
            "question": "Identify public evidence needed and a safe corrective action."}
    validate_packet(data)
    return data


def validate_packet(data):
    expected = {"problem", "intended_outcome", "failure_type", "failed_attempts", "verified_facts", "uncertain", "question"}
    if set(data) != expected or len(json.dumps(data)) > 5000:
        raise ValueError("Invalid outbound packet")
    for key in ("problem", "intended_outcome", "question"):
        safe_text(data[key])
    if data["failure_type"] not in {"identical_failure", "unsuccessful_approaches", "configuration_rewrite", "no_progress", "contradiction"}:
        raise ValueError("Invalid failure classification")
    if type(data["failed_attempts"]) is not int:
        raise ValueError("Invalid counters")
    if data["verified_facts"] != ["Tool outcomes triggered a deterministic local threshold."] or data["uncertain"] != ["Root cause and infrastructure state are unverified."]:
        raise ValueError("Untrusted evidence withheld")
