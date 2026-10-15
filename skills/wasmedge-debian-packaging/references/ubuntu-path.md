# Ubuntu: From Debian to Users

How a wasmedge version that reached Debian actually lands in Ubuntu — the
development series first, then released series via backports or SRU.
For sync from unstable, verify Debian unstable acceptance and assess known regressions. Debian testing migration is a separate health milestone, not a universal prerequisite. All external actions below, including PPA builds, messages and uploads, require explicit user approval under [../SKILL.md](../SKILL.md#publication-permission).

## Auto-sync

- Mechanics: Ubuntu imports new/higher versions automatically from
  **Debian unstable**, from the opening of each development series until
  **Debian Import Freeze (DIF)**. Packages carrying Ubuntu delta are
  skipped. Reference:
  `https://documentation.ubuntu.com/project/how-ubuntu-is-made/processes/merges-and-syncs/`
- Confirm a sync happened:
  `https://launchpad.net/ubuntu/+source/wasmedge/+publishinghistory`
  (or `rmadison -u ubuntu wasmedge`). Allow a few days after Debian
  acceptance.

### Auto-sync did not pick the package (no delta, window open)

Triage before falling back to a manual request:

1. Version actually higher? (`dpkg --compare-versions`, mind `+dfsg` vs
   plain suffix ordering)
2. Package on the sync blocklist, or stuck in Ubuntu `-proposed`? Check
   the publishing history and
   `https://ubuntu-archive-team.ubuntu.com/proposed-migration/` (Ubuntu
   runs its own britney; see "proposed migration" below).
3. Inspect actual Ubuntu source changes. A `build1` no-change rebuild does not establish substantive delta; a version suffix alone cannot decide sync versus merge. Preserve needed Ubuntu changes through a merge, or justify dropping obsolete delta when syncing.
4. Only then: request a manual sync.

## Manual sync

```bash
requestsync wasmedge <ubuntu-devel-series>
```

(`requestsync` from `ubuntu-dev-tools` files the Launchpad sync-request
bug for you; an Ubuntu developer or archive admin executes it with
`syncpackage`.) Pre-checks as in the Decision Tree: development series
target, version present in unstable, no Ubuntu delta (or delta obsolete —
state why in the bug), freeze status. Docs:
`https://documentation.ubuntu.com/project/contributors/uploading/request-a-sync/`

## Merge (Ubuntu carries delta)

When Ubuntu has substantive local changes that still need preserving, the new Debian version must be **merged**, not synced. The current official procedure uses
**git-ubuntu**; Merge-o-Matic remains useful for FINDING outstanding
merges, not for performing them:

1. Identify the merge: `https://merges.ubuntu.com/` lists outstanding
   merges per component (universe for wasmedge).
2. Perform the merge with `git-ubuntu`: clone the package repo, replay
   the Ubuntu delta onto the new Debian version rebase-style with the
   documented `split`/`logical`/`reconstruct` tags, deciding per delta
   chunk — still needed (keep), upstreamed/fixed in Debian (drop, and
   say so in the changelog), or obsolete. Full how-to:
   `https://documentation.ubuntu.com/project/contributors/merging/`
3. Changelog: new version `<debian-version>ubuntu1`, summarizing the
   remaining delta. (In the legacy manual-merge path, also run
   `update-maintainer` from ubuntu-dev-tools so Maintainer: points at
   Ubuntu, keeping `XSBC-Original-Maintainer:`; git-ubuntu handles this
   within its flow.)
4. Build in a PPA and test, then submit a git-ubuntu merge proposal for
   review; without upload rights, sponsors expect the git-ubuntu form —
   a hand-rolled debdiff to `~ubuntu-sponsors` is the fallback, not the
   norm.
5. If the entire delta is obsolete, request a sync instead and state in
   the bug that the delta can be dropped — archive admins can sync over
   delta.

## Freezes and Feature Freeze Exception (FFe)

Timeline per series: DIF (auto-sync stops) → Feature Freeze (new
features/versions need an exception) → Final Freeze → release.
Schedule: the series page on `https://wiki.ubuntu.com/Releases` /
`https://documentation.ubuntu.com/project/release-team/freezes/`.

After Feature Freeze, a new upstream wasmedge needs an **FFe**:

1. Prepare and TEST the updated package first — the release team expects
   build logs and install/upgrade evidence in the request.
2. File a Launchpad bug against the `wasmedge` package, title
   `[FFe] wasmedge <version>`, status New, containing: what changed
   upstream (changelog excerpt), why Ubuntu benefits this cycle, build
   log links, install/test evidence, regression assessment.
3. Subscribe `~ubuntu-release`. A release team member ACKs (status →
   Triaged), then the upload/sync proceeds via the normal sponsorship
   path.
4. **ABI/SONAME breaks always need release team approval** after FF —
   "a new SONAME is a feature" because every reverse dependency must be
   rebuilt. Factor this into release timing for any wasmedge update whose
   Gate 2 analysis shows a SONAME change.
   Reference: `https://documentation.ubuntu.com/project/release-team/freeze-exceptions/`
5. Bug-fix-only upstream microreleases do NOT need an FFe — document
   "bug-fix only" in the sync request/changelog with the upstream diff as
   evidence.

## Ubuntu-side build failure (after sync/merge)

Ubuntu's toolchain differs from Debian's (different GCC/LLVM defaults,
`-proposed` first). A version that built in sid can FTBFS in Ubuntu:

- Build logs: `https://launchpad.net/ubuntu/+source/wasmedge` → the
  failed build link, per architecture.
- Synced/merged uploads land in the development series' `-proposed`
  pocket and must pass Ubuntu's own proposed-migration (britney) —
  excuses at `https://ubuntu-archive-team.ubuntu.com/proposed-migration/update_excuses.html`.
- Fix paths, in order of preference: a no-change rebuild once a toolchain
  issue clears; a fix in Debian followed by re-sync (keeps zero delta);
  an Ubuntu-only patch upload `...ubuntu1` (creates delta — every future
  version then needs a merge; document the delta clearly).

## Released Ubuntu series

### Backports (new feature versions — the normal route for wasmedge)

Eligibility: the new version must already be in a later Ubuntu series
(the development release); targets are LTS series; backports are
opt-in for users and receive NO security-team support — the requester
maintains them.

1. Test-build on the target series:
   `pbuilder-dist <series> build wasmedge_<version>.dsc` (pbuilder-dist
   from `ubuntu-dev-tools`).
2. File the request: `requestbackport wasmedge -d <lts-series>` — creates
   the `[BPO]` Launchpad bug, enumerates intermediate series and reverse
   deps automatically.
3. Attach test evidence, set the bug to **Confirmed**, and **manually
   subscribe `~ubuntu-backporters`** — the tool does not subscribe the
   team, and an unsubscribed [BPO] bug sits unreviewed. Upload goes to
   the series' **backports pocket** (sponsor needed without upload
   rights).
   Reference: `https://documentation.ubuntu.com/project/how-ubuntu-is-made/processes/backports/`

### SRU and security updates (distinct approval paths)

For a specific serious bug in a released series (e.g. a crash or CVE in
the wasmedge version shipped in an LTS):

1. File/repurpose a Launchpad bug with the SRU template:

   ```text
   [ Impact ]        what breaks for users; why fix in the stable series
   [ Test Plan ]     exact steps a stranger can run to verify the fix
   [ Where problems could occur ]  honest regression analysis — must
                                   never be "none"/"low"
   [ Other Info ]    anything a reviewer will ask about
   ```

2. Default to a minimal, regression-tested fix against the released version. Approved microrelease or package-specific SRU exceptions may allow a new upstream release; verify current policy and obtain the required approval rather than assuming an exception. Version it
   `<old-version>ubuntu0.1` (or `+deb..build0.1` style per existing
   version), upload via sponsor to the series' `-proposed`.
3. The SRU team (`~ubuntu-sru`) reviews; once accepted into `-proposed`,
   verify per the Test Plan and set the `verification-done-<series>` tag
   (from `verification-needed-<series>`); after ~7 days aging without
   regressions it is released to `-updates`.
   Reference: `https://documentation.ubuntu.com/project/SRU/`
4. Security vulnerabilities require security coordination, not automatic routing through ordinary SRU because a package is in universe. Check Debian's security tracker and Ubuntu CVE pages, affected versions and current support arrangements. Coordinate the fix, target pocket and disclosure with the appropriate security team under current policy. Minimal backports are the default, not an absolute ban on approved upstream-version updates.
   For embargoed vulnerabilities, do not publish bugs, branches or artifacts. Prepare a private coordination draft for `team@security.debian.org` and/or `security@ubuntu.com` as appropriate; sending even private mail requires user approval. Preserve the embargo and obtain coordinated clearance before any publication.

## Standing monitoring (close the loop)

After each release cycle step, these answer "where is it now?":

- Debian: `https://tracker.debian.org/pkg/wasmedge` (subscribe by email
  for uploads/migrations/bugs)
- Debian excuses: `https://qa.debian.org/excuses.php?package=wasmedge`
- Ubuntu versions: `https://launchpad.net/ubuntu/+source/wasmedge` and
  `+publishinghistory`
- Ubuntu proposed migration: `https://ubuntu-archive-team.ubuntu.com/proposed-migration/`
- Security: Debian security-tracker + `https://ubuntu.com/security/cves?package=wasmedge`
