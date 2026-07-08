---
name: wasmedge-debian-packaging
description: Use when helping WasmEdge move an upstream release through the official Debian packaging path and into Ubuntu via Debian sync, merge, or backports. Covers Debian Salsa packaging, maintainer/sponsor handoff, Ubuntu requestsync, Launchpad sync bugs, authority boundaries, and the repo-local packaging helper.
metadata:
  short-description: Push WasmEdge releases through Debian into Ubuntu
---

# WasmEdge Debian Packaging

Use this skill when the user wants the official path for updating WasmEdge packages in Ubuntu, especially when the current Ubuntu package lags behind upstream. It can also be used by an AI agent to coordinate a release handoff, provided the agent respects the archive authority boundaries and produces reviewable artifacts instead of assuming upload rights.

Core premise: upstream WasmEdge maintainers normally cannot directly update Ubuntu archive packages. The official route is to update the Debian package first, get it accepted by a Debian Developer/Maintainer or sponsor, then let Ubuntu auto-sync or request a manual sync/merge into the Ubuntu development release. Released Ubuntu series usually require backports or SRU, not a normal feature-version update.

For detailed commands, issue templates, and decision points, read [references/official-path.md](references/official-path.md).

## Default Workflow

1. Verify current state using current sources:
   - upstream release: GitHub releases
   - Debian status: Debian tracker and Salsa packaging repo
   - Ubuntu status: Launchpad source package page and Ubuntu packages
   - Repology only as a downstream status dashboard, not as an official source
2. Identify whether Debian is behind upstream.
3. Prepare or review a Debian packaging update in the Salsa repo.
4. Submit a Salsa MR and/or Debian bug with a clear maintainer handoff.
   The BTS bug path is email-only and needs no account — use it when a
   Salsa account is blocked or pending approval. Time the MR to the
   review state, not to account availability: an open maintainer or
   upstream discussion means the patches will change — wait for it to
   settle. Debusine (`debusine.debian.net`, Salsa SSO) can pre-test
   uploads on official infrastructure — see the validation section of
   [references/official-path.md](references/official-path.md). For the
   concrete fork → push → open-MR steps (SSH/ssh-add setup, pushing the
   three gbp branches + tag, the pre-filled cross-project MR URL), follow
   the "Salsa MR mechanics" section in
   [references/official-path.md](references/official-path.md).
5. After Debian accepts the package in unstable, monitor testing
   migration and reverse-dep autopkgtests (crun), handle NEW
   queue/binNMUs, and escalate if the maintainer goes quiet — see
   [references/debian-post-upload.md](references/debian-post-upload.md).
6. Check whether Ubuntu auto-sync applies; if not, triage why before
   requesting a sync, or prepare a merge when Ubuntu carries delta. Past
   Feature Freeze, file an FFe — see
   [references/ubuntu-path.md](references/ubuntu-path.md).
7. For released Ubuntu versions, assess backports first
   (`requestbackport`); use SRU only for narrowly scoped bug/security
   fixes. Procedures and templates in
   [references/ubuntu-path.md](references/ubuntu-path.md).

## AI Release Mode

When asked to drive a release, operate as a release coordinator:

1. Produce a current-state report with upstream, Debian, and Ubuntu versions.
2. Refine the report before implementation: verify Ubuntu series data, freeze timing, Debian/Ubuntu delta, and upstream ABI/API impact.
3. Decide the next official gate: Debian MR, Debian sponsor request, Ubuntu sync, Ubuntu merge, Ubuntu backport, or no action.
4. Prepare concrete artifacts: commands run, validation results, MR text, bug text, and requested reviewer/maintainer action.
5. Stop at external authority gates and tell the user exactly who must act next.

Do not claim that the release is complete until the relevant archive has
accepted the package — and the Debian stage is only done once the version
migrated to testing with reverse-dep autopkgtests passing; the Ubuntu
stage once Launchpad shows the version published in the target series.
Do not file requests or submit MRs unless the user asks for that action
and the needed credentials/tools are available.

## Authority Boundaries

- Debian archive upload requires a Debian Developer, a Debian Maintainer with package rights, or a sponsor.
- Ubuntu archive sync/merge approval requires Ubuntu archive admins or Ubuntu developers with relevant rights.
- Upstream can prepare packaging, submit merge requests, file bugs, and coordinate with maintainers, but cannot bypass archive permissions.
- A PPA or private apt repository is controlled by upstream, but it is not the official Ubuntu archive path.

## When Answering

- State clearly which stage is currently blocked by external maintainer/archive action.
- Prefer concrete next actions: MR, bug, sponsor request, sync request, or backports request.
- Use exact distro series names and package versions when available.
- Browse before answering current package status, maintainer names, Ubuntu series, or release versions.
- Do not imply that Ubuntu stable releases will automatically receive new upstream versions.
- Separate "prepared by upstream" from "accepted by Debian/Ubuntu archive".
- If upstream release notes mention `SOVERSION`, ABI, API, plugin ABI, or shared-library changes, require Debian packaging impact analysis before proposing upload.

## Useful Commands

Use these as starting points, adapting to the current packaging state:

```bash
gbp clone https://salsa.debian.org/debian/wasmedge.git
cd wasmedge
uscan --download-version <version> --force-download --repack --compression xz
gbp import-orig --pristine-tar ../wasmedge_<version>+dfsg.orig.tar.xz
dch -v <version>+dfsg-1 "New upstream release."
sbuild -d unstable
```

The Debian version suffix must match the orig tarball uscan produced: uscan
applies `Repacksuffix: +dfsg` only when `Files-Excluded` actually removed a
file. If it produced `wasmedge_<version>.orig.tar.xz` (no `+dfsg`), use
`<version>-1` and drop the repack rules from `debian/watch` and
`debian/copyright` — see the dfsg decision point in
[references/official-path.md](references/official-path.md).

If release notes claim a SOVERSION change, verify `WASMEDGE_CAPI_SOVERSION`
vs `WASMEDGE_CAPI_VERSION` in upstream `CMakeLists.txt` before renaming any
library package — the SONAME alone decides the rename.

For Ubuntu manual sync after Debian acceptance:

```bash
requestsync wasmedge <ubuntu-devel-series>
```

The second argument is the Ubuntu TARGET series (e.g. the current
development series); the Debian source defaults to unstable (`-d
unstable` to be explicit). Use `requestsync` only after confirming the
Debian version is accepted and Ubuntu has no delta that requires a merge.

## Automation Helper

For local preparation, prefer the bundled helper:

```bash
scripts/prepare-wasmedge-debian-update.sh <version>
```

The helper prepares local artifacts only. It does not push branches, submit MRs, file bugs, request Ubuntu sync, sign packages, upload packages, or change credentials. Use `--run-build` and `--run-lintian` only when the local environment is ready for Debian package builds.

On a non-Debian host (e.g. macOS), run the helper inside a container with
the workdir mounted so artifacts land on the host:

```bash
docker run --rm -v <workdir>:/work \
  -v "$(pwd)/scripts/prepare-wasmedge-debian-update.sh:/usr/local/bin/prepare.sh:ro" \
  -e DEBEMAIL=<email> -e DEBFULLNAME=<name> debian:sid bash -c '
apt-get update -qq
apt-get install -y -qq --no-install-recommends git git-buildpackage pristine-tar devscripts ca-certificates xz-utils
git config --global user.name <name>; git config --global user.email <email>
git config --global --add safe.directory "*"
bash /usr/local/bin/prepare.sh <version> --workdir /work'
```
