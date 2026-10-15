import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/wasmedge-debian-packaging/scripts/release-workflow.py"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = self.root / "plan.json"
        self.state = self.root / "state"
        (self.root / "candidate.identity").write_text("source ref and reviewed delta")
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        import os
        self.git_env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="test@example.invalid", GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="test@example.invalid")
        subprocess.run(["git", "-C", str(self.repo), "commit", "--allow-empty", "-qm", "base"], env=self.git_env, check=True)
        import hashlib
        report = {"semantic_review": "passed", "checks": [
            {"category": name, "status": "passed", "exit_code": 0,
             "command": ["synthetic-test-fixture"], "log": "candidate.identity",
             "sha256": hashlib.sha256((self.root / "candidate.identity").read_bytes()).hexdigest()}
            for name in ["build", "lintian", "runtime"]]}
        (self.root / "validation.json").write_text(json.dumps(report))
        self.data = {"validation_report": "validation.json", "cwd": str(self.root), "inputs": ["candidate.identity"], "candidate_repos": ["repo"], "stages": []}
        for name in ["prepare", "review", "validate", "handoff"]:
            code = "from pathlib import Path; Path(%r).write_text('evidence'); p=Path('calls'); p.write_text((p.read_text() if p.exists() else '')+%r)" % (name, name + "\n")
            self.data["stages"].append({"name": name, "commands": [[sys.executable, "-c", code]], "outputs": [name]})

    def invoke(self):
        self.plan.write_text(json.dumps(self.data))
        return subprocess.run([sys.executable, str(SCRIPT), "--plan", str(self.plan), "--state-dir", str(self.state)], capture_output=True, text=True)

    def test_all_stages_and_resume_without_replay(self):
        self.assertEqual(self.invoke().returncode, 0)
        calls = (self.root / "calls").read_text()
        self.assertEqual(self.invoke().returncode, 0)
        self.assertEqual(calls, (self.root / "calls").read_text())
        state = json.loads((self.state / "state.json").read_text())
        self.assertFalse(state["publication_authorized"])
        self.assertEqual(state["result"], "LOCAL_PLAN_COMPLETE")

    def test_missing_validation_report_blocks_handoff(self):
        (self.root / "validation.json").unlink()
        self.assertEqual(self.invoke().returncode, 1)
        self.assertFalse((self.root / "handoff").exists())

    def test_skipped_validation_blocks_handoff(self):
        (self.root / "validation.json").write_text(json.dumps({
            "semantic_review": "passed", "checks": [
                {"category": c, "status": "not-applicable", "reason": "skip"}
                for c in ["build", "lintian", "runtime"]]}))
        self.assertEqual(self.invoke().returncode, 1)
        self.assertFalse((self.root / "handoff").exists())

    def test_failure_never_reaches_handoff(self):
        self.data["stages"][2]["commands"] = [[sys.executable, "-c", "raise SystemExit(7)"]]
        self.assertEqual(self.invoke().returncode, 1)
        self.assertFalse((self.root / "handoff").exists())
        state = json.loads((self.state / "state.json").read_text())
        self.assertEqual(state["stages"]["validate"]["exit"], 7)
        self.assertEqual(self.invoke().returncode, 2)

    def test_changed_evidence_rejected(self):
        self.assertEqual(self.invoke().returncode, 0)
        (self.root / "review").write_text("changed")
        self.assertEqual(self.invoke().returncode, 2)

    def test_changed_input_rejected(self):
        self.assertEqual(self.invoke().returncode, 0)
        (self.root / "candidate.identity").write_text("new candidate")
        self.assertEqual(self.invoke().returncode, 2)

    def test_handoff_after_validation_drift_rejected(self):
        self.assertEqual(self.invoke().returncode, 0)
        (self.repo / "after-validation").write_text("drift")
        self.assertEqual(self.invoke().returncode, 2)

    def test_untracked_candidate_change_rejected(self):
        self.assertEqual(self.invoke().returncode, 0)
        (self.repo / "new").write_text("change")
        self.assertEqual(self.invoke().returncode, 2)

    def test_tracked_candidate_edit_rejected(self):
        (self.repo / "tracked").write_text("original")
        subprocess.run(["git", "-C", str(self.repo), "add", "tracked"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "tracked"], env=self.git_env, check=True)
        self.assertEqual(self.invoke().returncode, 0)
        (self.repo / "tracked").write_text("edited")
        self.assertEqual(self.invoke().returncode, 2)

    def test_new_candidate_commit_rejected(self):
        self.assertEqual(self.invoke().returncode, 0)
        subprocess.run(["git", "-C", str(self.repo), "commit", "--allow-empty", "-qm", "new"], env=self.git_env, check=True)
        self.assertEqual(self.invoke().returncode, 2)

    def test_changed_plan_rejected(self):
        self.assertEqual(self.invoke().returncode, 0)
        self.data["revision"] = 2
        self.assertEqual(self.invoke().returncode, 2)

    def test_missing_outputs_fail(self):
        self.data["stages"][0]["outputs"] = ["missing"]
        self.assertEqual(self.invoke().returncode, 1)
        self.assertFalse((self.root / "review").exists())

    def test_publication_commands_rejected(self):
        for cmd in [["git", "push", "origin"], ["glab", "mr", "create"], ["dput", "target"]]:
            with self.subTest(cmd=cmd):
                self.data["stages"][0]["commands"] = [cmd]
                self.assertEqual(self.invoke().returncode, 2)
                self.assertFalse((self.root / "calls").exists())

    def test_preparation_alone_not_complete(self):
        self.data["stages"] = self.data["stages"][:1]
        self.assertEqual(self.invoke().returncode, 2)

    def test_lock_not_bypassed(self):
        self.state.mkdir()
        (self.state / "run.lock").write_text("existing")
        self.assertEqual(self.invoke().returncode, 2)
        self.assertEqual((self.state / "run.lock").read_text(), "existing")


if __name__ == "__main__":
    unittest.main()
