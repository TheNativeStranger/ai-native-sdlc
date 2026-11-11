#!/usr/bin/env python3
"""Records that a plan was accepted. The record pins the plan's content, so a later edit voids it.

Usage: accept.py plan <name> [--by NAME]
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdlc_rules as rules

parser = argparse.ArgumentParser()
parser.add_argument("kind", choices=["plan"])
parser.add_argument("name")
parser.add_argument("--by", default=os.environ.get("USER", "unknown"))
args = parser.parse_args()
root = rules.repo_root(os.getcwd())
plan = os.path.join(root or ".", "intent", args.name, "plan.md")
if not root or not os.path.exists(plan):
    print(f"FAIL no plan at intent/{args.name}/plan.md")
    sys.exit(1)
record = os.path.join(root, rules.acceptance_path(args.name))
os.makedirs(os.path.dirname(record), exist_ok=True)
with open(record, "w", encoding="utf-8") as handle:
    json.dump({"change": args.name, "sha256": rules.sha256_file(plan), "accepted_by": args.by,
               "accepted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}, handle, indent=2)
    handle.write("\n")
print(f"OK plan for '{args.name}' accepted by {args.by}; record at {rules.acceptance_path(args.name)}")
