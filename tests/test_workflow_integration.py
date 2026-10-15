"""Local end-to-end transport boundary test: real Git, fake GitLab, no network."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/wasmedge-debian-packaging/scripts"
spec = importlib.util.spec_from_file_location("submit", SCRIPTS / "submit-mr.py")
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


class IntegrationTests(unittest.TestCase):
    def test_push_does_not_follow_unapproved_tag_or_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            remote = Path(tmp) / "remote.git"
            env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="test@example.invalid", GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="test@example.invalid")
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], env=env, text=True).strip()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            git("commit", "--allow-empty", "-qm", "fixture")
            git("tag", "-a", "unapproved", "-m", "must not push")
            git("config", "push.followTags", "true")
            git("config", "push.pushOption", "merge_request.create")
            # A plain bare repository rejects push options, so success checks suppression too.
            git("-c", "push.followTags=false", "-c", "push.pushOption=", "-c", "push.recurseSubmodules=no", "push", "--no-follow-tags", "--recurse-submodules=no", "--atomic", str(remote), "HEAD:refs/heads/candidate")
            refs = subprocess.check_output(["git", "--git-dir", str(remote), "for-each-ref", "--format=%(refname)"], text=True)
            self.assertEqual(refs.strip(), "refs/heads/candidate")

    def test_real_candidate_preview_and_fake_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            repo.mkdir()
            env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid", GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid")
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], env=env, text=True).strip()
            git("init", "-q")
            (repo / "debian").mkdir()
            (repo / "debian/changelog").write_text("fixture baseline\n")
            git("add", ".")
            git("commit", "-qm", "fixture baseline")
            base = git("rev-parse", "HEAD")
            git("checkout", "-qb", "debian/fixture")
            (repo / "debian/changelog").write_text("fixture candidate\n")
            git("commit", "-qam", "fixture candidate")
            head = git("rev-parse", "HEAD")
            (root / "candidate.json").write_text(json.dumps({"head": head, "base": base}))
            stages = []
            for name in ["prepare", "review", "validate", "handoff"]:
                code = "from pathlib import Path; Path(%r).write_text('fixture stage completed')" % (name + ".log")
                stages.append({"name": name, "commands": [[sys.executable, "-c", code]], "outputs": [name + ".log"]})
            gate = {"semantic_review": "passed", "checks": [
                {"category": category, "status": "passed", "exit_code": 0,
                 "command": ["synthetic-gate-fixture"], "log": "candidate.json",
                 "sha256": hashlib.sha256((root / "candidate.json").read_bytes()).hexdigest()}
                for category in ["build", "lintian", "runtime"]]}
            (root / "validation.json").write_text(json.dumps(gate))
            plan_path = root / "local.json"
            plan_path.write_text(json.dumps({"validation_report": "validation.json", "cwd": str(root), "inputs": ["candidate.json"], "candidate_repos": ["repo"], "stages": stages}))
            cmd = [sys.executable, str(SCRIPTS / "release-workflow.py"), "--plan", str(plan_path), "--state-dir", str(root / "state")]
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            report = root / "ready.json"
            evidence = root / "validate.log"
            report.write_text(json.dumps({"status": "READY_FOR_REVIEW", "head": head, "base": base, "evidence": [{"path": str(evidence), "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}]}))
            plan = {"repo": str(repo), "source_project": "fixture/pkg", "target_project": "debian/pkg", "source_branch": "debian/fixture", "target_branch": "debian/latest", "head": head, "base": base, "account": "fixture", "title": "Fixture", "body": "Fixture only", "ready_report": str(report), "ready_report_sha256": hashlib.sha256(report.read_bytes()).hexdigest()}
            class Transport(submit.Client):
                def __init__(self): self.effects = []; self.mr = None
                def git(self, repo_path, *args):
                    if "push" in args: self.effects.append("push"); return ""
                    return git(*args)
                def api(self, path, fields=None):
                    if fields is not None:
                        self.effects.append("create")
                        self.mr = dict(fields, source_project_id=1, target_project_id=2, sha=head, iid=1, state="opened", web_url="https://salsa.debian.org/debian/pkg/-/merge_requests/1")
                        return self.mr
                    if path == "user": return {"username": "fixture"}
                    if path == "projects/fixture%2Fpkg": return {"id": 1, "path_with_namespace": "fixture/pkg", "ssh_url_to_repo": "git@salsa.debian.org:fixture/pkg.git", "forked_from_project": {"id": 2}}
                    if path == "projects/debian%2Fpkg": return {"id": 2, "path_with_namespace": "debian/pkg"}
                    if "repository/branches" in path: return {"commit": {"id": base}}
                    if "merge_requests?" in path: return [self.mr] if self.mr else []
                    if path.endswith("merge_requests/1"): return self.mr
                    raise AssertionError(path)
            client = Transport()
            git("config", "url.file:///unapproved/.pushInsteadOf", "git@salsa.debian.org:")
            with self.assertRaisesRegex(ValueError, "URL rewrites"):
                submit.submit(plan, client, state_dir=root / "publish-state")
            self.assertEqual(client.effects, [])
            git("config", "--unset", "url.file:///unapproved/.pushInsteadOf")
            preview = submit.submit(plan, client, state_dir=root / "publish-state")
            self.assertEqual(client.effects, [])
            result = submit.submit(plan, client, preview["digest"], root / "publish-state")
            self.assertEqual(result["status"], "SUBMITTED")
            self.assertEqual(client.effects, ["push", "create"])
            client.effects.clear()
            result = submit.submit(plan, client, state_dir=root / "publish-state")
            self.assertEqual(result["status"], "EXISTING")
            self.assertEqual(client.effects, [])


if __name__ == "__main__": unittest.main()
