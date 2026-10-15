#!/usr/bin/env python3
"""Read-only candidate audit; writes a separate local report, never publishes."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def snapshot(repo, base):
    base = git(repo, 'rev-parse', '--verify', base + '^{commit}').decode().strip()
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    diff = git(repo, 'diff', '--binary', base, '--', 'debian/')
    names = git(repo, 'diff', '--name-only', base, '--', 'debian/').decode().splitlines()
    untracked = git(repo, 'ls-files', '--others', '--exclude-standard', '--', 'debian/').decode().splitlines()
    top = (repo / 'debian/changelog').read_text().split('\n -- ', 1)[0]
    return base, head, diff, names, untracked, top


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--base', required=True, help='explicit reviewed canonical base commit/ref')
    parser.add_argument('--review', required=True, type=Path, help='JSON per maintainer-readiness.md')
    parser.add_argument('--output', required=True, type=Path, help='new local report; never overwritten')
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = args.output.resolve()
    if output == repo or repo in output.parents:
        parser.error('output must be outside the candidate repository')
    base, head, diff, names, untracked, top = snapshot(repo, args.base)
    review = json.loads(args.review.read_text())
    errors = []
    digest = hashlib.sha256(diff).hexdigest()
    if review.get('base') != base or review.get('head') != head or review.get('diff_sha256') != digest:
        errors.append('review is not bound to this exact base/HEAD/Debian diff')
    if untracked:
        errors.append('untracked Debian files require explicit review and staging: ' + ', '.join(untracked))
    changes = review.get('changes', {})
    for name in names:
        if name == 'debian/changelog':
            continue
        item = changes.get(name, {})
        if not item.get('reason'):
            errors.append(name + ': missing change rationale')
        entry = item.get('changelog_entry', '')
        if not entry or entry not in top:
            errors.append(name + ': reviewed changelog text missing from top entry')
    checks = review.get('checks', {})
    for name in ['identity', 'copyright_paths', 'source_repack', 'bugs', 'policy_watch', 'abi', 'tests', 'freshness']:
        item = checks.get(name, {})
        if item.get('status') not in ['pass', 'not-applicable', 'blocked', 'not-tested'] or not item.get('evidence'):
            errors.append(name + ': missing explicit result/evidence')
        elif item['status'] in ['blocked', 'not-tested']:
            errors.append(name + ': ' + item['status'])
    artifacts = review.get('artifacts', [])
    if not artifacts:
        errors.append('no candidate-specific evidence artifacts')
    for item in artifacts:
        path = (args.review.parent / item['path']).resolve()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item.get('sha256'):
            errors.append('missing or changed artifact: ' + str(path))
    report = {
        'scope': 'Local review consistency only; human/model assertions are not independently proven test results.',
        'publication_authorized': False,
        'base': base, 'head': head, 'debian_diff_sha256': digest,
        'changed_files': names, 'untracked_files': untracked,
        'result': 'INCOMPLETE' if errors else 'REVIEW_RECORD_CONSISTENT',
        'findings': errors, 'review': review,
        'warning': 'Any later candidate change invalidates this report. Check full source provenance and build identity separately.'
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(report['result'] + ': ' + str(output))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
