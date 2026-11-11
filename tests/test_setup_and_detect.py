"""Checks the setup script, the detection script and the files the plugin ships."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "templates", "ops"))
sys.path.insert(0, os.path.join(ROOT, "lib"))
import detect
import sdlc_rules as rules

BANDS = json.load(open(os.path.join(ROOT, "templates", "ops", "bands.json")))


class Detect(unittest.TestCase):
    base = [10, 11, 9, 10, 12, 8, 10, 11, 9, 10, 10, 11, 9, 12, 8]

    def tier(self, latest, series=None):
        return detect.evaluate(BANDS, (series or self.base) + [latest])["tier"]

    def test_tiers(self):
        self.assertEqual(self.tier(10), "none")
        self.assertEqual(self.tier(11.5), "log")
        self.assertEqual(self.tier(12.7), "diagnose")
        self.assertEqual(self.tier(20), "propose")

    def test_slow_drift_is_caught_before_a_band_is_breached(self):
        drifting = self.base + [10.6] * 7
        result = detect.evaluate(BANDS, drifting + [10.6])
        self.assertEqual(result["tier"], "diagnose"); self.assertIn("eight points", result["reason"])

    def test_short_history_does_nothing(self):
        self.assertEqual(detect.evaluate(BANDS, [1, 2, 99])["tier"], "none")


class Setup(unittest.TestCase):
    def test_init_creates_a_working_project_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as project:
            subprocess.run(["git", "init", "-q", "-b", "main", project], check=True)
            open(os.path.join(project, "CLAUDE.md"), "w").write("mine")
            run = lambda: subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "init.py"), project], capture_output=True, text=True)
            first = run()
            self.assertEqual(first.returncode, 0, first.stdout)
            self.assertEqual(open(os.path.join(project, "CLAUDE.md")).read(), "mine", "an existing file is kept")
            for path in ("sdlc/config.json", "sdlc/seats.json", "sdlc/bin/stage_check.py", "sdlc/bin/sdlc_rules.py", "REVIEW.md",
                         "CODEOWNERS", ".claude/settings.json", ".claude/skills/security/SKILL.md", ".github/workflows/stage-check.yml",
                         "evals/check.sh", "ops/detect.py", "ops/bands.json"):
                self.assertTrue(os.path.exists(os.path.join(project, path)), path)
            self.assertEqual(rules.check_seats(rules.load_seats(project)), [])
            self.assertIn("OK 0 file(s) created", run().stdout, "a second run changes nothing")
            env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e.com")
            subprocess.run(["git", "add", "-A"], cwd=project, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "setup"], cwd=project, check=True, env=env)
            check = subprocess.run([sys.executable, "sdlc/bin/stage_check.py", "HEAD", "HEAD", "main"], cwd=project, capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)


class Shipped(unittest.TestCase):
    def frontmatter(self, path):
        text = open(path, encoding="utf-8").read()
        block = re.match(r"---\n(.*?)\n---\n", text, re.S)
        self.assertTrue(block, path)
        return dict(line.split(":", 1) for line in block.group(1).splitlines() if ":" in line), text

    def test_agents_have_the_required_fields_and_seats_have_agents(self):
        names = set()
        for entry in sorted(os.listdir(os.path.join(ROOT, "agents"))):
            fields, _ = self.frontmatter(os.path.join(ROOT, "agents", entry))
            self.assertEqual(fields["name"].strip(), entry[:-3])
            self.assertTrue(fields["description"].strip())
            names.add(entry[:-3])
        self.assertTrue(set(rules.SEATS) <= names, "every seat has a role agent")
        self.assertEqual(len(names), 11)

    def test_reviewing_agents_cannot_write_files(self):
        for seat in rules.SEATS:
            fields, _ = self.frontmatter(os.path.join(ROOT, "agents", seat + ".md"))
            tools = fields["tools"]
            self.assertNotIn("Write", tools, seat); self.assertNotIn("Edit", tools, seat)

    def test_skills_and_json_files_are_well_formed(self):
        for name in os.listdir(os.path.join(ROOT, "skills")):
            fields, _ = self.frontmatter(os.path.join(ROOT, "skills", name, "SKILL.md"))
            self.assertEqual(fields["name"].strip(), name)
        for folder, _, files in os.walk(ROOT):
            if ".git" in folder.split(os.sep):
                continue
            for entry in files:
                if entry.endswith(".json"):
                    json.load(open(os.path.join(folder, entry), encoding="utf-8"))
        hooks = json.load(open(os.path.join(ROOT, "hooks", "hooks.json")))
        self.assertIn("hooks", hooks)
        for event in hooks["hooks"].values():
            for group in event:
                for hook in group["hooks"]:
                    script = re.search(r"hooks/(\w+\.py)", hook["command"]).group(1)
                    self.assertTrue(os.path.exists(os.path.join(ROOT, "hooks", script)), script)


if __name__ == "__main__":
    unittest.main(verbosity=1)
