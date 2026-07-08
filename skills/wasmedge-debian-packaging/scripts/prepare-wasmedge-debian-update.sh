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
  --run-lintian         Run lintian after build artifacts exist.
  --no-fetch            Do not clone or download; operate on existing workdir/repo.
  -h, --help            Show this help.

This helper prepares local artifacts only. It never pushes branches, submits MRs,
files bugs, requests Ubuntu sync, uploads packages, signs packages, or changes
credentials.

Re-running after an interruption is safe: completed steps (clone, download,
import, changelog) are detected and skipped.
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
    WorkDir="${2:-}"
    shift 2
    ;;
  --repo)
    RepoUrl="${2:-}"
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

if [[ "${RunBuild}" -eq 1 ]]; then
  require_cmd sbuild
fi

if [[ "${RunLintian}" -eq 1 ]]; then
  require_cmd lintian
fi

mkdir -p "${WorkDir}"
cd "${WorkDir}"

if [[ ! -d wasmedge ]]; then
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

CurrentBranch="$(git branch --show-current || true)"
PrepBranch="wasmedge-${Version}"

if git rev-parse --verify "${PrepBranch}" >/dev/null 2>&1; then
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

# uscan applies the watch-file Repacksuffix (e.g. +dfsg) only when
# Files-Excluded actually removed something. If upstream dropped the excluded
# files, the orig tarball has no suffix and the Debian version must not
# carry +dfsg either.
RepackNote=""
OrigTarball="$(find .. -maxdepth 1 -type f -name "wasmedge_${Version}+dfsg.orig.tar.*" | sort | tail -n 1)"
if [[ -n "${OrigTarball}" ]]; then
  UpstreamVersion="${Version}+dfsg"
  RepackNote="dfsg repack applied (Files-Excluded removed files)"
else
  OrigTarball="$(find .. -maxdepth 1 -type f -name "wasmedge_${Version}.orig.tar.*" | sort | tail -n 1)"
  if [[ -n "${OrigTarball}" ]]; then
    UpstreamVersion="${Version}"
    RepackNote="no dfsg suffix: Files-Excluded matched nothing; consider dropping Repacksuffix from debian/watch and Files-Excluded from debian/copyright"
    echo "note: ${RepackNote}" >&2
  fi
fi
if [[ -z "${OrigTarball}" ]]; then
  echo "could not find ../wasmedge_${Version}+dfsg.orig.tar.* or ../wasmedge_${Version}.orig.tar.*" >&2
  echo "check debian/watch, Files-Excluded, and uscan output" >&2
  exit 1
fi
DebVersion="${UpstreamVersion}-1"

# gbp.conf points debian-branch at debian/latest; import onto the local
# preparation branch instead so nothing touches the maintainer branches.
# Skip steps a previous run already completed so re-runs are safe.
if git rev-parse -q --verify "refs/tags/upstream/${UpstreamVersion}" >/dev/null; then
  echo "note: tag upstream/${UpstreamVersion} exists; skipping gbp import-orig (resume)" >&2
else
  gbp import-orig --pristine-tar --no-interactive --debian-branch="${PrepBranch}" "${OrigTarball}"
fi

if [[ "$(dpkg-parsechangelog -l debian/changelog -S Version 2>/dev/null)" == "${DebVersion}" ]]; then
  echo "note: changelog already at ${DebVersion}; skipping dch (resume)" >&2
else
  dch -v "${DebVersion}" --distribution UNRELEASED "New upstream release."
fi

BuildStatus="not run"
LintianStatus="not run"

if [[ "${RunBuild}" -eq 1 ]]; then
  sbuild -d unstable
  BuildStatus="sbuild -d unstable completed"
fi

if [[ "${RunLintian}" -eq 1 ]]; then
  cd ..
  LintianTargets="$(find . -maxdepth 1 -type f \( -name "*.changes" -o -name "*.dsc" \) | sort)"
  if [[ -z "${LintianTargets}" ]]; then
    echo "no .changes or .dsc files found for lintian" >&2
    exit 1
  fi
  lintian ${LintianTargets}
  LintianStatus="lintian completed"
  cd wasmedge
fi

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

## Status

- Local packaging preparation completed.
- Build: ${BuildStatus}
- Lintian: ${LintianStatus}
- No branch was pushed.
- No Salsa MR was submitted.
- No Debian bug was filed.
- No Ubuntu sync/backport request was filed.
- No package was signed or uploaded.

## Required Manual Review

- Confirm +dfsg repack result and debian/copyright Files-Excluded.
- Inspect upstream release notes for SOVERSION, ABI/API, plugin API, dependency, or build-system changes.
- Review debian/control package names and build dependencies.
- Review symbols/shlibs handling if shared library ABI changed.
- Check reverse dependency impact if ABI changed.
- Refresh, drop, or justify debian/patches.
- Run sbuild and lintian if not already run.
- Smoke-test the built packages: install them and check that
  \`wasmedge --version\` prints ${Version}, not 0.0.0-unreleased.
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
lintian ../*.changes ../*.dsc
\`\`\`

## External Authority Gate

After local review, a Debian maintainer, Debian Developer, Debian Maintainer with upload rights, or sponsor must review and upload the package to Debian unstable. Only after Debian unstable accepts this version should Ubuntu sync/merge/backport handling be considered.
EOF

echo "Prepared local Debian packaging tree:"
echo "  ${WorkDir}/wasmedge"
echo
echo "Handoff file:"
echo "  ${WorkDir}/HANDOFF.md"
echo
echo "Stopped before push, MR submission, bug filing, requestsync, signing, or upload."
