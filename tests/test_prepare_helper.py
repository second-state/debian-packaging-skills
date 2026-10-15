"""Offline contract tests: real Git, stubbed Debian commands, no network/build."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'skills/wasmedge-debian-packaging/scripts/prepare-wasmedge-debian-update.sh'


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='helper test ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / 'work space'
        self.repo = self.work / 'wasmedge'
        self.repo.mkdir(parents=True)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        DEBEMAIL='validation@example.invalid', DEBFULLNAME='Local Validation',
                        GIT_AUTHOR_NAME='Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_NAME='Test', GIT_COMMITTER_EMAIL='test@example.invalid',
                        TEST_LOG=str(self.root / 'calls'))
        self.git('init', '-q')
        (self.repo / 'debian').mkdir()
        (self.repo / 'debian/changelog').write_text('fixture\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.git('tag', 'upstream/0.18.0')
        self.archive = self.work / 'wasmedge_0.18.0.orig.tar.xz'
        self.archive.write_text('fixture archive')
        self.env['TEST_ARCHIVE'] = str(self.archive)
        for tool in ['gbp', 'uscan', 'dch']:
            self.stub(tool, 'echo unexpected >&2; exit 99')
        self.stub('dpkg-parsechangelog', 'echo 0.18.0-1')
        self.stub('pristine-tar', 'cp "$TEST_ARCHIVE" "$2"')
        self.stub('sbuild', '''for arg in "$@"; do
case "$arg" in --build-dir=*) out="${arg#--build-dir=}";; esac
done
printf fixture > "$out/wasmedge_0.18.0-1_arm64.changes"
printf fixture > "$out/wasmedge_9.0.0-1_arm64.changes"
''')
        self.stub('lintian', 'printf "%s\\n" "$@" > "$TEST_LOG"')

    def stub(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/bash\nset -eu\n' + body + '\n')
        path.chmod(0o755)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], env=self.env, stderr=subprocess.STDOUT, text=True)

    def run_helper(self, *args):
        return subprocess.run(['bash', str(HELPER), '0.18.0', '--no-fetch',
                               '--workdir', str(self.work), *args], env=self.env,
                              capture_output=True, text=True)

    def test_verified_resume_and_handoff(self):
        p = self.run_helper()
        self.assertEqual(p.returncode, 0, p.stderr)
        text = (self.work / 'HANDOFF.md').read_text()
        self.assertIn('NOT upload-ready', text)
        self.assertIn('unmatched exclusions are not proof', text)
        self.assertIn('Publication freshness', text)
        self.assertIn('explicit user approval', text)

    def test_ambiguous_archives_stop(self):
        (self.work / 'wasmedge_0.18.0+dfsg.orig.tar.xz').write_text('other')
        p = self.run_helper()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('exactly one', p.stderr)

    def test_detached_import_tag_stops(self):
        self.git('checkout', '-qb', 'unrelated-import')
        (self.repo / 'new').write_text('new')
        self.git('add', '.')
        self.git('commit', '-qm', 'upstream')
        self.git('tag', '-f', 'upstream/0.18.0')
        self.git('checkout', '-')
        p = self.run_helper()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('not integrated', p.stderr)

    def test_archive_mismatch_stops(self):
        self.stub('pristine-tar', 'printf changed > "$2"')
        p = self.run_helper()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('does not match', p.stderr)

    def test_dirty_tree_preserved(self):
        (self.repo / 'untracked').write_text('keep')
        p = self.run_helper()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('dirty', p.stderr)
        self.assertEqual((self.repo / 'untracked').read_text(), 'keep')

    def test_lintian_requires_new_build(self):
        p = self.run_helper('--run-lintian')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('requires --run-build', p.stderr)

    def test_lintian_only_current_candidate_with_spaces(self):
        (self.work / 'wasmedge_0.18.0-1_stale.changes').write_text('stale')
        p = self.run_helper('--run-build', '--run-lintian')
        self.assertEqual(p.returncode, 0, p.stderr)
        calls = (self.root / 'calls').read_text().splitlines()
        self.assertEqual(len(calls), 1)
        self.assertIn('/build-0.18.0-1.', calls[0])
        self.assertTrue(calls[0].endswith('wasmedge_0.18.0-1_arm64.changes'))

    def test_missing_identity_stops_before_mutation(self):
        env = dict(self.env)
        env.pop('DEBEMAIL')
        env.pop('DEBFULLNAME')
        p = subprocess.run(['bash', str(HELPER), '0.18.0', '--no-fetch',
                            '--workdir', str(self.work)], env=env,
                           capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('DEBEMAIL and DEBFULLNAME are required', p.stderr)
        self.assertEqual(self.git('branch', '--list', 'wasmedge-0.18.0').strip(), '')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.git('rev-parse', 'HEAD').strip(),
                         self.git('rev-parse', 'upstream/0.18.0').strip())

    def test_missing_git_identity_stops(self):
        for key in ['GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL', 'EMAIL']:
            self.env.pop(key, None)
        self.env['GIT_CONFIG_GLOBAL'] = '/dev/null'
        self.env['GIT_CONFIG_NOSYSTEM'] = '1'
        self.git('config', 'user.useConfigOnly', 'true')
        p = self.run_helper()
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('missing Git identity', p.stderr)
        self.assertEqual(self.git('branch', '--list', 'wasmedge-0.18.0').strip(), '')

    def test_first_import_and_changelog_preserve_metadata(self):
        self.git('tag', '-d', 'upstream/0.18.0')
        for name in ['watch', 'copyright', 'rules', 'control', 'libwasmedge0.symbols']:
            (self.repo / 'debian' / name).write_text('maintainer baseline\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'metadata')
        self.stub('gbp', 'test "$1" = import-orig; git tag upstream/0.18.0')
        self.stub('dpkg-parsechangelog', 'echo 0.17.1-1')
        self.stub('dch', 'printf "wasmedge (0.18.0-1) UNRELEASED; urgency=medium\\n" > debian/changelog')
        p = self.run_helper()
        self.assertEqual(p.returncode, 0, p.stderr)
        for name in ['watch', 'copyright', 'rules', 'control', 'libwasmedge0.symbols']:
            self.assertEqual((self.repo / 'debian' / name).read_text(), 'maintainer baseline\n')
        self.assertIn('0.18.0-1', (self.repo / 'debian/changelog').read_text())

    def test_failed_import_stops_before_changelog_or_handoff(self):
        self.git('tag', '-d', 'upstream/0.18.0')
        self.stub('gbp', 'exit 42')
        p = self.run_helper()
        self.assertEqual(p.returncode, 42)
        self.assertEqual((self.repo / 'debian/changelog').read_text(), 'fixture\n')
        self.assertFalse((self.work / 'HANDOFF.md').exists())

    def test_missing_option_argument(self):
        p = self.run_helper('--repo')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('requires a URL', p.stderr)


if __name__ == '__main__':
    unittest.main()
