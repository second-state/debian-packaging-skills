"""Execute a substantive offline slash workflow, not an LLM-behavior guarantee.

Run: python3 -m unittest discover -s tests -p 'test_skill_acceptance.py' -v
Only temporary fixture repositories are committed. GitLab and push effects are
injected fakes; the stage runner, semantic driver, Git and functional tests run.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
SKILL = PROJECT / "skills/wasmedge-debian-packaging"
SCRIPTS = SKILL / "scripts"
FIXTURE = Path(__file__).parent / "fixtures/skill_acceptance"
spec = importlib.util.spec_from_file_location("skill_acceptance_submit", SCRIPTS / "submit-mr.py")
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


class OfflineGitLab(submit.Client):
    """Only read-only local Git executes; all transport effects stay in memory."""
    def __init__(self, fixture, plan):
        self.fixture = fixture
        self.plan = plan
        self.effects = []
        self.mr = None
        self.reads = []

    def git(self, repo, *args):
        self.fixture.assertEqual(Path(repo), self.fixture.repo)
        if "push" in args:
            self.fixture.assertEqual(args, (
                "-c", "push.followTags=false", "-c", "push.pushOption=", "-c", "push.recurseSubmodules=no",
                "push", "--no-follow-tags", "--recurse-submodules=no", "--atomic",
                "git@salsa.debian.org:fixture/fixture-greeter.git",
                self.plan["head"] + ":refs/heads/debian/fixture-1.1"))
            self.effects.append("mock push exact candidate ref")
            return ""
        return self.fixture.git(*args)

    def api(self, path, fields=None):
        if fields is not None:
            self.fixture.assertEqual(path, "projects/11/merge_requests")
            self.fixture.assertIsNone(self.mr, "a retry must not POST another MR")
            self.fixture.assertEqual(fields, {
                "source_branch": self.plan["source_branch"], "target_branch": self.plan["target_branch"],
                "target_project_id": 22, "title": self.plan["title"], "description": self.plan["body"]})
            self.effects.append("mock create MR")
            self.mr = dict(fields, source_project_id=11, target_project_id=22,
                           sha=self.plan["head"], iid=7, state="opened",
                           web_url="https://salsa.debian.org/debian/fixture-greeter/-/merge_requests/7")
            return self.mr
        self.reads.append(path)
        if path == "user":
            return {"username": "fixture"}
        if path == "projects/fixture%2Ffixture-greeter":
            return {"id": 11, "path_with_namespace": "fixture/fixture-greeter",
                    "ssh_url_to_repo": "git@salsa.debian.org:fixture/fixture-greeter.git", "forked_from_project": {"id": 22}}
        if path == "projects/debian%2Ffixture-greeter":
            return {"id": 22, "path_with_namespace": "debian/fixture-greeter"}
        if path == "projects/22/repository/branches/debian%2Flatest":
            return {"commit": {"id": self.plan["base"]}}
        if path.startswith("projects/22/merge_requests?"):
            return [self.mr] if self.mr else []
        if path == "projects/22/merge_requests/7":
            return self.mr
        raise AssertionError("unexpected transport call: " + path)


class SkillAcceptanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="skill-offline-acceptance-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.repo = self.root / "candidate"
        # Do not inherit the developer's author, signing, hooks or URL rewrites.
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0", PYTHONDONTWRITEBYTECODE="1")
        shutil.copytree(FIXTURE, self.root / "inputs")
        self.driver = self.root / "inputs/driver.py"
        pinned = [SKILL / "SKILL.md", SKILL / "references/command-contract.md",
                  SCRIPTS / "release-workflow.py", SCRIPTS / "submit-mr.py"]
        self.intent = {
            "invocation": "/skill:wasmedge-debian-packaging 1.1",
            "version": "1.1-1", "suite": "UNRELEASED", "mode": "scripted offline fixture",
            "identity": {"name": "Offline Fixture Contributor", "email": "fixture@example.invalid",
                         "confirmed": True, "scope": "disposable fixture only; not publication consent"},
            "versions": {str(p.relative_to(PROJECT)): sha(p) for p in pinned},
            "environment": {"python": sys.version, "git": self.command(["git", "--version"]).stdout.strip(),
                            "validation": "stdlib zipapp build and executable Python CLI tests; no Debian toolchain"}}
        (self.root / "intent.json").write_text(json.dumps(self.intent, indent=2))
        inputs = ["intent.json"] + [str(p.relative_to(self.root)) for p in sorted((self.root / "inputs").rglob("*")) if p.is_file()]
        inputs += [str(p) for p in pinned]
        outputs = {
            "prepare": ["prepare.json", "old-consumer.log"],
            "review": ["review.json", "candidate.diff"],
            "validate": ["validation.json", "functional.log", "fixture-greeter.pyz"],
            "handoff": ["MR-DRAFT.md", "handoff.json"]}
        self.plan = {"validation_report": "gate-fixture.json", "cwd": str(self.root), "inputs": inputs, "candidate_repos": ["candidate"],
                     "stages": [{"name": name, "commands": [[sys.executable, str(self.driver), name]],
                                 "outputs": files} for name, files in outputs.items()]}
        self.plan_path = self.root / "local-plan.json"
        self.state_dir = self.root / "state"
        self.submission_state = self.root / "submission-state"

    def command(self, argv):
        return subprocess.run(argv, cwd=self.root, env=self.env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=45)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], env=self.env, text=True).strip()

    def workflow(self, expected=0):
        self.plan_path.write_text(json.dumps(self.plan, indent=2))
        result = self.command([sys.executable, str(SCRIPTS / "release-workflow.py"),
                               "--plan", str(self.plan_path), "--state-dir", str(self.state_dir)])
        logs = "\n".join(p.read_text() for p in self.state_dir.glob("*.log"))
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr + logs)
        return result

    def audit(self, expected=0):
        result = self.command([sys.executable, str(self.driver), "audit"])
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def make_ready(self):
        self.workflow()
        # Inspect real output before a separate audit, not merely stage exit codes.
        review = read_json(self.root / "review.json")
        self.assertEqual(review["before"]["missing_changelog_entries"],
                         ["Update the smoke test to use the required --name option."])
        self.assertEqual(review["after"]["missing_changelog_entries"], [])
        self.assertIn("--name", (self.root / "old-consumer.log").read_text())
        validation = read_json(self.root / "validation.json")
        self.assertEqual([r["label"] for r in validation["runs"]], ["source", "built zipapp"])
        for run in validation["runs"]:
            self.assertEqual(run["exit"], 0)
            self.assertEqual(run["stderr"], "")
            self.assertEqual(run["stdout"], "named greeting: OK\nversion 1.1: OK\nold positional invocation rejected: OK\n")
        self.audit()
        ready = read_json(self.root / "ready.json")
        draft = read_json(self.root / "handoff.json")
        return {"repo": str(self.repo), "source_project": "fixture/fixture-greeter",
                "target_project": "debian/fixture-greeter", "source_branch": "debian/fixture-1.1",
                "target_branch": "debian/latest", "head": ready["head"], "base": ready["base"],
                "account": "fixture", "title": draft["title"], "body": draft["body"],
                "ready_report": str(self.root / "ready.json"), "ready_report_sha256": sha(self.root / "ready.json")}

    def fake_owner_decision(self, plan, client, preview, approved):
        """Model only the scripted owner boundary; never request real consent."""
        if not approved:
            return {"status": "CANCELLED"}
        # Explicit fictional approval covers this exact preview, not future heads.
        self.assertEqual(preview["plan"], plan)
        self.assertEqual(preview["push_destination"], "git@salsa.debian.org:fixture/fixture-greeter.git")
        return submit.submit(plan, client, preview["digest"], self.submission_state)

    def test_bare_invocation_to_review_then_exact_mock_publish_and_retry(self):
        plan = self.make_ready()
        prepare = read_json(self.root / "prepare.json")
        self.assertEqual(prepare["identity"], self.intent["identity"])
        self.assertEqual(prepare["baseline_test_exit"], 0)
        self.assertNotEqual(prepare["old_consumer_exit"], 0)
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "2")
        old = (self.root / "inputs/baseline/debian/changelog").read_text()
        self.assertTrue((self.repo / "debian/changelog").read_text().endswith(old))
        patch = (self.root / "candidate.diff").read_text()
        self.assertIn('+parser.add_argument("--name", required=True)', patch)
        self.assertIn("+  * Update the smoke test", patch)
        self.assertNotIn("diff --git a/debian/control", patch)
        state = read_json(self.state_dir / "state.json")
        self.assertEqual(state["result"], "LOCAL_PLAN_COMPLETE")
        self.assertFalse(state["publication_authorized"])
        ready = read_json(self.root / "ready.json")
        self.assertEqual(ready["status"], "READY_FOR_REVIEW")
        self.assertEqual(ready["head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(ready["base"], self.git("rev-parse", "debian/latest"))
        for item in ready["evidence"]:
            self.assertEqual(item["sha256"], sha(item["path"]))
        self.assertIn("no Debian package build", plan["body"])
        self.assertIn("AI-assisted", plan["body"])
        # Stable resume really retains stage artifacts and does not repeat commits.
        before = {p: (sha(p), p.stat().st_mtime_ns) for p in self.state_dir.glob("*.log")}
        resumed = self.workflow()
        self.assertEqual(resumed.stdout.count(": retained"), 4)
        self.assertEqual(before, {p: (sha(p), p.stat().st_mtime_ns) for p in before})
        self.assertEqual(self.git("rev-list", "--count", "HEAD"), "2")

        client = OfflineGitLab(self, plan)
        preview = submit.submit(plan, client, state_dir=self.submission_state)
        self.assertEqual(preview["status"], "AWAITING_OWNER_APPROVAL")
        self.assertEqual(client.effects, [])
        self.assertEqual(preview["refs"], [{"ref": "refs/heads/debian/fixture-1.1", "sha": plan["head"]}])
        self.assertEqual(self.fake_owner_decision(plan, client, preview, approved=False), {"status": "CANCELLED"})
        self.assertEqual(client.effects, [])
        self.assertFalse((self.submission_state / "submission.json").exists())
        with self.assertRaisesRegex(ValueError, "approval digest differs"):
            submit.submit(plan, client, "0" * 64, self.submission_state)
        self.assertEqual(client.effects, [])
        result = self.fake_owner_decision(plan, client, preview, approved=True)
        self.assertEqual(result, {"status": "SUBMITTED", "url": "https://salsa.debian.org/debian/fixture-greeter/-/merge_requests/7"})
        self.assertEqual(client.effects, ["mock push exact candidate ref", "mock create MR"])
        self.assertEqual(read_json(self.submission_state / "submission.json")["status"], "submitted")
        client.effects.clear()
        self.assertEqual(submit.submit(plan, client, preview["digest"], self.submission_state),
                         {"status": "EXISTING", "url": result["url"], "state": "opened", "content_drift": False})
        self.assertEqual(client.effects, [])
        self.assertIn("user", client.reads)
        self.assertIn("projects/22/merge_requests/7", client.reads)

    def test_helper_success_but_real_functional_failure_cannot_become_ready(self):
        upstream = self.root / "inputs/upstream/greet.py"
        upstream.write_text(upstream.read_text().replace("Hello, {args.name}!", "Wrong, {args.name}!"))
        result = self.workflow(expected=1)
        self.assertIn("validate: BLOCKED", result.stdout)
        state = read_json(self.state_dir / "state.json")
        self.assertEqual(state["stages"]["prepare"]["status"], "passed")
        self.assertEqual(state["stages"]["review"]["status"], "passed")
        self.assertEqual(state["result"], "BLOCKED")
        self.assertNotIn("handoff", state["stages"])
        self.assertIn("Wrong, Debian!", (self.root / "functional.log").read_text())
        validation = read_json(self.root / "validation.json")
        self.assertTrue(all(r["exit"] != 0 for r in validation["runs"]))
        self.audit(expected=1)
        self.assertFalse((self.root / "ready.json").exists())
        self.assertFalse((self.root / "MR-DRAFT.md").exists())
        self.assertFalse(self.submission_state.exists())
        self.workflow(expected=2)  # A failed validation is not silently adopted.

    def test_review_rejects_rewritten_history_and_unfounded_changelog_claim(self):
        for damage, error in [("history", "historical changelog was rewritten"),
                              ("claim", "unsupported changelog claim")]:
            with self.subTest(damage=damage):
                # Each negative case gets a separate disposable fixture invocation.
                if self.repo.exists():
                    shutil.rmtree(self.repo)
                    shutil.rmtree(self.state_dir)
                code = ("from pathlib import Path; p=Path('candidate/debian/changelog'); "
                        + ("p.write_text(p.read_text().replace('Initial release.', 'Altered history.'))"
                           if damage == "history" else
                           "p.write_text(p.read_text().replace('  * New upstream release.', '  * Refresh library symbols.'))"))
                self.plan["stages"][0]["commands"] = [[sys.executable, str(self.driver), "prepare"], [sys.executable, "-c", code]]
                self.workflow(expected=1)
                state = read_json(self.state_dir / "state.json")
                self.assertEqual(state["stages"]["review"]["status"], "failed")
                self.assertIn(error, (self.state_dir / "review.log").read_text())
                self.assertFalse((self.root / "ready.json").exists())
                self.assertFalse((self.root / "MR-DRAFT.md").exists())

    def test_dirty_or_new_committed_candidate_invalidates_resume_and_approval(self):
        plan = self.make_ready()
        client = OfflineGitLab(self, plan)
        preview = submit.submit(plan, client, state_dir=self.submission_state)
        source = self.repo / "src/greet.py"
        source.write_text(source.read_text() + "\n# unreviewed candidate change\n")
        self.assertIn("live candidate changed", self.workflow(expected=2).stderr)
        self.audit(expected=1)
        with self.assertRaisesRegex(ValueError, "working tree must be clean"):
            submit.submit(plan, client, preview["digest"], self.submission_state)
        self.git("add", "src/greet.py")
        identity = self.intent["identity"]
        self.git("-c", "user.name=" + identity["name"], "-c", "user.email=" + identity["email"],
                 "commit", "-qm", "Fixture unreviewed candidate mutation")
        self.assertIn("live candidate changed", self.workflow(expected=2).stderr)
        self.assertIn("stale evidence", self.audit(expected=1).stderr)
        with self.assertRaisesRegex(ValueError, "HEAD changed"):
            submit.submit(plan, client, preview["digest"], self.submission_state)
        self.assertEqual(client.effects, [])

    def test_changed_validation_output_invalidates_runner_and_submission(self):
        plan = self.make_ready()
        client = OfflineGitLab(self, plan)
        preview = submit.submit(plan, client, state_dir=self.submission_state)
        with (self.root / "functional.log").open("a") as log:
            log.write("Unreviewed replacement evidence\n")
        self.assertIn("completed output changed", self.workflow(expected=2).stderr)
        self.audit(expected=1)
        with self.assertRaisesRegex(ValueError, "validation evidence changed"):
            submit.submit(plan, client, preview["digest"], self.submission_state)
        self.assertEqual(client.effects, [])


if __name__ == "__main__":
    unittest.main()
