#!/usr/bin/env python3
"""PostToolUse hook: runs the project's formatter and linter on the file that just changed."""
import json
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import sdlc_rules as rules

event = json.load(sys.stdin)
target = (event.get("tool_input") or {}).get("file_path")
if target:
    target = os.path.abspath(os.path.join(event.get("cwd") or os.getcwd(), target))
    root = rules.repo_root(os.path.dirname(target))
    cfg = rules.load_config(root) if root else None
    if cfg and cfg.get("format_command") and os.path.exists(target):
        command = cfg["format_command"].replace("{file}", shlex.quote(os.path.relpath(target, root)))
        result = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            sys.stderr.write(f"Format and lint failed for {os.path.relpath(target, root)}:\n{(result.stdout + result.stderr)[-1500:]}")
            sys.exit(2)  # surfaces the output to Claude so it can fix the file
