import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/wasmedge-debian-packaging/scripts/check-validation.py"
spec = importlib.util.spec_from_file_location("validation_records", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ValidationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.report = self.root / "validation.json"
        log = self.root / "result.log"
        log.write_text("test fixture output")
        self.data = {"semantic_review": "passed", "checks": [
            {"category": c, "status": "passed", "exit_code": 0,
             "command": ["fixture", c], "log": "result.log",
             "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
            for c in ["build", "lintian", "runtime"]]}

    def check(self):
        self.report.write_text(json.dumps(self.data))
        return module.inspect_report(self.report)

    def test_complete(self):
        self.assertEqual(self.check(), [])

    def test_previous_driver_shape_rejected(self):
        self.data = {"binary_build": "passed", "lintian_exit": "0", "runtime": "pending"}
        self.assertTrue(self.check())

    def test_build_only_rejected(self):
        self.data["checks"].pop()
        self.assertIn("runtime: missing required check", self.check())

    def test_failed_runtime_rejected(self):
        self.data["checks"][-1]["exit_code"] = 1
        self.assertIn("runtime: not passed", self.check())

    def test_pending_review_rejected(self):
        self.data["semantic_review"] = "pending"
        self.assertIn("semantic review is incomplete", self.check())

    def test_stale_log_rejected(self):
        (self.root / "result.log").write_text("changed")
        self.assertTrue(self.check())

    def test_exception_requires_reason(self):
        self.data["checks"][-1] = {"category": "runtime", "status": "not-applicable"}
        self.assertTrue(self.check())

    def test_missing_log_rejected(self):
        (self.root / "result.log").unlink()
        self.assertTrue(self.check())

if __name__ == "__main__": unittest.main()
