"""Runs the hooks and the stage check against a throwaway git repository."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = {k: v for k, v in os.environ.items() if k != "RELEASE_APPROVAL"}
ENV.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def sh(cwd, *args, env=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=env or ENV)


class Repo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        sh(self.dir, "git", "init", "-q", "-b", "main")
        os.makedirs(os.path.join(self.dir, "sdlc"))
        shutil.copy(os.path.join(ROOT, "templates", "sdlc", "config.json"), os.path.join(self.dir, "sdlc", "config.json"))
        shutil.copy(os.path.join(ROOT, "templates", "sdlc", "seats.json"), os.path.join(self.dir, "sdlc", "seats.json"))
        self.write("README.md", "x")
        self.commit("init")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, path, text):
        full = os.path.join(self.dir, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)

    def commit(self, message):
        sh(self.dir, "git", "add", "-A")
        sh(self.dir, "git", "commit", "-q", "-m", message)

    def hook(self, script, tool_input, agent_type=None, env=None):
        event = {"hook_event_name": "PreToolUse", "cwd": self.dir, "tool_input": tool_input}
        if agent_type:
            event["agent_type"] = agent_type
        result = subprocess.run([sys.executable, os.path.join(ROOT, "hooks", script)], input=json.dumps(event),
                                capture_output=True, text=True, cwd=self.dir, env=env or ENV)
        self.assertEqual(result.returncode, 0, result.stderr)
        if not result.stdout.strip():
            return True, ""
        out = json.loads(result.stdout)["hookSpecificOutput"]
        return out["permissionDecision"] != "deny", out.get("permissionDecisionReason", "")

    def can_write(self, path, content="x"):
        return self.hook("pre_write.py", {"file_path": os.path.join(self.dir, path), "content": content})

    def accept(self, name):
        return sh(self.dir, sys.executable, os.path.join(ROOT, "scripts", "accept.py"), "plan", name, "--by", "tester")

    def stage_check(self, base, head, branch):
        return sh(self.dir, sys.executable, os.path.join(ROOT, "scripts", "stage_check.py"), base, head, branch)


class StageLock(Repo):
    def test_full_chain_opens_one_door_at_a_time(self):
        self.assertTrue(self.can_write("intent/orders/intent.md")[0], "an intent can always be written")
        ok, why = self.can_write("intent/orders/spec.md")
        self.assertFalse(ok); self.assertIn("intent", why)
        self.write("intent/orders/intent.md", "# Intent"); self.commit("intent accepted")
        self.assertTrue(self.can_write("intent/orders/spec.md")[0], "spec opens once the intent is on main")
        ok, why = self.can_write("intent/orders/plan.md")
        self.assertFalse(ok); self.assertIn("spec", why)
        self.write("intent/orders/spec.md", "# Spec"); self.commit("spec accepted")
        ok, why = self.can_write("src/orders.py")
        self.assertFalse(ok); self.assertIn("branch", why)
        sh(self.dir, "git", "checkout", "-q", "-b", "change/orders")
        self.assertTrue(self.can_write("intent/orders/plan.md")[0], "plan opens once the spec is on main")
        ok, why = self.can_write("src/orders.py")
        self.assertFalse(ok); self.assertIn("plan", why)
        self.write("intent/orders/plan.md", "# Plan\n\n## Files that change\nsrc/orders.py\n")
        self.assertFalse(self.can_write("src/orders.py")[0], "a written plan is not an accepted plan")
        self.assertEqual(self.accept("orders").returncode, 0)
        self.assertTrue(self.can_write("src/orders.py")[0], "code opens once the plan is accepted")
        self.write("intent/orders/plan.md", "# Plan, changed after acceptance\n")
        ok, why = self.can_write("src/orders.py")
        self.assertFalse(ok); self.assertIn("changed after acceptance", why)

    def test_code_for_one_change_does_not_ride_on_another(self):
        self.write("intent/a/intent.md", "i"); self.write("intent/a/spec.md", "s"); self.commit("a accepted")
        sh(self.dir, "git", "checkout", "-q", "-b", "change/b")
        ok, why = self.can_write("src/b.py")
        self.assertFalse(ok); self.assertIn("intent/b/intent.md", why)

    def test_unconfigured_project_is_left_alone(self):
        os.remove(os.path.join(self.dir, "sdlc", "config.json"))
        self.assertTrue(self.can_write("src/anything.py")[0])


class ProtectedAndSecrets(Repo):
    def test_seats_config_and_workflows_are_protected(self):
        for path in ("sdlc/seats.json", "sdlc/config.json", "sdlc/acceptance/x.plan.json", ".github/workflows/ci.yml", "CODEOWNERS"):
            ok, why = self.can_write(path)
            self.assertFalse(ok, path); self.assertIn("protected", why)

    def test_shell_cannot_rewrite_protected_files(self):
        ok, why = self.hook("pre_bash.py", {"command": "echo '{}' > sdlc/seats.json"})
        self.assertFalse(ok); self.assertIn("Protected", why)
        self.assertTrue(self.hook("pre_bash.py", {"command": "cat sdlc/seats.json"})[0], "reading is fine")

    def test_credentials_are_blocked(self):
        for secret in ("AKIAABCDEFGHIJKLMNOP", "-----BEGIN PRIVATE KEY-----", 'api_key = "abcdefghijklmnopqrstuvwxyz012345"'):
            ok, why = self.can_write("docs/notes.md", secret)
            self.assertFalse(ok, secret); self.assertIn("Credential", why)
        self.assertTrue(self.can_write("docs/notes.md", "api_key = os.environ['API_KEY']")[0])


class FixLane(Repo):
    def test_fix_branch_needs_a_plan_but_not_a_spec_and_locks_committed_tests(self):
        self.write("src/pay.py", "bug"); self.write("tests/test_old.py", "old"); self.commit("existing code")
        sh(self.dir, "git", "checkout", "-q", "-b", "fix/rounding")
        self.assertFalse(self.can_write("src/pay.py")[0], "even a fix needs an accepted plan")
        self.assertTrue(self.can_write("intent/rounding/plan.md")[0], "a fix plan needs no spec")
        self.write("intent/rounding/plan.md", "# Plan\n\n## Files that change\nsrc/pay.py\n"); self.accept("rounding")
        self.assertTrue(self.can_write("src/pay.py")[0])
        self.assertTrue(self.can_write("tests/test_rounding.py")[0], "a new failing test can be added")
        ok, why = self.can_write("tests/test_old.py")
        self.assertFalse(ok); self.assertIn("Test lock", why)


class BashGates(Repo):
    def test_production_gate(self):
        ok, why = self.hook("pre_bash.py", {"command": "make deploy ENV=production"})
        self.assertFalse(ok); self.assertIn("Production gate", why)
        self.assertTrue(self.hook("pre_bash.py", {"command": "make deploy ENV=staging"})[0])
        approved = dict(ENV, RELEASE_APPROVAL="REL-42")
        self.assertTrue(self.hook("pre_bash.py", {"command": "make deploy ENV=production"}, env=approved)[0])

    def set_seat(self, setting):
        seats = json.load(open(os.path.join(self.dir, "sdlc", "seats.json")))
        seats["tech-lead"]["setting"] = setting
        json.dump(seats, open(os.path.join(self.dir, "sdlc", "seats.json"), "w"))

    def test_acceptance_gate_follows_the_seat(self):
        command = {"command": "python3 scripts/accept.py plan orders"}
        self.write("intent/orders/plan.md", "# Plan\n\n## Files that change\nsrc/orders.py\n")
        self.set_seat("human")
        self.assertFalse(self.hook("pre_bash.py", command, agent_type="ai-native-sdlc:tech-lead")[0], "human seat: no agent accepts")
        self.set_seat("human-when-flagged")
        self.assertFalse(self.hook("pre_bash.py", command)[0], "the author (main session) cannot accept")
        self.assertFalse(self.hook("pre_bash.py", command, agent_type="designer")[0], "another agent cannot accept")
        self.assertTrue(self.hook("pre_bash.py", command, agent_type="ai-native-sdlc:tech-lead")[0], "unflagged plan: tech lead agent accepts")
        self.write("intent/orders/plan.md", "# Plan\n\n## Files that change\nsrc/auth/login.py\n")
        ok, why = self.hook("pre_bash.py", command, agent_type="ai-native-sdlc:tech-lead")
        self.assertFalse(ok); self.assertIn("higher-risk", why)
        self.set_seat("agent")
        self.assertTrue(self.hook("pre_bash.py", command, agent_type="tech-lead")[0])


class StageCheck(Repo):
    def test_pull_requests_cannot_skip_a_stage(self):
        sh(self.dir, "git", "checkout", "-q", "-b", "change/orders")
        self.write("intent/orders/spec.md", "# Spec"); self.commit("spec before intent")
        result = self.stage_check("main", "HEAD", "change/orders")
        self.assertEqual(result.returncode, 1); self.assertIn("intent is not accepted", result.stdout)
        sh(self.dir, "git", "checkout", "-q", "main")
        self.write("intent/orders/intent.md", "i"); self.write("intent/orders/spec.md", "s"); self.commit("accepted")
        sh(self.dir, "git", "checkout", "-q", "-B", "change/orders")
        self.write("src/orders.py", "code"); self.commit("code without plan")
        result = self.stage_check("main", "HEAD", "change/orders")
        self.assertEqual(result.returncode, 1); self.assertIn("without intent/orders/plan.md", result.stdout)
        self.write("intent/orders/plan.md", "# Plan\n\n## Files that change\nsrc/orders.py\n"); self.commit("plan, not accepted")
        self.assertIn("no acceptance record", self.stage_check("main", "HEAD", "change/orders").stdout)
        self.accept("orders"); self.commit("accepted plan")
        result = self.stage_check("main", "HEAD", "change/orders")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.write("intent/orders/plan.md", "# Plan edited later\n"); self.commit("plan drift")
        self.assertIn("changed after it was accepted", self.stage_check("main", "HEAD", "change/orders").stdout)

    def test_flags_risk_paths_and_rejects_an_agent_release_manager(self):
        self.write("intent/x/intent.md", "i"); self.write("intent/x/spec.md", "s"); self.commit("accepted")
        sh(self.dir, "git", "checkout", "-q", "-b", "change/x")
        self.write("intent/x/plan.md", "# Plan\n"); self.accept("x")
        self.write("src/auth/login.py", "code"); self.commit("risky")
        self.assertIn("FLAG src/auth/login.py", self.stage_check("main", "HEAD", "change/x").stdout)
        seats = json.load(open(os.path.join(self.dir, "sdlc", "seats.json")))
        seats["release-manager"]["setting"] = "agent"
        json.dump(seats, open(os.path.join(self.dir, "sdlc", "seats.json"), "w")); self.commit("bad seats")
        result = self.stage_check("main", "HEAD", "change/x")
        self.assertEqual(result.returncode, 1); self.assertIn("release-manager must be 'human'", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
