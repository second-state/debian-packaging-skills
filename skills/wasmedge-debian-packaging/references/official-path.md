# Official Debian to Ubuntu Path for WasmEdge

All external-action recipes below are conditional on the explicit user approval rule in [../SKILL.md](../SKILL.md#publication-permission). Preparing a package, having credentials, or receiving maintainer encouragement does not authorize publication or external artifact submission.

## Source of Truth Checks

Always browse or query current sources before giving package-status advice:

- Upstream releases: `https://github.com/WasmEdge/WasmEdge/releases`
- Debian tracker: `https://tracker.debian.org/pkg/wasmedge`
- Debian packaging: `https://salsa.debian.org/debian/wasmedge`
- Ubuntu source package: `https://launchpad.net/ubuntu/+source/wasmedge`
- Ubuntu source packages: `https://packages.ubuntu.com/source/<series>/wasmedge`
- Ubuntu sync docs: `https://documentation.ubuntu.com/project/how-ubuntu-is-made/processes/merges-and-syncs/`
- Ubuntu requestsync docs: `https://documentation.ubuntu.com/project/contributors/uploading/request-a-sync/`
- Debian testing excuses: `https://qa.debian.org/excuses.php?package=wasmedge`
- Debian binNMU/wanna-build: `https://release.debian.org/wanna-build.html`, `https://wiki.debian.org/binNMU`
- Debian NMU/salvage: devref ch. 5, `https://wiki.debian.org/PackageSalvaging`
- Ubuntu freezes/FFe: `https://documentation.ubuntu.com/project/release-team/freeze-exceptions/`
- Ubuntu backports: `https://documentation.ubuntu.com/project/how-ubuntu-is-made/processes/backports/`
- Ubuntu SRU: `https://documentation.ubuntu.com/project/SRU/`

Repology is useful for a broad downstream view, but do not treat it as an official release or packaging authority.

## AI Release Operating Model

An AI agent may coordinate the official packaging release path, but it must treat archive upload and sync approval as external authority gates.

Entry criteria:

- target upstream version is known
- user wants the official Debian to Ubuntu route
- current Debian and Ubuntu package versions have been verified
- the agent has access to the packaging repo or can prepare instructions for a human contributor

First response requirements:

- produce a current-state report
- identify the likely next release gate
- list verification gaps before implementation
- ask before local changes, MR submission, bug filing, `requestsync`, or push operations

Exit criteria:

- Debian MR, Debian bug, sponsor request, Ubuntu sync request, merge request, or backport request is prepared with validation artifacts
- the next external actor is identified
- the current blocker is stated plainly

Report unstable acceptance, testing migration/reverse-dependency health, and Ubuntu publication as separate milestones. Gate 3.5 is monitored alongside Ubuntu work, not a universal prerequisite for sync from unstable. Confirm each claimed milestone using archive status and publishing history.

## Release Target Selection

A Debian packaging branch normally advances one upstream version at a time. When several upstream releases are available, such as a maintenance release and a newer feature release, prepare both only as local comparisons unless the maintainer explicitly asks for parallel proposals.

Use this decision:

- Recommend the newer release when it supersedes the older one and its transition, ABI, toolchain, test, and migration risks are understood.
- Recommend the maintenance release first when the newer release has a materially larger transition or compatibility risk, contains changes Debian cannot yet validate, or the maintainer wants a conservative update.
- Normally propose one target for the same suite. This is not a Debian Policy ban on parallel MRs: maintainer-requested alternatives or draft design reviews, and separate destinations such as unstable/experimental or stable maintenance, can justify multiple proposals. Obtain user approval for each external action and label the purpose clearly.
- If the first version is accepted and a later upstream version is still desired, prepare a second MR from the updated `debian/latest`. That is sequential release work, not parallel alternatives.

The handoff should state:

```text
Candidate A: <version> — maintenance or feature release, key risks
Candidate B: <version> — maintenance or feature release, key risks
Recommendation: <one version>
Reason: <why this version should be the next Debian upload>
Not submitted: <the alternative remains local only>
```

If the maintainer chooses the other candidate, preserve reusable packaging fixes and prepare from the current canonical base. Do not delete work or rewrite shared history without appropriate authorization. Discover the team's branch conventions; `debian/latest` is the WasmEdge example, not a universal branch name.

## Release Gates

Gate 1: upstream release exists.

- Confirm release version, date, tag, and source archive URL.
- Confirm whether this is newer than Debian unstable.
- Read upstream release notes for `SOVERSION`, ABI, API, plugin ABI, dependency, or build-system changes.

Gate 2: Debian packaging is ready.

- Audit repacking before choosing the Debian version. `No files matched excluded pattern` is a diagnostic, not proof of DFSG compliance: excluded content may have moved. Inspect the complete downloaded tree, additions, renamed files, licenses, and availability of source. If exclusions remain necessary, correct their patterns and rerun uscan. Drop `Files-Excluded` and `Repacksuffix` only when evidence shows repacking is no longer needed. Match the version to the verified resulting orig tarball; do not rename a tarball merely to preserve a suffix convention.
- Confirm patches are refreshed or intentionally removed.
- Confirm build dependencies are current.
- Confirm shared-library package names, symbols/shlibs handling, and reverse dependency impact when ABI changes.
- Confirm package builds in a Debian unstable environment.

ABI verification (do not trust release-notes wording):

- Release notes may say "SOVERSION bumped" when only the library file version
  changed. Verify in the upstream source: `CMakeLists.txt` sets
  `WASMEDGE_CAPI_VERSION` (file version, e.g. `libwasmedge.so.0.1.1`) and
  `WASMEDGE_CAPI_SOVERSION` (the SONAME, e.g. `libwasmedge.so.0`).
- Inspect the built ELF SONAME (for example with `readelf -d`), not only CMake variables. A SONAME change normally requires a coordinated library package transition; confirm package naming and reverse dependencies with the maintainer.
- Explicitly compare symbols and public headers. `dpkg-gensymbols` failures depend on check level and cannot detect all ABI changes, including same-name C signature changes. Review minimum dependency versions against when symbols actually became available in Debian, including Debian patches and symbol-version changes; do not blindly copy generated output. Discover current reverse dependencies; crun is a WasmEdge example.
- Per-architecture caution: C++ symbol mangling differs between
  architectures (e.g. `unsigned long` on LP64 vs ILP32). A symbols file
  regenerated from a single non-amd64 build (the containerized workflow
  on Apple Silicon builds arm64) may be wrong on the amd64 buildds. For
  C symbols this rarely matters; for `(c++)` entries, reason explicitly
  about the types involved, use `(arch=...)`/`(optional)` tags where they
  genuinely differ, and say in the handoff which architecture generated
  the diff. Validate each relevant architecture; amd64 success does not establish correctness elsewhere. Do not mark required symbols optional merely to silence a failure.
- If a release removes exported symbols, or changes the signature of a
  symbol while keeping its name, under an unchanged SONAME, treat it as a
  real ABI break — not a routine symbols-file update. (dpkg-gensymbols
  does not catch a same-name C signature change, so it will not stop
  you.) Flag it to the maintainer and resolve it before upload rather
  than shipping silently; the fix is the maintainer's call.
- The standard ways to absorb such a break are ELF symbol versioning
  (keep the SONAME; export the old and new implementations as distinct
  versioned symbols so already-compiled consumers keep resolving the old
  one) or a SONAME bump (rename the library package and rebuild every
  reverse dependency). Name both options in the handoff; the choice is
  upstream's or the maintainer's.

Gate 3: Debian archive acceptance.

- Confirm package is accepted in Debian unstable before treating it as syncable to Ubuntu.
- If not accepted, the next action is maintainer review, sponsor upload, or Debian bug follow-up.
- A binary package rename (library transition) routes the upload through
  the NEW queue: manual ftp-master review, days to weeks. See
  [debian-post-upload.md](debian-post-upload.md).

Gate 3.5: Debian testing migration and reverse dependencies.

- Acceptance into unstable is not health: monitor britney excuses until
  the package migrates to testing and reverse-dep autopkgtests (crun)
  pass. ABI changes are the main cause of being stuck here.
- binNMUs of reverse deps, dak REJECT handling, and the
  maintainer-unresponsive escalation ladder are covered in
  [debian-post-upload.md](debian-post-upload.md).

Gate 4: Ubuntu development release sync or merge.

- Confirm target Ubuntu development series.
- Confirm whether Ubuntu has package delta.
- If no delta, sync can be requested.
- If delta exists, a merge is required.
- Auto-sync mechanics/verification, no-sync triage, the merge procedure,
  Feature Freeze Exceptions, and Ubuntu-side build failures are covered
  in [ubuntu-path.md](ubuntu-path.md).

Gate 5: Ubuntu stable availability.

- Use backports for feature releases in stable series.
- Use SRU only for narrowly scoped fixes with a regression analysis.
- Concrete backports (`requestbackport`) and SRU procedures with
  templates: [ubuntu-path.md](ubuntu-path.md).

## Decision Tree

### 1. Debian is behind upstream

Goal: get a new Debian upload accepted.

Actions:

- Clone the Salsa packaging repo.
- Download the target upstream version explicitly with `uscan --download-version <version>`.
  If uscan finds or downloads nothing, the watch file is likely broken by
  an upstream URL/tag-scheme change: debug with
  `uscan --verbose --no-download`, fix `debian/watch` (the fix belongs in
  the MR), and re-run.
- If `gbp import-orig` fails, inspect branch ancestry, the existing upstream tag, pristine-tar and dirty files. Preserve work and capture the failure. Prefer a new isolated preparation directory; do not delete branches/tags, reset shared history, or disable pristine-tar merely to bypass the error. Obtain scoped approval before destructive recovery.
- Verify source provenance and content separately. Validate upstream signatures or authenticated checksums when available and record the trust source and archive digest. Safely extract the downloaded archive into a separate temporary directory and actually compare its content with an export of the verified upstream tag (for example, directory-to-directory `diff -ruN`). Account for export exclusions, submodules, generated release files and documented Debian repacking; investigate unexplained differences. `git diff <tag>` in an unrelated checkout and a commit identifier in a directory name do not verify archive content or authenticity. Record limitations if authenticated provenance is unavailable.
- If the build FTBFS in sid: read the FIRST error in the build log, then
  classify — (a) new toolchain default (sid moved to a newer GCC/LLVM:
  check upstream for an existing fix to cherry-pick as a
  `debian/patches` entry), (b) missing/too-old build dependency (adjust
  `debian/control` and say why in the changelog), (c) test failure
  (investigate; `DEB_BUILD_OPTIONS=nocheck` is for local iteration only,
  not proof of upload readiness). For a patch that no longer applies, inspect and resolve every rejected hunk before refreshing with quilt or gbp pq. Verify the intended fix survives; never use force/refresh to silently discard changes. Drop an upstreamed patch only with evidence and a changelog note.
- Import the new upstream tarball with the existing `+dfsg` repack rules after confirming the generated tarball name.
- Refresh or drop `debian/patches` as needed.
- Update `debian/changelog`.
- Review `debian/control`, build dependencies, LLVM compatibility, symbols/shlibs, package names, reverse dependencies, and tests.
- Review all relevant Debian bugs and FTBFS reports; determine which are fixed by the upstream release and list only verified bug numbers in `debian/changelog` `Closes:` entries.
- Compare upstream trees with rename detection and audit packaging references:
  `git diff --find-renames --summary <old-upstream>..<new-upstream>`. Check moved or deleted paths against `debian/copyright`, install files, patches, tests, and build rules. A removed `Files-Excluded` entry does not complete the copyright review if other tracked paths moved.
- If the package has serialized or generated artifacts (for WasmEdge, this includes AOT output), check artifact format/version compatibility and state whether old artifacts need regeneration.
- If the upstream project has optional plugins, bindings, or backends, compare upstream changes with Debian's enabled build options and shipped files; record why each relevant change does or does not affect the package.
- Build with `sbuild -d unstable`.
- Run package checks such as `lintian` if available. Triage by severity:
  `E:` must be fixed or overridden with a justification
  (`debian/<pkg>.lintian-overrides`), `W:` fixed or explained in the
  handoff, `I:`/`P:` optional. `lintian-explain-tags <tag>` explains any
  tag.
- Smoke-test the built packages: install them and run `wasmedge --version`.
  Upstream CMake derives the version from git-describe and falls back to
  `0.0.0-unreleased` in tarball builds unless a `VERSION` file exists at the
  source root. If the binary reports `0.0.0-unreleased`, have
  `debian/rules` generate `VERSION` from `DEB_VERSION_UPSTREAM`
  (`/usr/share/dpkg/pkg-info.mk`) before configure and remove it in clean.
- Optional pre-upload testing via Debusine (`debusine.debian.net`):
  submit the source package and it builds in clean environments across
  five architectures and runs lintian + autopkgtest (including
  reverse-dep autopkgtests) on official infrastructure — this covers
  exactly what a local container build cannot (clean chroot, amd64,
  test suite). Login is Salsa SSO; accounts are auto-created for
  DDs/DMs, other contributors may need to request access. Workflow:
  install `debusine-client`, `debusine --server=debian setup`, then
  `dput -O debusine_workflow=upload-to-unstable -O
  debusine_workflow_data.enable_upload=false debusine.debian.net
  <pkg>_<ver>_source.changes` (test-only, no upload). Docs:
  https://wiki.debian.org/DebusineDebianNet
- Submit a Salsa MR — but time it to the review state, do not open one
  just because the account became available:
  - Open design questions (e.g. an ABI approach the maintainer put on
    hold pending an upstream decision) mean the patches will change:
    wait for the discussion to settle and the patches to be final, or
    open the MR only if the maintainer asks for one, marking it as
    pending the open discussion in the description.
  - No open questions and patches final: open the MR, referencing the
    BTS bug number if one exists.
  - A half-baked MR creates a second review thread the maintainer must
    answer with "waiting on X" — it adds noise, not progress.
- Open a Debian bug or contact the package maintainer if appropriate.
  The BTS path needs no account and is the official fallback when a Salsa
  account is blocked or pending approval — see "Debian BTS Submission"
  below.
- Coordinate upload with the existing Debian maintainer/team first. Seek sponsorship when appropriate to that arrangement; a sponsor's upload rights do not authorize bypassing the maintainer's release plan.

Automation option:

```bash
scripts/prepare-wasmedge-debian-update.sh <version>
```

Use optional validation only when the local Debian build environment is ready:

```bash
scripts/prepare-wasmedge-debian-update.sh <version> --run-build --run-lintian
```

The helper stops after local preparation and writes `HANDOFF.md` in the working directory. Review the generated tree before any push, MR, bug, `requestsync`, signing, or upload.

Containerized build validation on a non-Debian host (no sbuild available):

```bash
docker run --rm -v <workdir>:/work -w /work/wasmedge \
  -e DEB_BUILD_OPTIONS=nocheck debian:sid bash -c '
sed -i "s/^Types: deb$/Types: deb deb-src/" /etc/apt/sources.list.d/*.sources
apt-get update -qq
apt-get install -y --no-install-recommends build-essential devscripts lintian
apt-get build-dep -y ./
dpkg-buildpackage -us -uc -b
lintian ../*.changes
apt-get install -y ../wasmedge_*.deb ../libwasmedge0_*.deb
wasmedge --version'
```

Record these limitations in the handoff when validating this way:

- `dpkg-buildpackage` in a container is not a clean sbuild chroot; the
  maintainer/sponsor must still run `sbuild -d unstable` before upload.
- The container architecture may differ from the amd64 buildds (e.g. arm64
  on Apple Silicon); note the build arch.
- `DEB_BUILD_OPTIONS=nocheck` skips the test suite; drop it or note that
  tests were skipped.

Expected blocker: archive upload depends on Debian maintainer, DD, DM, or sponsor action.

Required artifacts:

- upstream release URL
- imported orig tarball version
- summary of `+dfsg` repack result
- ABI/API impact summary, including `SOVERSION` or plugin API changes if present
- patch refresh summary
- build log summary
- test summary
- lintian summary if available
- proposed `debian/changelog` entry

### 2. Debian unstable has the desired version, Ubuntu development does not

Goal: get Ubuntu development release updated from Debian.

Check whether Ubuntu has delta:

```bash
rmadison -u ubuntu wasmedge
rmadison -u debian wasmedge
```

Also verify Launchpad and package pages when available, because Ubuntu development series names and versions can change during the release cycle.

If Ubuntu has no delta and the auto-sync window is open, wait for auto-sync or file a manual sync request.

If manual sync is needed:

```bash
requestsync wasmedge <ubuntu-devel-series>
```

(The positional argument after the package is the Ubuntu TARGET series,
not the Debian source suite — `requestsync` defaults to syncing from
Debian unstable; pass `-d` only to choose a different Debian suite.)

If Ubuntu has delta, prepare or request a merge instead of a sync.

Expected blocker: sync/merge depends on Ubuntu archive admin or Ubuntu developer action.

Before `requestsync`, check:

- Ubuntu target series is the development series
- Debian unstable contains the desired version
- Ubuntu carries no delta, or the delta is obsolete
- Ubuntu is not past a freeze point that makes sync inappropriate without extra justification

If Ubuntu has a version suffix such as `ubuntu1`, inspect the changelog or source diff before requesting sync.

### 3. Ubuntu development has the desired version, released Ubuntu does not

Goal: serve users on stable Ubuntu releases.

Options:

- Backports: preferred for newer feature releases in stable Ubuntu series.
- SRU: only for important bug fixes with minimal regression risk, not general new upstream feature releases.
- PPA: controlled by upstream, useful for fast user access, but not official Ubuntu archive.

For the official archive route, request backports after the package is in the Ubuntu development release.

## Debian BTS Submission (no account needed)

The BTS (debbugs) is email-driven and requires no registration; identity
checks happen only at archive upload (GPG). Use it when Salsa is
unavailable (e.g. account pending approval) or alongside an MR.

1. Email `submit@bugs.debian.org`. The mail body MUST start with
   pseudo-headers:

   ```
   Package: wasmedge
   Version: <version currently in unstable>
   Severity: wishlist
   X-Debbugs-Cc: <your-address>, <maintainer-address>
   ```

   `Severity: wishlist` is the convention for new-upstream-release
   requests. `Version:` is the archive version the request applies to,
   not the new one.
2. Attach the prepared work. Commit any hand edits on the prep branch
   first, then, from inside the packaging clone (`<workdir>/wasmedge`):

   ```bash
   git format-patch -o ../patches debian/latest..<prep-branch> -- debian/
   ```

   `-o ../patches` keeps the series in the workdir instead of littering
   the packaging clone.

   The `-- debian/` path filter is required: without it the series also
   contains the huge `gbp import-orig` upstream-import and merge commits.
   The orig tarball is not attached either — the maintainer regenerates it
   with uscan. Include the maintainer-handoff content from this document.
3. Tag it as carrying a patch by adding a first body line
   `Control: tags -1 + patch` (before the free text), or send
   `tags <bugno> + patch` to `control@bugs.debian.org` afterwards.
4. The bug number is auto-assigned: debbugs replies to the sender with
   `Bug#<nnnnnn>: Acknowledgement ...` within minutes. The bug is public at
   `https://bugs.debian.org/<nnnnnn>`. Follow-ups go to
   `<nnnnnn>@bugs.debian.org`.
   No acknowledgement within ~30 minutes: check
   `https://bugs.debian.org/wasmedge` for the bug anyway (ack mail can be
   spam-filtered); if absent, the usual cause is HTML mail breaking the
   pseudo-header parsing — re-send as plain text from the same address.
5. Wire the number back: add `(Closes: #<nnnnnn>)` to the
   `debian/changelog` entry — archive acceptance then closes the bug
   automatically — and reference the bug in the eventual Salsa MR. Bug,
   MR, and upload stay linked by the one number.

Send the mail as plain text. HTML mail (the Gmail default) can break
debbugs' parsing of the pseudo-headers and `Control:` lines — in Gmail
enable plain-text mode before sending. The pseudo-headers must be the
very first lines of the body, with nothing above them.

Salsa account timing: registration on salsa.debian.org requires manual
admin approval, which can take days to weeks. Register at the START of
the packaging work, not at submission time; if the account is still
pending when the work is ready, submit via this BTS path and reference
the bug from the MR later.

When the account is approved mid-flow (after a BTS submission), the
approval unlocks tooling but changes no gate:

- Unlocked: pushing the packaging branch, opening the Salsa MR
  (subject to the MR-timing rule above — an open maintainer/upstream
  discussion still means wait), and Debusine pre-upload testing.
- Unchanged: whatever the submission was waiting on (maintainer review,
  an upstream decision, sponsor action) is still the active gate. Do
  not treat account approval as a cue to act — re-check what the
  actual blocker is first.
- Worth doing immediately: verify the login works and note the
  username in the handoff/status record, so the MR step has no
  surprises later.

### Debian Bug Email Template

```text
To: submit@bugs.debian.org
Subject: wasmedge: prepared packaging update for <debian-version>

Package: wasmedge
Version: <version currently in unstable>
Severity: wishlist
X-Debbugs-Cc: <your-address>

Control: tags -1 + patch

<maintainer-handoff content: upstream release URL, packaging notes,
validation results, ABI/API impact, Ubuntu sync intent — same fields as
the Salsa MR template>

The prepared changes are attached as a git format-patch series against
debian/latest. A sponsor upload is welcome if more convenient.
```

## Salsa MR mechanics (fork -> push -> open)

For a Salsa-hosted gbp package the standard delivery is a merge request
from a personal fork. The BTS bug stays the tracking anchor; the MR is the
reviewable change. Only the debian branch is reviewed, but push all three
gbp branches so the fork is buildable.

1. Fork the packaging repo on Salsa (web UI "Fork") into your namespace,
   then add it as a remote:

   ```sh
   git remote add fork git@salsa.debian.org:<user>/wasmedge.git
   ```

2. SSH prerequisites (Salsa refuses HTTPS git push without a token, so SSH
   is simpler for pushing):
   - Add your PUBLIC key on the website at
     `https://salsa.debian.org/-/user_settings/ssh_keys`. This is separate
     from `ssh-add`: the site needs the key, the agent needs it loaded.
   - If the key is passphrase-protected, load it first
     (`ssh-add ~/.ssh/id_ed25519`); a key the agent isn't offering yields
     `Permission denied (publickey)`.
   - Verify: `ssh -T git@salsa.debian.org` -> `Welcome to GitLab, @<user>!`.
   - Repeated failed attempts trip Salsa's fail2ban: further connections
     fail with `kex_exchange_identification: Connection reset by peer`.
     That is a temporary IP ban (minutes), not an auth error -- stop
     retrying and wait; confirm Salsa itself is up over HTTPS meanwhile.

3. Check the final publication gate below. Prepare a focused range against the current canonical base, excluding unselected candidate imports. Preserve separate logical packaging commits unless the maintainer requests squashing. Follow the repository's gbp/pristine-tar conventions rather than requiring one packaging commit. Preserve existing work; prefer a fresh preparation branch over destructive resets.

4. Push the gbp branches + upstream tag to the fork:

   ```sh
   git push fork debian/<ver>       # MR source branch
   git push fork upstream/latest
   git push fork pristine-tar
   git push fork upstream/<ver>     # the upstream tag
   ```

   pristine-tar lets the maintainer regenerate the exact orig tarball;
   push only debian/<ver> and the fork is not independently buildable.

5. Open the cross-project MR (fork -> canonical `debian/latest`). Creating
   an MR needs the GitLab API (a token) or the web UI -- an SSH key alone
   cannot. Without a token, build a pre-filled URL and click Create. Get
   the canonical project id from the public API:

   ```sh
   curl -s https://salsa.debian.org/api/v4/projects/debian%2Fwasmedge \
     | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])'
   ```

   ```
   https://salsa.debian.org/<user>/wasmedge/-/merge_requests/new?merge_request%5Bsource_branch%5D=debian/<ver>&merge_request%5Btarget_project_id%5D=<id>&merge_request%5Btarget_branch%5D=debian/latest&merge_request%5Btitle%5D=<url-encoded title>
   ```

   Confirm target = `debian/wasmedge : debian/latest` before submitting.

6. GitLab pre-fills the description from the branch commit message (markdown
   line breaks collapse into one blob). Replace it with a proper MR
   description (see the Salsa MR template below): upstream URL, packaging
   notes, ABI/symbols impact, validation results, reverse-dep note, Ubuntu
   sync intent.

7. Wire it to the bug: the changelog already carries `Closes: #<bug>`, and
   the MR title/body should reference the bug; post a one-line note on the
   bug pointing to the MR URL so bug and MR stay linked.

8. Confirm the MR landed even if the UI shows a stray error (e.g. a "to-do
   item" toast): query it via the public API rather than trusting the
   toast --
   `curl -s "https://salsa.debian.org/api/v4/projects/<id>/merge_requests?source_branch=debian/<ver>&state=all"`.

## Timing and Freeze Checks

Before requesting Ubuntu sync, check the Ubuntu development release schedule, Debian import status, and current development series. If Debian Import Freeze or Feature Freeze has passed, expect additional justification or a merge/backport-specific path.

Before planning a Debian upload, check whether Debian is in a freeze period and whether a new upstream release is appropriate for unstable at that point.

If freeze timing blocks normal sync, report the freeze as the blocker and propose the next realistic route.

## Final Publication Gate

Immediately before any authorized publication, recheck canonical HEAD, archive versions, existing MRs/bugs and maintainer decisions. Record the base commit and candidate commit. If equivalent or newer work supersedes the proposal, stop and reconcile rather than publishing a duplicate. Rebase or regenerate safely when needed and validate the final tree; old candidate build logs do not validate a changed candidate. Missing online access means freshness is unverified, not passed.

## Required Validation Artifacts

Maintain an internal impact record (matrix or equivalent review notes) with result, evidence, required action and unresolved blocker for: source provenance/repack/licensing; renamed and added files; Debian bugs/FTBFS; policy/watch changes; ABI and reverse dependencies; generated formats; optional components; build/runtime/autopkgtests. Use justified `not applicable` or explicit `not tested`, never inferred passes.

Review applicable Debian Policy changes before bumping Standards-Version. Review watch matching, version mangling, stable/prerelease selection, signatures and repacking; preserve maintainer policy unless a change is justified. These are not automatic version/style upgrades.

Validate clean source regeneration, build isolation and offline build behavior where applicable, install/upgrade behavior, actual runtime execution, package autopkgtests and relevant reverse dependencies. Record candidate hash, architecture, dependency versions and skipped tests. `--version` alone is insufficient functional coverage.


For Debian MR or sponsor request, summarize relevant results below in a few factual lines. Do not attach the entire internal impact record or logs by default. Include targeted evidence if required by the template, needed for a failure, or requested by the maintainer; external attachments still require approval.

- source package build result
- binary package build result
- test result
- lintian result if available
- dependency changes
- ABI/API impact, especially `SOVERSION`, shared library package names, symbols/shlibs, plugin API, and reverse dependencies
- patch refresh summary
- known skipped tests or platform constraints

For Ubuntu sync, merge, or backport, attach or summarize:

- Debian version accepted in unstable
- Ubuntu target series
- Ubuntu delta status
- build/test result
- regression risk
- freeze or backport justification if relevant

## Maintainer Handoff Checklist

Before preparing a submission, follow [maintainer-readiness.md](maintainer-readiness.md). Reconcile the final Debian diff, changelog and candidate-specific evidence; the local finalizer is an optional internal aid, not a contributor form. A successful preparation is not a completed metadata audit, and finalization is not permission to publish.

Complete the internal impact and freshness review before a Debian MR or bug. Present only relevant changes, verified tests, material limitations and decisions needed from the maintainer; do not paste the whole matrix. Do not infer a rejection reason from an MR's closed status; compare final trees and review evidence.

Also include:

- upstream version and release URL
- summary of important upstream changes
- confirmation of `+dfsg` repack status
- build log summary
- test results
- ABI/API impact summary
- known dependency or LLVM-version changes
- changed patches and why
- whether Ubuntu sync/backport is intended after Debian acceptance

For Ubuntu sync request, include:

- Debian version to sync
- Ubuntu development series
- confirmation that Ubuntu has no delta, or explanation if it does
- changelog summary
- Debian acceptance reference
- build/test notes where relevant

## Communication Templates

### Debian Salsa MR Description

Follow the repository's current template first. This is a fallback outline, not text to paste unchanged. Omit inapplicable sections and placeholders; include required assistance disclosure separately where project rules require it. No claims below are pre-approved facts.

```text
Update wasmedge to <debian-version>.

<One sentence explaining the Debian-relevant benefit.>
Upstream release: <release-url>

Packaging changes:
- <Logical change and reason; omit unchanged metadata.>

Tests:
- <Actual command, architecture/environment, and result.>
- <Relevant limitation or warning, if any.>

<Material ABI/upgrade concern or a specific maintainer decision, if needed.>
```

Do not add a generic Ubuntu intent paragraph unless it is relevant to the request. Put background links after the actionable information. For a bug report, retain the minimal reproducer and expected/actual result; brevity does not justify dropping required OS/version/architecture fields.

### Pre-Implementation Refinement Prompt

```text
Before preparing the packaging update, refine the release plan:
1. Use an explicit target version with uscan, such as `uscan --download-version <version>`.
2. Reconfirm upstream, Debian, and Ubuntu series/version data from authoritative sources.
3. Check Ubuntu development-series timing, freeze status, and whether Ubuntu carries delta.
4. Inspect upstream release notes for SOVERSION, ABI/API, plugin API, dependency, or build-system changes.
5. Identify Debian packaging files likely affected: debian/control, debian/*.symbols, shlibs handling, package names, debian/patches, debian/copyright, and tests.
6. Stop before MR submission, bug filing, requestsync, push, or upload.
```

### Ubuntu Sync Request Rationale

```text
Please sync wasmedge <debian-version> from Debian unstable into <ubuntu-series>.

Rationale:
- New upstream release packaged in Debian unstable.
- Ubuntu currently carries no delta / Ubuntu delta status: <status>.
- Build/test status: <status>.
- This update is intended for the Ubuntu development release. Stable series can be considered separately through backports if appropriate.
```

## Common Pitfalls

- Do not ask for SRU just because upstream has a newer release.
- Do not request sync while Ubuntu carries delta unless the delta is obsolete or a merge is prepared.
- Do not skip Debian if the goal is the normal official Ubuntu archive path.
- Do not describe PPA as official Ubuntu archive packaging.
- Do not rely on Repology for maintainer identity or archive state.
