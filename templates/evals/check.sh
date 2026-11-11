#!/usr/bin/env bash
# Checks one eval result. Usage: check.sh <eval.json> <result.json>
set -euo pipefail
eval_file="$1"; result_file="$2"
python3 - "$eval_file" "$result_file" <<'PY'
import fnmatch, json, subprocess, sys
spec = json.load(open(sys.argv[1])); result = json.load(open(sys.argv[2]))
expect, problems = spec.get("expect", {}), []
changed = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
paths = [line[3:] for line in changed]
for pattern in expect.get("must_not_change", []):
    hits = [p for p in paths if fnmatch.fnmatch(p, pattern.replace("**", "*"))]
    if hits:
        problems.append(f"changed {hits} but must not change {pattern}")
text = json.dumps(result).lower()
for word in expect.get("must_mention", []):
    if word.lower() not in text:
        problems.append(f"result never mentions '{word}'")
for problem in problems:
    print(f"FAIL {spec['name']}: {problem}")
print(("OK " if not problems else "FAIL ") + spec["name"])
sys.exit(1 if problems else 0)
PY
