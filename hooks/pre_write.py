#!/usr/bin/env python3
"""PreToolUse hook for file writes: stage lock, protected paths, test lock, credential filter."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import sdlc_rules as rules

SECRETS = [
    (r"AKIA[0-9A-Z]{16}", "an AWS access key id"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "a private key"),
    (r"gh[pousr]_[A-Za-z0-9]{36,}", "a GitHub token"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "an Anthropic API key"),
    (r"(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*['\"][A-Za-z0-9/+_\-]{20,}['\"]", "a hard-coded credential"),
]


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not target:
        return
    target = os.path.abspath(os.path.join(event.get("cwd") or os.getcwd(), target))
    root = rules.repo_root(os.path.dirname(target))
    cfg = rules.load_config(root) if root else None
    if not cfg:
        return  # not a project set up for this plugin: stay out of the way
    path = os.path.relpath(target, root).replace(os.sep, "/")
    allowed, reason = rules.check_write(root, path, cfg)
    if not allowed:
        deny(reason)
    text = "\n".join(str(v) for v in [tool_input.get("content"), tool_input.get("new_string")] if v)
    text += "\n".join(str(e.get("new_string", "")) for e in tool_input.get("edits") or [] if isinstance(e, dict))
    for pattern, what in SECRETS:
        if re.search(pattern, text):
            deny(f"Credential filter: this change appears to contain {what}. Keep secrets out of the repository; read them from the environment.")


if __name__ == "__main__":
    main()
