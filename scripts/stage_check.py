#!/usr/bin/env python3
"""CI stage check: fails a pull request that skips a stage. Prints flagged paths for the seats to look at.

Usage: stage_check.py <base-ref> <head-ref> <head-branch-name>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdlc_rules as rules

base, head, branch = sys.argv[1:4]
root = rules.repo_root(os.getcwd())
cfg = rules.load_config(root)
if not cfg:
    print("FAIL sdlc/config.json not found")
    sys.exit(1)
problems = rules.check_seats(rules.load_seats(root))
found, flagged = rules.check_pull_request(root, cfg, base, head, branch)
problems += found
for problem in problems:
    print(f"FAIL {problem}")
for path in flagged:
    print(f"FLAG {path}")
print(("OK" if not problems else "FAIL") + f" stage check: {len(problems)} problem(s), {len(flagged)} flagged path(s)")
sys.exit(1 if problems else 0)
