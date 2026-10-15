#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  prepare-wasmedge-debian-update.sh <version> [options]

Options:
  --workdir <dir>       Working directory. Default: wasmedge-debian-update-<version>
                        in the current directory, or next to the enclosing git
                        repository when invoked from inside one (gbp layout:
                        the packaging clone's parent dir holds the orig tarball,
                        and the tree must not nest inside an upstream checkout).
  --repo <url>          Debian packaging repo. Default: https://salsa.debian.org/debian/wasmedge.git
  --run-build           Run sbuild -d unstable after preparing the tree.
  --run-lintian         Lint artifacts from this invocation (requires --run-build).
  --no-fetch            Do not clone or download; operate on existing workdir/repo.
  -h, --help            Show this help.

This helper prepares local artifacts only. It never pushes branches, submits MRs,
files bugs, requests Ubuntu sync, uploads packages, signs packages, or changes
credentials.

Resume requires a clean tree, an integrated upstream tag, and a matching
pristine-tar archive. Ambiguous or unverified state stops without resetting work.
Review and commit local packaging edits before rerunning.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

Version=""
WorkDir=""
RepoUrl="https://salsa.debian.org/debian/wasmedge.git"
RunBuild=0
RunLintian=0
NoFetch=0

while [[ $# -gt 0 ]]; do
  case "$1" in
  -h | --help)
    usage
    exit 0
    ;;
  --workdir)
    [[ $# -ge 2 && -n "$2" && "$2" != -* ]] || { echo "--workdir requires a directory" >&2; exit 1; }
    WorkDir="$2"
    shift 2
    ;;
  --repo)
    [[ $# -ge 2 && -n "$2" && "$2" != -* ]] || { echo "--repo requires a URL" >&2; exit 1; }
    RepoUrl="$2"
    shift 2
    ;;
  --run-build)
    RunBuild=1
    shift
    ;;
  --run-lintian)
    RunLintian=1
    shift
    ;;
  --no-fetch)
    NoFetch=1
    shift
    ;;
  -*)
    echo "unknown option: $1" >&2
    usage
    exit 1
    ;;
  *)
    if [[ -n "${Version}" ]]; then
      echo "unexpected argument: $1" >&2
      usage
      exit 1
    fi
    Version="$1"
    shift
    ;;
  esac
done

if [[ -z "${Version}" ]]; then
  echo "version is required" >&2
  usage
  exit 1
fi

if [[ ! "${Version}" =~ ^[0-9]+(\.[0-9]+)+$ ]]; then
  echo "expected a stable numeric upstream version (for example 0.18.0)" >&2
  exit 1
fi
if [[ "${RunLintian}" -eq 1 && "${RunBuild}" -ne 1 ]]; then
  echo "--run-lintian requires --run-build; existing artifacts are not fresh evidence" >&2
  exit 1
fi

if [[ -z "${WorkDir}" ]]; then
  # Keep the packaging tree out of any upstream checkout: when invoked from
  # inside a git repository, place the workdir next to that repository.
  if RepoTop="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    WorkDir="$(dirname "${RepoTop}")/wasmedge-debian-update-${Version}"
    echo "note: inside git repo ${RepoTop}; using sibling workdir ${WorkDir}" >&2
  else
    WorkDir="${PWD}/wasmedge-debian-update-${Version}"
  fi
fi

require_cmd git
require_cmd gbp
require_cmd uscan
require_cmd dch
require_cmd dpkg-parsechangelog
require_cmd pristine-tar

if [[ -z "${DEBEMAIL:-}" || -z "${DEBFULLNAME:-}" ]]; then
  echo "DEBEMAIL and DEBFULLNAME are required for non-interactive local preparation" >&2
  echo "Use a clearly local identity, for example:" >&2
  echo "  DEBEMAIL=validation@example.invalid DEBFULLNAME='Local Validation'" >&2
  exit 1
fi

if [[ "${RunBuild}" -eq 1 ]]; then
  require_cmd sbuild
fi

if [[ "${RunLintian}" -eq 1 ]]; then
  require_cmd lintian
fi

mkdir -p "${WorkDir}"
cd "${WorkDir}"
WorkDir="$(pwd -P)"

if [[ ! -d wasmedge ]]; then
  for Identity in GIT_AUTHOR_IDENT GIT_COMMITTER_IDENT; do
    if ! git var "${Identity}" >/dev/null 2>&1; then
      echo "missing Git identity: ${Identity}; configure explicit identity before cloning" >&2
      exit 1
    fi
  done
  if [[ "${NoFetch}" -eq 1 ]]; then
    echo "expected existing repo at ${WorkDir}/wasmedge" >&2
    exit 1
  fi
  gbp clone "${RepoUrl}" wasmedge
fi

cd wasmedge

if [[ ! -d debian ]]; then
  echo "not a Debian packaging tree: ${WorkDir}/wasmedge" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "packaging tree is dirty; review and commit or preserve changes before rerunning" >&2
  exit 1
fi
InitialCommit="$(git rev-parse HEAD)"
# Resolve identity in this repository (including repo-local configuration).
# Never change user configuration or guess the maintainer's identity.
for Identity in GIT_AUTHOR_IDENT GIT_COMMITTER_IDENT; do
  if ! git var "${Identity}" >/dev/null 2>&1; then
    echo "missing Git identity: ${Identity}; set explicit author/committer identity before importing" >&2
    exit 1
  fi
done
CurrentBranch="$(git branch --show-current || true)"
PrepBranch="wasmedge-${Version}"

if git show-ref --verify --quiet "refs/heads/${PrepBranch}"; then
  git switch "${PrepBranch}"
else
  git switch -c "${PrepBranch}"
fi

if [[ "${NoFetch}" -eq 0 ]]; then
  if ! uscan --download-version "${Version}" --force-download --repack --compression xz; then
    echo "uscan failed: likely a broken debian/watch (upstream URL or tag-scheme change)." >&2
    echo "debug with: uscan --verbose --no-download, fix debian/watch (include the fix in the MR), then re-run" >&2
    exit 1
  fi
fi

shopt -s nullglob
Tarballs=()
for Candidate in ../"wasmedge_${Version}"{,+dfsg}.orig.tar.{gz,bz2,xz,lzma}; do
  [[ -f "${Candidate}" ]] && Tarballs+=("${Candidate}")
done
if [[ ${#Tarballs[@]} -ne 1 ]]; then
  echo "expected exactly one candidate orig tarball; found ${#Tarballs[@]}. Use an isolated workdir; do not guess among stale archives." >&2
  exit 1
fi
OrigTarball="${Tarballs[0]}"
UpstreamVersion="${Version}"
[[ "${OrigTarball}" == *+dfsg.orig.tar.* ]] && UpstreamVersion="${Version}+dfsg"
RepackNote="filename indicates ${UpstreamVersion}; source provenance and DFSG audit NOT VERIFIED. Unmatched exclusions may indicate moved content. Do not remove exclusions based on this filename."
DebVersion="${UpstreamVersion}-1"

# gbp.conf points debian-branch at debian/latest; import onto the local
# preparation branch instead so nothing touches the maintainer branches.
UpstreamTag="refs/tags/upstream/${UpstreamVersion}"
if git rev-parse -q --verify "${UpstreamTag}^{commit}" >/dev/null; then
  if ! git merge-base --is-ancestor "${UpstreamTag}" HEAD; then
    echo "upstream tag exists but is not integrated into ${PrepBranch}; inspect partial import manually" >&2
    exit 1
  fi
  VerifyDir="$(mktemp -d "${WorkDir}/verify-orig.XXXXXX")"
  trap 'rm -rf "${VerifyDir}"' EXIT
  if ! pristine-tar checkout "${VerifyDir}/$(basename "${OrigTarball}")" ||
     ! cmp -s "${OrigTarball}" "${VerifyDir}/$(basename "${OrigTarball}")"; then
    echo "resume archive does not match pristine-tar data or cannot be verified" >&2
    exit 1
  fi
  rm -rf "${VerifyDir}"
  trap - EXIT
  echo "note: integrated upstream tag and pristine-tar archive verified; skipping import" >&2
else
  gbp import-orig --pristine-tar --no-interactive --debian-branch="${PrepBranch}" "${OrigTarball}"
  git merge-base --is-ancestor "${UpstreamTag}" HEAD || { echo "import did not integrate upstream tag" >&2; exit 1; }
fi

if [[ "$(dpkg-parsechangelog -l debian/changelog -S Version 2>/dev/null)" == "${DebVersion}" ]]; then
  echo "note: changelog already at ${DebVersion}; skipping dch (resume)" >&2
else
  dch -v "${DebVersion}" --distribution UNRELEASED "New upstream release."
fi

BuildStatus="not run"
LintianStatus="not run"

if [[ "${RunBuild}" -eq 1 ]]; then
  BuildDir="$(mktemp -d "${WorkDir}/build-${DebVersion}.XXXXXX")"
  sbuild -d unstable --build-dir="${BuildDir}"
  BuildStatus="sbuild completed; artifacts: ${BuildDir}; inspect logs for tests/architecture"
fi

if [[ "${RunLintian}" -eq 1 ]]; then
  LintianTargets=()
  for Candidate in "${BuildDir}"/wasmedge_"${DebVersion}"_*.changes "${BuildDir}"/wasmedge_"${DebVersion}".dsc; do
    [[ -f "${Candidate}" ]] && LintianTargets+=("${Candidate}")
  done
  if [[ ${#LintianTargets[@]} -eq 0 ]]; then
    echo "no candidate .changes or .dsc in this invocation's build directory" >&2
    exit 1
  fi
  lintian "${LintianTargets[@]}"
  LintianStatus="lintian completed on this invocation's candidate artifacts only"
fi
CandidateCommit="$(git rev-parse HEAD)"
# The finalizer deliberately takes an explicit baseline rather than trusting
# this initial checkout to be the current canonical maintainer branch.
git diff --binary HEAD > "${WorkDir}/candidate-working-tree.patch"

cat > "${WorkDir}/HANDOFF.md" <<EOF
# WasmEdge Debian Packaging Handoff

Target upstream version: ${Version}
Debian version: ${DebVersion}
Packaging repo: ${RepoUrl}
Working tree: ${WorkDir}/wasmedge
Preparation branch: ${PrepBranch}
Previous branch: ${CurrentBranch}
Orig tarball: ${OrigTarball}
Repack: ${RepackNote}
Initial checkout commit (not verified canonical base): ${InitialCommit}
Candidate HEAD: ${CandidateCommit}
Uncommitted tracked changes: candidate-working-tree.patch
Freshness / live archive / existing MRs: NOT CHECKED

## Status

- Local import/changelog preparation completed; NOT upload-ready.
- Handoff regenerated by this invocation; keep review evidence separately.
- Build: ${BuildStatus}
- Lintian: ${LintianStatus}
- No branch was pushed.
- No Salsa MR was submitted.
- No Debian bug was filed.
- No Ubuntu sync/backport request was filed.
- No package was signed or uploaded.

## Impact Matrix (fill with evidence; no inferred passes)

| Area | Result | Evidence | Required action / blocker |
| --- | --- | --- | --- |
| Provenance and repack | NOT VERIFIED | archive name only | Verify origin, content and exclusions, including relocated material |
| Copyright paths and new files | NOT REVIEWED | none | Expand Files patterns; inspect renames, new licenses and attribution |
| Debian bugs / FTBFS | NOT REVIEWED | none | Verify fixes before Closes entries |
| Policy / watch | NOT REVIEWED | none | Audit compliance and release selection; do not blindly bump versions |
| ABI / symbols / reverse dependencies | NOT TESTED | none | Inspect headers, built ELF and relevant architectures |
| Generated formats / AOT | NOT TESTED | none | Check old/new producer-consumer compatibility |
| Optional components | NOT REVIEWED | none | Compare enabled options and actual shipped files |
| Runtime / upgrade / autopkgtests | NOT TESTED | none | Run candidate-specific tests and document skips |
| Publication freshness | NOT CHECKED | none | Recheck canonical HEAD, archive versions, existing proposals and maintainer decisions |

Use justified N/A only where appropriate. Build and lintian status above do not satisfy other rows.

## Required Manual Review

- Audit the complete source tree before changing repack rules; unmatched exclusions are not proof of removal.
- Inspect upstream release notes for SOVERSION, ABI/API, plugin API, dependency, or build-system changes.
- Review debian/control package names and build dependencies.
- Review symbols/shlibs handling if shared library ABI changed.
- Check reverse dependency impact if ABI changed.
- Refresh, drop, or justify debian/patches.
- Run sbuild and lintian if not already run.
- Smoke-test the built packages: install them and check that
  \`wasmedge --version\` prints ${Version}, not 0.0.0-unreleased.
- Reconcile every packaging change with the top changelog entry; do not copy all upstream release notes or invent Closes entries.
- Complete the maintainer-readiness review in references/maintainer-readiness.md.
- Reconcile final diff, changelog and evidence; optionally use scripts/finalize-debian-handoff.py as an internal aid. Do not ask contributors to fill JSON or send the internal matrix as the MR body.
- Fill in validation results before MR, bug, or sponsor request.

## Suggested Next Commands

\`\`\`bash
cd ${WorkDir}/wasmedge
git status
git diff --stat
git diff
\`\`\`

Optional validation:

\`\`\`bash
sbuild -d unstable
# Lint only explicitly verified candidate artifacts, not parent-directory globs.
\`\`\`

## External Authority Gate

Local preparation is not publication permission. Obtain explicit user approval for each external action and destination, including push, fork, MR, bug, email, comment, Debusine/PPA build submission, sync request or artifact upload. Credentials or maintainer encouragement do not grant that permission. Coordinate upload with the existing Debian maintainer/team; sponsorship does not bypass them. Track unstable acceptance, testing health and Ubuntu publication separately.
EOF

echo "Prepared local Debian packaging tree:"
echo "  ${WorkDir}/wasmedge"
echo
echo "Handoff file:"
echo "  ${WorkDir}/HANDOFF.md"
echo
echo "Stopped before push, MR submission, bug filing, requestsync, signing, or upload."
