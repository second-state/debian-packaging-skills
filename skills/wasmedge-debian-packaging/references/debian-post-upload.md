# Debian: After the Upload

Track unstable acceptance, testing migration and reverse-dependency health separately. Ubuntu may sync from unstable before Debian testing migration; evaluate known regressions rather than imposing an unconditional migration prerequisite.

Every email, bug, comment, upload and external submission below requires explicit user approval under [../SKILL.md](../SKILL.md#publication-permission).

## Stage map

```
upload → dak checks → (NEW queue?) → ACCEPTED into unstable
       → britney evaluates daily → migrates to testing
       → reverse deps (crun) rebuilt/working
```

## dak: ACCEPTED, NEW, or REJECT

- Normal case: the upload is auto-accepted within minutes and an ACCEPTED
  mail goes to the uploader; the package appears in unstable on the next
  dinstall run (~4x daily).
- **NEW queue**: triggered whenever the upload introduces a binary package
  name the archive has not seen — which is exactly what a library rename
  (`libwasmedge0` → `libwasmedge1` on a SONAME bump) does. NEW means
  manual ftp-master review: days to weeks, no SLA. Status:
  `https://ftp-master.debian.org/new.html`. Plan for this latency whenever
  the ABI analysis concludes a package rename.
- **REJECT**: dak mails the reason (signature, copyright,
  override mismatch...). REJECTs are normal, not fatal: read the mail, fix,
  bump the changelog, re-upload via the sponsor.

## Testing migration (britney)

Ubuntu auto-sync pulls from unstable, but Debian's own health signal — and
the stable-release path — is migration to testing. Monitor it; a package
that cannot migrate usually indicates a problem Ubuntu will inherit.

- Where: the package page on `https://tracker.debian.org/pkg/wasmedge`
  shows "testing migrations" status; detailed excuses at
  `https://qa.debian.org/excuses.php?package=wasmedge` and
  `https://release.debian.org/britney/update_excuses.html`.
- Normal aging: `urgency=medium` waits 5 days, `low` 10, `high` 2.
- What blocks migration:
  - new RC bugs against the package
  - build failure on any release architecture (check
    `https://buildd.debian.org/status/package.php?p=wasmedge`)
  - **autopkgtest regressions — including in reverse dependencies.**
    britney runs the test suites of packages that depend on
    libwasmedge0 (e.g. crun) against the NEW library. An ABI or
    behavior change that breaks crun's tests holds wasmedge in unstable
    indefinitely. This is the direct consequence of the ABI changes the
    Gate 2 analysis flags — check crun's autopkgtest result in the
    excuses page in the first days after acceptance.
- If stuck on a reverse-dep regression: inspect the migration CI log and reproduce with the actual candidate library, architecture, test version and dependency environment. A generic sid autopkgtest run may test different packages and is not equivalent evidence. Then either fix wasmedge (restore compatibility), or
  coordinate a fixed crun upload with its maintainer, or — if the
  regression is in the test not the code — file a bug against crun asking
  for a test update and reference it in the excuses (the release team can
  force-badtest only with justification).

## binNMU: rebuilding reverse dependencies

When the library package is renamed (SONAME bump) or rdeps merely need a
rebuild against the new version, the rebuild is a **binNMU**, scheduled by
the Debian release team (wanna-build access).

- Often automatic: for ordinary library transitions the release team
  auto-schedules binNMUs of reverse deps. Check
  `https://release.debian.org/transitions/` before requesting anything.
- Manual request: file a bug against the `release.debian.org`
  pseudo-package with usertag `binnmu` (reportbug automates this):

  ```text
  To: submit@bugs.debian.org
  Subject: nmu: crun_<version>
  Package: release.debian.org
  User: release.debian.org@packages.debian.org
  Usertags: binnmu
  Severity: normal

  nmu crun_<version> . ANY . -m "Rebuild against libwasmedge1"
  ```

  `ANY` expands to all architectures except `all`. Reference:
  `https://release.debian.org/wanna-build.html`, `https://wiki.debian.org/binNMU`.
- Not a binNMU: failed builds are "give-back" (`gb`) requests to
  `debian-wb-team@lists.debian.org`, not binNMUs.

## Maintainer communication and exceptional escalation

Silence is not permission to replace the maintainer's release plan. Check recent team activity, existing proposals and stated blockers first. With user approval, send a concise follow-up offering help through the established channel; avoid duplicate requests.

Coordinate sponsorship with the maintainer/team. A sponsor supplies review and upload authority, not automatic permission to bypass maintenance decisions. See https://mentors.debian.net/sponsors/.

NMUs, salvaging and MIA procedures are distinct exceptional processes, not timer-triggered steps for a new upstream release. Before proposing one, verify current Developer's Reference guidance, package/team policy, urgency, scope, notifications and waiting requirements with an appropriate Debian developer. Broad new-upstream NMUs need particular justification. A paper trail provides evidence, not authorization. Do not execute any escalation without explicit user approval.

References: https://www.debian.org/doc/manuals/developers-reference/pkgs.en.html and https://wiki.debian.org/PackageSalvaging.

## Exit criterion for this stage

Report milestones independently:
- Unstable acceptance: archive confirms the exact version.
- Testing migration: the target actually migrated; merely aging means pending.
- Reverse-dependency health: record actual installability and test results, including gaps.

Ubuntu work may proceed from unstable acceptance after reviewing risks and the target series' policy; it need not wait for testing migration. Continue monitoring Debian health alongside [ubuntu-path.md](ubuntu-path.md).
