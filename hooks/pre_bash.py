#!/usr/bin/env python3
"""PreToolUse hook for shell commands: production gate, acceptance gate, protected files."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import sdlc_rules as rules


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


def main():
    event = json.load(sys.stdin)
    command = (event.get("tool_input") or {}).get("command") or ""
    root = rules.repo_root(event.get("cwd") or os.getcwd())
    cfg = rules.load_config(root) if root else None
    if not cfg:
        return
    if any(re.search(p, command, re.I) for p in cfg["production_patterns"]) and not os.environ.get("RELEASE_APPROVAL"):
        deny("Production gate: a production release needs the release manager's authorization. "
             "The release manager sets RELEASE_APPROVAL for the session that ships; an agent cannot grant it.")
    accept = re.search(r"accept\.py\s+plan\s+([\w.-]+)", command)
    if accept:
        name = accept.group(1)
        seat = rules.load_seats(root).get("tech-lead", {}).get("setting", "human")
        agent = (event.get("agent_type") or "").split(":")[-1]
        flagged = rules.is_flagged(rules.planned_files(root, name), cfg)
        if seat == "human":
            deny("Acceptance gate: the tech lead seat is set to 'human'. The person in that seat runs the accept command in their own terminal.")
        if agent != "tech-lead":
            deny("Acceptance gate: only the tech-lead agent may accept a plan. The agent that wrote the plan cannot approve it.")
        if seat == "human-when-flagged" and flagged:
            deny("Acceptance gate: this plan touches higher-risk paths (" + ", ".join(flagged) + "), so a person accepts it.")
        return
    for pattern in cfg["protected_paths"]:
        literal = pattern.split("*")[0].rstrip("/")
        if literal and literal in command and re.search(r"(>|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bchmod\b)", command):
            deny(f"Protected path: this command appears to change {literal}. A person changes it, through a reviewed pull request.")


if __name__ == "__main__":
    main()
