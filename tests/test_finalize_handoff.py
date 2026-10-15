"""Local consistency regression tests, not release validation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
import test_prepare_helper as fixtures

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/wasmedge-debian-packaging/scripts/finalize-debian-handoff.py'


class FinalizerTests(unittest.TestCase):
    git = fixtures.HelperTests.git
    stub = fixtures.HelperTests.stub

    def setUp(self):
        fixtures.HelperTests.setUp(self)
        self.base = self.git('rev-parse', 'HEAD').strip()
        (self.repo / 'debian/rules').write_text('new rules\n')
        self.git('add', 'debian/rules')
        (self.repo / 'debian/changelog').write_text('wasmedge (0.18.0-1) UNRELEASED; urgency=medium\n\n  * Update rules.\n\n -- Test <test@example.invalid>  date\n')
        self.evidence = self.root / 'build.log'
        self.evidence.write_text('fixture: NOT a real build\n')
        self.review = self.root / 'review.json'
        self.output = self.root / 'final.json'
        self.data = {
            'base': self.base, 'head': self.base,
            'diff_sha256': hashlib.sha256(self.git('diff', '--binary', self.base, '--', 'debian/').encode()).hexdigest(),
            'changes': {'debian/rules': {'reason': 'fixture', 'changelog_entry': 'Update rules.'}},
            'checks': {name: {'status': 'not-applicable', 'evidence': 'synthetic unit fixture only'} for name in ['identity', 'copyright_paths', 'source_repack', 'bugs', 'policy_watch', 'abi', 'tests', 'freshness']},
            'artifacts': [{'path': 'build.log', 'sha256': hashlib.sha256(self.evidence.read_bytes()).hexdigest()}]
        }

    def finalize(self):
        self.review.write_text(json.dumps(self.data))
        return subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.repo), '--base', self.base,
                               '--review', str(self.review), '--output', str(self.output)], capture_output=True, text=True)

    def test_consistent_record(self):
        p = self.finalize()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(json.loads(self.output.read_text())['publication_authorized'])

    def test_missing_changelog_summary(self):
        self.data['changes']['debian/rules']['changelog_entry'] = 'Not actually documented.'
        self.assertEqual(self.finalize().returncode, 1)

    def test_stale_diff(self):
        (self.repo / 'debian/rules').write_text('changed again\n')
        self.assertEqual(self.finalize().returncode, 1)

    def test_stale_evidence(self):
        self.evidence.write_text('changed\n')
        self.assertEqual(self.finalize().returncode, 1)

    def test_unreviewed_file(self):
        (self.repo / 'debian/new.install').write_text('usr/bin/*\n')
        self.assertEqual(self.finalize().returncode, 1)

    def test_unperformed_gate(self):
        self.data['checks']['abi']['status'] = 'not-tested'
        self.assertEqual(self.finalize().returncode, 1)

    def test_no_overwrite(self):
        self.output.write_text('keep\n')
        self.assertNotEqual(self.finalize().returncode, 0)
        self.assertEqual(self.output.read_text(), 'keep\n')


if __name__ == '__main__':
    unittest.main()
