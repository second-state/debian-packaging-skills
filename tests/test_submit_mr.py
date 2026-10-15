import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/wasmedge-debian-packaging/scripts/submit-mr.py"
spec = importlib.util.spec_from_file_location("submit_mr", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeClient:
    def __init__(self, plan):
        self.plan = plan
        self.effects = []
        self.mrs = []
        self.account = "contributor"
        self.base = "b" * 40
        self.dirty = False
        self.lose_response = False

    def git(self, repo, *args):
        if args[0] == "status":
            return " M changed" if self.dirty else ""
        if args[0] == "rev-parse":
            return self.plan["head"]
        if "push" in args:
            self.effects.append(("push", args))
        return ""

    def api(self, path, fields=None):
        if fields is not None:
            self.effects.append(("create", fields))
            m = dict(fields, source_project_id=1, target_project_id=2, sha=self.plan["head"], iid=7, state="opened", web_url="https://salsa.debian.org/debian/wasmedge/-/merge_requests/7")
            self.mrs = [m]
            if self.lose_response:
                raise OSError("response lost after creation")
            return m
        if path == "user": return {"username": self.account}
        if "repository/branches" in path: return {"commit": {"id": self.base}}
        if "merge_requests?" in path: return self.mrs
        if path.endswith("merge_requests/7"): return self.mrs[0]
        if path == "projects/contributor%2Fwasmedge":
            return {"id": 1, "path_with_namespace": "contributor/wasmedge", "ssh_url_to_repo": "git@salsa.debian.org:contributor/wasmedge.git", "forked_from_project": {"id": 2}}
        if path == "projects/debian%2Fwasmedge":
            return {"id": 2, "path_with_namespace": "debian/wasmedge"}
        raise AssertionError(path)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        log = self.root / "log"
        log.write_text("fixture only")
        report = self.root / "ready.json"
        report.write_text(json.dumps({"status": "READY_FOR_REVIEW", "head": "a"*40, "base": "b"*40, "evidence": [{"path": str(log), "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}]}))
        self.plan = {"repo": str(self.root), "source_project": "contributor/wasmedge", "target_project": "debian/wasmedge", "source_branch": "debian/0.17.2", "target_branch": "debian/latest", "head": "a"*40, "base": "b"*40, "account": "contributor", "title": "Update 0.17.2", "body": "Fixture test results", "ready_report": str(report)}
        self.plan["ready_report_sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
        self.client = FakeClient(self.plan)

    def approval(self):
        return hashlib.sha256(json.dumps(self.plan, sort_keys=True).encode()).hexdigest()

    def test_cli_transport_preserves_body_and_selects_salsa(self):
        body = "First line\nQuotes: ' and \"; $(not-a-command)"
        with patch.object(module.subprocess, "check_output", return_value='{"iid": 7}') as call:
            result = module.Client().api("projects/1/merge_requests", {"description": body, "target_project_id": 2})
        self.assertEqual(result["iid"], 7)
        argv = call.call_args.args[0]
        self.assertEqual(argv[:4], ["glab", "api", "--hostname", "salsa.debian.org"])
        self.assertIn("description=" + body, argv)
        self.assertIn("target_project_id=2", argv)
        self.assertEqual(argv[argv.index("--method") + 1], "POST")
        self.assertNotIn("shell", call.call_args.kwargs)

    def test_readonly_cli_does_not_post(self):
        with patch.object(module.subprocess, "check_output", return_value='{"username": "fixture"}') as call:
            module.Client().api("user")
        self.assertNotIn("--method", call.call_args.args[0])

    def test_url_rewrites_prevent_push(self):
        original = self.client.git
        def git(repo, *args):
            if args[0] == "config":
                return "url.other.pushinsteadof git@salsa.debian.org:"
            return original(repo, *args)
        self.client.git = git
        with self.assertRaisesRegex(ValueError, "URL rewrites"):
            module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_default_preview_has_no_effects(self):
        result = module.submit(self.plan, self.client)
        self.assertEqual(result["status"], "AWAITING_OWNER_APPROVAL")
        self.assertEqual(self.client.effects, [])

    def test_exact_approved_plan_returns_verified_url(self):
        result = module.submit(self.plan, self.client, self.approval())
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual([e[0] for e in self.client.effects], ["push", "create"])
        self.assertTrue(result["url"].endswith("/7"))

    def test_existing_mr_is_not_recreated(self):
        module.submit(self.plan, self.client, self.approval())
        self.client.effects.clear()
        result = module.submit(self.plan, self.client)
        self.assertEqual(result["status"], "EXISTING")
        self.assertEqual(self.client.effects, [])

    def test_uncertain_response_looks_up_not_recreates(self):
        self.client.lose_response = True
        self.assertEqual(module.submit(self.plan, self.client, self.approval())["status"], "SUBMITTED")
        self.assertEqual(sum(e[0] == "create" for e in self.client.effects), 1)

    def test_unresolved_create_never_reposts(self):
        original = self.client.api
        def api(path, fields=None):
            if fields is not None:
                self.client.effects.append(("create", fields))
                raise OSError("request outcome unknown")
            return original(path, fields)
        self.client.api = api
        with self.assertRaisesRegex(ValueError, "unknown"):
            module.submit(self.plan, self.client, self.approval())
        self.assertEqual(sum(e[0] == "create" for e in self.client.effects), 1)

    def test_changed_ready_report_no_effects(self):
        Path(self.plan["ready_report"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "report changed"):
            module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_unrelated_fork_rejected(self):
        original = self.client.api
        def api(path, fields=None):
            result = original(path, fields)
            if path == "projects/contributor%2Fwasmedge":
                result["forked_from_project"] = {"id": 99}
            return result
        self.client.api = api
        with self.assertRaisesRegex(ValueError, "fork"):
            module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_canonical_push_rejected(self):
        self.plan["source_project"] = self.plan["target_project"]
        with self.assertRaisesRegex(ValueError, "fork"):
            module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_unknown_create_blocks_across_invocations(self):
        original = self.client.api
        def api(path, fields=None):
            if fields is not None:
                self.client.effects.append(("create", fields))
                raise OSError("outcome unknown")
            return original(path, fields)
        self.client.api = api
        journal = self.root / "submission-state"
        for _ in range(2):
            with self.assertRaises(ValueError):
                module.submit(self.plan, self.client, self.approval(), journal)
        self.assertEqual(sum(e[0] == "create" for e in self.client.effects), 1)

    def test_submission_lock_prevents_parallel_effects(self):
        journal = self.root / "submission-state"
        journal.mkdir()
        (journal / "submit.lock").write_text("active")
        with self.assertRaises(FileExistsError):
            module.submit(self.plan, self.client, self.approval(), journal)
        self.assertEqual(self.client.effects, [])

    def test_wrong_digest_no_effects(self):
        with self.assertRaises(ValueError): module.submit(self.plan, self.client, "wrong")
        self.assertEqual(self.client.effects, [])

    def test_account_change_no_effects(self):
        self.client.account = "another-user"
        with self.assertRaises(ValueError): module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_advanced_base_no_effects(self):
        self.client.base = "c"*40
        with self.assertRaises(ValueError): module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_dirty_candidate_no_effects(self):
        self.client.dirty = True
        with self.assertRaises(ValueError): module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_changed_evidence_no_effects(self):
        (self.root / "log").write_text("changed")
        with self.assertRaises(ValueError): module.submit(self.plan, self.client, self.approval())
        self.assertEqual(self.client.effects, [])

    def test_existing_different_body_not_overwritten(self):
        module.submit(self.plan, self.client, self.approval())
        self.client.effects.clear()
        self.client.mrs[0]["description"] = "changed by maintainer"
        result = module.submit(self.plan, self.client, self.approval())
        self.assertEqual(result["status"], "EXISTING")
        self.assertTrue(result["content_drift"])
        self.assertEqual(self.client.effects, [])


if __name__ == "__main__": unittest.main()
