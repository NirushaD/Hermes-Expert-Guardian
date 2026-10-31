"""Bounded deterministic fingerprints; no shell parsing or model judgement."""
import json
import re
import shlex
from .privacy import digest


def operation(tool, args):
    normalized = dict(args)
    if isinstance(normalized.get("command"), str):
        # Preserve case and quoted whitespace: collapsing them can change shell semantics.
        command = normalized["command"].strip()
        # POSIX read-only commands with plain literal arguments only. Shell syntax,
        # expansions, scripts, Windows commands and writes retain exact fingerprints.
        if not re.search(r"[|;&<>$`\\\n\r*?\[\]{}~#]", command):
            try:
                words = shlex.split(command, posix=True)
                if words and words[0] in {"ls", "cat", "stat", "ip", "ping", "uname", "id", "whoami"}:
                    command = {"literal_posix_argv": words}
            except ValueError:
                pass
        normalized["command"] = command
    return digest([tool, normalized])


def signature(result):
    text = json.dumps(result, sort_keys=True, default=str)[:32000]
    text = re.sub(r"\b0x[0-9a-fA-F]+\b|\b\d{4}-\d\d-\d\dT\S+|\bpid[=: ]+\d+", "#", text)
    return digest(text)


def failed(result, status):
    if status == "error":
        return True
    try:
        value = json.loads(result) if isinstance(result, str) else result
    except (ValueError, TypeError):
        return False
    return isinstance(value, dict) and (value.get("success") is False or
        bool(value.get("error")) or value.get("exit_code", 0) not in (0, None))


def reason(events, current, identical=2, approaches=3, no_progress=5):
    related = [e for e in events if e["scope"] == current["scope"]]
    same = [e for e in related if e["op"] == current["op"]]
    if current["failure"]:
        if sum(e["failure"] and e["sig"] == current["sig"] for e in same) >= identical:
            return "identical_failure"
        failures = [e for e in related if e["failure"]]
        if len({e["op"] for e in failures}) >= approaches:
            return "unsuccessful_approaches"
    if current["rewrite"] and sum(e["rewrite"] for e in related) >= approaches:
        return "configuration_rewrite"
    if sum(e["sig"] == current["sig"] for e in same) >= no_progress:
        return "no_progress"
    return None
