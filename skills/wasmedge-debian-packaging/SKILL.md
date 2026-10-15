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

## Harness-neutral workflow contract

**Explicit invocation rule:** When the user explicitly invokes this skill with no
additional task text, immediately treat it as the `draft` intent. Do not reply
with a generic "what would you like me to work on?" question. Start discovery:
check the current upstream/Debian versions, inspect bounded workspace state,
propose the target and workspace, and ask only the compact identity/version
question required before local preparation. A skill being auto-loaded by a host
without an explicit user request does not start work.

Read [references/decision-contract.md](references/decision-contract.md) first. It defines dynamic options; versions and risk labels must be generated from current sources. Then read [references/command-contract.md](references/command-contract.md). This skill defines workflow intents and gates, not a slash command, chat command, extension API or harness-specific function. A host integration may map user input to these intents, but must preserve their order, evidence rules and authority boundaries.

- **prepare/draft intent:** complete local `prepare → review → validate → handoff` and produce an editable candidate. Stop at `READY_FOR_REVIEW`, `BLOCKED` or one concrete owner/maintainer decision. Helper success is not completion.
- **status intent:** read-only; show candidate version, canonical base, exact workspace, current stage, stale/failed evidence, readiness and retained artifacts. Never prepare, delete, push or publish.
- **publish intent:** submit only the exact reviewed candidate after account, fork, destination, content and explicit human-approval checks. It is not Debian archive upload. Return a verified MR URL, not archive acceptance.
- **resume intent:** reuse unchanged completed stages only after live candidate identity/evidence checks; otherwise create a recovery plan and explain the invalidation.

The host must not ask the contributor to write internal JSON or select routine commands. Use `scripts/release-workflow.py` for durable local stages and `scripts/submit-mr.py` for preview/transport; generate their plans internally. No host may infer publication permission from skill invocation, login state or a readiness result.

## Draft completion and recovery

Do not stop a draft merely because a runner attempt is BLOCKED. Diagnose local
failures and, within existing authorization, repair ordinary packaging/test/doc
mismatches, update changelog, and rerun affected validation using a new recovery
state in the same workspace. A failed command is not automatically an owner-only
decision. Follow the bounded recovery rules in command-contract.md.

Run installed-package runtime tests during validate, NOT after reporting stage
completion. Before handoff use `scripts/check-validation.py` to reject pending
semantic/runtime checks and missing or changed logs. Never declare readiness from
build/lintian success alone. Preserve real upstream blockers; do not disable tests
or change expected behavior simply to pass. If necessary evidence or authorization
is genuinely unavailable, explain the specific blocker, not a generic next-step
list the contributor must drive.

## Publication Permission

Local preparation does not authorize external action. Obtain explicit user approval for the destination, action, and content before any push, fork, MR, bug, email, comment, sync request, external build submission (including Debusine), or artifact upload. This applies even when archive upload is disabled. Credentials, account approval, maintainer encouragement, and example commands are not user permission. Private messages also require approval. Existing approval applies only within its stated scope; otherwise keep drafts local.

## Guided Preparation and Final Review

Before preparation, follow [references/workspace-lifecycle.md](references/workspace-lifecycle.md) to show the detected series/version, canonical baseline, exact proposed workdir, existing candidate state and cleanup/retention scope. Never reuse or delete work based on its directory name. Group missing path/resume/cleanup decisions with the identity questionnaire. Then follow [references/contributor-onboarding.md](references/contributor-onboarding.md): inspect prior owner decisions, detect GitHub/Git/Debian identity candidates read-only, and obtain any missing human confirmation in one compact questionnaire. In Pi with auto-reply, use `inevitable_auto_reply` with `responseMode: "user"` for identity or new scope/authorization; never delegate those choices to a model. Apply approved identity only to the invocation and verify the resulting new commits/changelog. Cancelled input pauses preparation; identity consent never authorizes publication. Then follow [references/maintainer-readiness.md](references/maintainer-readiness.md). After packaging edits, reconcile the final Debian diff with changelog and validation evidence. Optionally use `scripts/finalize-debian-handoff.py` as an internal consistency aid; the assistant prepares its inputs, not the contributor. The helper's preparation HANDOFF is not a final submission report; successful consistency checking never authorizes publication.

For public text, follow the project's required template in English with concise factual wording. Draft logical changelog entries, a focused patch explanation and relevant test results; ask the contributor only for missing intent, identity, material decisions and authorization. Keep internal matrices/hashes and execution diaries local, not mandatory reviewer reading. Natural language must not conceal required AI-assistance disclosures or fabricate personal experience. See the writing guidance in maintainer-readiness.md.

## Default Workflow

1. Verify current state using current sources:
   - upstream release: GitHub releases
   - Debian status: Debian tracker and Salsa packaging repo
   - Ubuntu status: Launchpad source package page and Ubuntu packages
   - Repology only as a downstream status dashboard, not as an official source
2. Identify whether Debian is behind upstream.
3. Select one proposed upstream target for the Debian update before preparing the package.
   - `debian/latest` is a linear release path: do not prepare competing public MRs for two upstream versions from the same base unless the maintainer explicitly requests parallel options.
   - If multiple upstream versions are available (for example, a maintenance release and a newer feature release), analyze both locally but recommend one target. Prefer the newer target when it is acceptable and supersedes the older one; prefer the maintenance target when the newer release has materially higher transition, ABI, toolchain, or migration risk, or when the maintainer asks for it.
   - Keep the non-selected version as a local comparison artifact, not a second public MR. If the maintainer chooses the other version, regenerate the package from the current `debian/latest` rather than stacking both proposals.
4. Prepare or review a Debian packaging update in the Salsa repo.
5. Submit a Salsa MR and/or Debian bug with a clear maintainer handoff.
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
6. After Debian accepts the package in unstable, monitor testing
   migration and reverse-dep autopkgtests (crun), handle NEW
   queue/binNMUs, and escalate if the maintainer goes quiet — see
   [references/debian-post-upload.md](references/debian-post-upload.md).
7. Check whether Ubuntu auto-sync applies; if not, triage why before
   requesting a sync, or prepare a merge when Ubuntu carries delta. Past
   Feature Freeze, file an FFe — see
   [references/ubuntu-path.md](references/ubuntu-path.md).
8. For released Ubuntu versions, assess backports first
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

Track separate milestones: Debian unstable acceptance, Debian testing migration and reverse-dependency health, and Ubuntu publication in the requested series/pocket. Report each explicitly; aging is not completed migration. Ubuntu sync from unstable need not wait for Debian testing migration, but assess known regressions before recommending it. Never claim an unverified milestone or publish without the permission above.

## Release Impact Review

Before deciding that an upstream release is ready for Debian, classify changes beyond ordinary source updates. These checks are conditional: do them when the package actually contains the affected component.

- **Serialized or generated artifacts:** check whether caches, bytecode, AOT files, model files, or other generated outputs changed format or version. If old artifacts require regeneration, record that as a compatibility or migration note and test the producer/consumer pairing.
- **Optional components:** check plugins, bindings, backends, examples, and optional modules for additions, removals, renamed exports, changed dependencies, or changed build switches. Compare this with what Debian actually builds and ships; an upstream plugin change may require no Debian change when that component is disabled, but the conclusion must be recorded.
- **Shared-library ABI:** when the package ships a shared library, inspect SONAME, exported symbols, signatures, public structs, symbol versions, C++ ABI, and reverse dependencies. An unchanged SONAME does not prove ABI compatibility. When the package is not a shared library, do not invent a library transition review.
- **Toolchain and build portability:** inspect Debian bugs, FTBFS reports, release notes, CI results, and the current unstable compiler/LLVM stack. Classify failures as upstream fixes, packaging/build-dependency issues, or test-only failures. Do not claim a local build proves current Debian buildability.

Also compare the upstream tree, not only release notes:

```bash
git diff --find-renames --summary <old-upstream>..<new-upstream>
```

Use detected adds, deletes, and renames to audit Debian metadata and packaging references, especially `debian/copyright`, install files, patches, tests, and build rules. Expand `Files:` patterns using Debian copyright-format semantics, rather than treating them as literal paths. Investigate unmatched patterns, moved files, and new files lacking accurate license/copyright coverage. Update paths and years from source evidence, not mechanically from the current date.

The one-target rule is a default for competing updates to the same suite, not Debian Policy. Distinct destinations (such as unstable versus experimental or stable maintenance) and maintainer-requested draft alternatives may justify separate MRs, still subject to user approval. Discover actual branch conventions and reverse dependencies rather than assuming every package uses `debian/latest` or depends on crun.

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
file. An unmatched exclusion or plain tarball does not prove the excluded content disappeared: it may have moved. Audit the complete new source tree and licensing first. Update exclusions and rerun uscan if needed; drop repack metadata only after confirming it is no longer required. Use the resulting verified tarball name — see the dfsg decision point in
[references/official-path.md](references/official-path.md).

If release notes claim a SOVERSION change, verify `WASMEDGE_CAPI_SOVERSION`
vs `WASMEDGE_CAPI_VERSION` in upstream `CMakeLists.txt` before renaming any
library package, then verify the built ELF SONAME. Coordinate package naming and any transition with the maintainer; unchanged SONAME does not establish ABI safety.

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
export GIT_AUTHOR_NAME="$DEBFULLNAME" GIT_AUTHOR_EMAIL="$DEBEMAIL"
export GIT_COMMITTER_NAME="$DEBFULLNAME" GIT_COMMITTER_EMAIL="$DEBEMAIL"
bash /usr/local/bin/prepare.sh <version> --workdir /work'
```
