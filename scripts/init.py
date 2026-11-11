#!/usr/bin/env python3
"""Sets up a repository for the lifecycle. Copies templates; never overwrites an existing file."""
import os
import shutil
import sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(PLUGIN, "templates")
PLAN = [
    ("sdlc/config.json", "sdlc/config.json"), ("sdlc/seats.json", "sdlc/seats.json"),
    ("CLAUDE.md", "CLAUDE.md"), ("REVIEW.md", "REVIEW.md"), ("CODEOWNERS", "CODEOWNERS"),
    ("claude/settings.json", ".claude/settings.json"),
    ("claude/skills", ".claude/skills"), ("github/workflows", ".github/workflows"),
    ("evals", "evals"), ("ops", "ops"),
]
EXTRA = [(os.path.join(PLUGIN, "lib", "sdlc_rules.py"), "sdlc/bin/sdlc_rules.py"),
         (os.path.join(PLUGIN, "scripts", "stage_check.py"), "sdlc/bin/stage_check.py"),
         (os.path.join(PLUGIN, "scripts", "accept.py"), "sdlc/bin/accept.py")]


def copy(source, target, made, kept):
    if os.path.isdir(source):
        for entry in sorted(os.listdir(source)):
            copy(os.path.join(source, entry), os.path.join(target, entry), made, kept)
    elif os.path.exists(target):
        kept.append(target)
    else:
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        shutil.copy(source, target)
        made.append(target)


root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
if not os.path.isdir(os.path.join(root, ".git")):
    print(f"FAIL {root} is not the root of a git repository")
    sys.exit(1)
made, kept = [], []
for source, target in PLAN:
    copy(os.path.join(T, source), os.path.join(root, target), made, kept)
for source, target in EXTRA:
    copy(source, os.path.join(root, target), made, kept)
for folder in ("intent", "sdlc/acceptance"):
    os.makedirs(os.path.join(root, folder), exist_ok=True)
    keep = os.path.join(root, folder, ".gitkeep")
    if not os.listdir(os.path.join(root, folder)):
        open(keep, "w").close(); made.append(keep)
for path in made:
    print("created ", os.path.relpath(path, root))
for path in kept:
    print("kept    ", os.path.relpath(path, root))
print(f"OK {len(made)} file(s) created, {len(kept)} left as they were")
