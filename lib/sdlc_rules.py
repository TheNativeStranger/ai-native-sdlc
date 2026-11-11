"""Stage rules shared by the hooks (in the agent) and the stage check (in CI).

One rule set, two enforcement points: a write is checked before it happens, and
a pull request is checked before it merges. Standard library only.
"""
import fnmatch
import hashlib
import json
import os
import re
import subprocess

DEFAULTS = {
    "default_branch": "main",
    "change_branch_prefix": "change/",
    "fix_branch_prefix": "fix/",
    "exempt_paths": ["intent/**", "sdlc/**", ".claude/**", ".github/**", "evals/**", "ops/**", "docs/**",
                     "*.md", "CODEOWNERS", ".mcp.json", ".gitignore", "LICENSE", "Makefile"],
    "protected_paths": ["sdlc/seats.json", "sdlc/config.json", "sdlc/acceptance/**", "sdlc/bin/**", ".github/workflows/**", "CODEOWNERS"],
    "test_paths": ["tests/**", "test/**", "**/*_test.*", "**/test_*.*", "**/*.test.*", "**/*.spec.*"],
    "risk_paths": ["**/auth/**", "**/payment*/**", "**/migrations/**", "infra/**"],
    "production_patterns": [r"deploy.*prod", r"prod.*deploy"],
    "format_command": "",
}
SEATS = ["product-owner", "policy-owner", "tech-lead", "platform-engineer", "code-owner", "release-manager", "service-owner"]
SETTINGS = ["human", "human-when-flagged", "agent"]
STAGE_FILE = re.compile(r"^intent/([^/]+)/(intent|spec|plan)\.md$")


def load_config(root):
    """Returns the merged config, or None when the project has not been set up."""
    path = os.path.join(root, "sdlc", "config.json")
    if not os.path.exists(path):
        return None
    cfg = dict(DEFAULTS)
    with open(path, encoding="utf-8") as handle:
        cfg.update(json.load(handle))
    return cfg


def load_seats(root):
    path = os.path.join(root, "sdlc", "seats.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def check_seats(seats):
    """Returns problems in a seats file. The release manager seat is always human."""
    problems = []
    for seat in SEATS:
        entry = seats.get(seat)
        if not entry:
            problems.append(f"seat missing: {seat}")
        elif entry.get("setting") not in SETTINGS:
            problems.append(f"seat {seat} has unknown setting: {entry.get('setting')}")
    if seats.get("release-manager", {}).get("setting", "human") != "human":
        problems.append("release-manager must be 'human': production release cannot be delegated to an agent")
    return problems


def _glob_to_regex(pattern):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"; i += 3
        elif pattern.startswith("**", i):
            out += ".*"; i += 2
        elif pattern[i] == "*":
            out += "[^/]*"; i += 1
        elif pattern[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pattern[i]); i += 1
    return re.compile("^" + out + "$")


def matches(path, patterns):
    return any(_glob_to_regex(p).match(path) for p in patterns)


def git(root, *args):
    result = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def repo_root(start):
    probe = start
    while probe and not os.path.isdir(probe):
        probe = os.path.dirname(probe)
    code, out = git(probe or ".", "rev-parse", "--show-toplevel")
    return out if code == 0 else None


def current_branch(root):
    code, out = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return out if code == 0 else ""


def exists_at(root, ref, path):
    code, _ = git(root, "cat-file", "-e", f"{ref}:{path}")
    return code == 0


def accepted_on_default(root, cfg, path):
    """A document is accepted when it is on the default branch."""
    branch = cfg["default_branch"]
    return exists_at(root, f"origin/{branch}", path) or exists_at(root, branch, path)


def lane_of(branch, cfg):
    """Returns (lane, change name). Lanes: 'full' needs intent, spec and plan; 'fix' needs a plan only."""
    for lane, key in (("full", "change_branch_prefix"), ("fix", "fix_branch_prefix")):
        prefix = cfg[key]
        if branch.startswith(prefix) and len(branch) > len(prefix):
            return lane, branch[len(prefix):]
    return None, None


def sha256_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def acceptance_path(name):
    return f"sdlc/acceptance/{name}.plan.json"


def plan_accepted(root, name):
    """The plan is accepted when a record exists and still matches the plan's content."""
    record, plan = os.path.join(root, acceptance_path(name)), os.path.join(root, "intent", name, "plan.md")
    if not (os.path.exists(record) and os.path.exists(plan)):
        return False
    try:
        with open(record, encoding="utf-8") as handle:
            return json.load(handle).get("sha256") == sha256_file(plan)
    except (ValueError, OSError):
        return False


def planned_files(root, name):
    """Paths listed under the plan's 'Files that change' heading."""
    plan = os.path.join(root, "intent", name, "plan.md")
    if not os.path.exists(plan):
        return []
    text = open(plan, encoding="utf-8").read()
    section = re.search(r"^## Files that change\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return re.findall(r"[\w./-]+\.[A-Za-z0-9]+|[\w.-]+/[\w./-]+", section.group(1)) if section else []


def is_flagged(paths, cfg):
    return sorted(p for p in paths if matches(p, cfg["risk_paths"]))


def check_write(root, path, cfg):
    """Decides whether a file may be written right now. Returns (allowed, reason)."""
    if matches(path, cfg["protected_paths"]):
        return False, f"{path} is a protected path. A person changes it, through a reviewed pull request."
    branch = current_branch(root)
    lane, name = lane_of(branch, cfg)
    stage = STAGE_FILE.match(path)
    if stage:
        change, kind = stage.group(1), stage.group(2)
        if kind == "spec" and not accepted_on_default(root, cfg, f"intent/{change}/intent.md"):
            return False, (f"Stage lock: intent/{change}/intent.md is not accepted yet (it is not on {cfg['default_branch']}). "
                           "Design starts after the intent is accepted.")
        if kind == "plan" and not (lane == "fix" and name == change) and not accepted_on_default(root, cfg, f"intent/{change}/spec.md"):
            return False, (f"Stage lock: intent/{change}/spec.md is not accepted yet (it is not on {cfg['default_branch']}). "
                           "Build starts after the spec is accepted.")
        return True, ""
    if matches(path, cfg["exempt_paths"]):
        return True, ""
    if not lane:
        return False, (f"Stage lock: code is written on a '{cfg['change_branch_prefix']}<name>' or '{cfg['fix_branch_prefix']}<name>' branch, "
                       f"not on '{branch}'. Create the branch for the change first.")
    if lane == "full":
        for doc in ("intent", "spec"):
            if not accepted_on_default(root, cfg, f"intent/{name}/{doc}.md"):
                return False, f"Stage lock: intent/{name}/{doc}.md is not accepted yet. Code waits for the accepted {doc}."
    if not plan_accepted(root, name):
        return False, (f"Stage lock: the plan for '{name}' is not accepted, or it changed after acceptance. "
                       f"Write intent/{name}/plan.md and have the tech lead seat accept it.")
    if lane == "fix" and matches(path, cfg["test_paths"]) and exists_at(root, "HEAD", path):
        return False, (f"Test lock: {path} is a committed test and this is a fix branch. "
                       "Fix the code, not the test. A new failing test goes in a new file, committed before the fix.")
    return True, ""


def check_pull_request(root, cfg, base, head, head_branch):
    """Checks a pull request's changed files against the stage rules. Returns (problems, flagged paths)."""
    code, out = git(root, "diff", "--name-status", f"{base}...{head}")
    if code != 0:
        return [f"cannot diff {base}...{head}"], []
    changed = [line.split("\t") for line in out.splitlines() if line]
    paths = [parts[-1] for parts in changed]
    lane, name = lane_of(head_branch, cfg)
    problems = []
    for path in paths:
        stage = STAGE_FILE.match(path)
        if stage:
            change, kind = stage.group(1), stage.group(2)
            if kind == "spec" and not exists_at(root, base, f"intent/{change}/intent.md"):
                problems.append(f"{path}: the intent is not accepted yet (intent/{change}/intent.md is not on the base branch)")
            if kind == "plan" and not (lane == "fix" and name == change) and not exists_at(root, base, f"intent/{change}/spec.md"):
                problems.append(f"{path}: the spec is not accepted yet (intent/{change}/spec.md is not on the base branch)")
    code_paths = [p for p in paths if not STAGE_FILE.match(p) and not matches(p, cfg["exempt_paths"])]
    if code_paths:
        if not lane:
            problems.append(f"code changes need a '{cfg['change_branch_prefix']}<name>' or '{cfg['fix_branch_prefix']}<name>' branch; this one is '{head_branch}'")
        else:
            if lane == "full":
                for doc in ("intent", "spec"):
                    if not exists_at(root, base, f"intent/{name}/{doc}.md"):
                        problems.append(f"code for '{name}' arrived before its accepted {doc} (intent/{name}/{doc}.md is not on the base branch)")
            plan, record = f"intent/{name}/plan.md", acceptance_path(name)
            if not exists_at(root, head, plan):
                problems.append(f"code for '{name}' arrived without {plan}")
            elif not exists_at(root, head, record):
                problems.append(f"the plan for '{name}' has no acceptance record ({record})")
            else:
                _, plan_text = git(root, "show", f"{head}:{plan}")
                _, record_text = git(root, "show", f"{head}:{record}")
                digest = hashlib.sha256((plan_text + "\n").encode()).hexdigest()
                try:
                    recorded = json.loads(record_text).get("sha256")
                except ValueError:
                    recorded = None
                raw = subprocess.run(["git", "-C", root, "show", f"{head}:{plan}"], capture_output=True).stdout
                if recorded not in (digest, hashlib.sha256(raw).hexdigest()):
                    problems.append(f"the plan for '{name}' changed after it was accepted; accept it again")
            if lane == "fix":
                for parts in changed:
                    if parts[0].startswith("M") and matches(parts[-1], cfg["test_paths"]):
                        problems.append(f"{parts[-1]}: an existing test was edited on a fix branch")
    protected = [p for p in paths if matches(p, cfg["protected_paths"]) and p != acceptance_path(name or "")]
    return problems, sorted(set(is_flagged(paths, cfg)) | set(protected))
