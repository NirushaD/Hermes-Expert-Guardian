"""Exercise Desktop's actual install-time gate without placing or enabling a plugin.

Run with Hermes Python, HERMES_HOME pointing at a scratch profile, and its source
on PYTHONPATH. This is deliberately separate from the development admission check.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tree", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from tools.plugin_guard import scan_plugin, should_allow_plugin_install
    from hermes_cli.plugins_cmd import (
        _scan_on_install_enabled, _scan_plugin_tree, PluginScanBlocked,
    )
    assert _scan_on_install_enabled(), "Standard installation scanning must be enabled"
    result = scan_plugin(args.tree, source=args.source)
    allowed, reason = should_allow_plugin_install(result, force=False)
    try:
        gated = _scan_plugin_tree(args.tree, args.source, force=False)
        decision = "ALLOWED"
        assert gated is not None
    except PluginScanBlocked:
        decision = "BLOCKED"
    report = {"scan": asdict(result), "decision": decision,
              "policy_allowed": allowed, "policy_reason": reason,
              "force": False, "reviewed_pin": False, "decision_callback": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
