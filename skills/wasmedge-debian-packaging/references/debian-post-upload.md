# Debian: After the Upload

What happens between "sponsor uploaded the package" and "Ubuntu can sync
it", and what to do at each stage when it stalls. Acceptance into unstable
is NOT the finish line: the package must also migrate to testing, and
reverse dependencies must keep working.

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
- If stuck on a reverse-dep regression: reproduce locally
  (`autopkgtest crun -- schroot sid`, which needs a pre-built sid schroot
  from `mk-sbuild`/`sbuild-createchroot`; otherwise read the CI log
  linked from the excuses page), then either fix wasmedge (restore
  compatibility), or
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

## Maintainer unresponsive: escalation ladder

The handoff's expected blocker is maintainer/sponsor action. If nothing
happens, escalate in this order — each step is legitimate and documented;
skipping steps is considered hostile (package hijacking).

1. **~2 weeks**: ping the BTS bug (mail `<bugno>@bugs.debian.org`) asking
   if help is wanted; offer the prepared branch/patches again.
2. **~4 weeks**: seek a sponsor independently of the maintainer — file an
   RFS bug against the `sponsorship-requests` pseudo-package
   (`Subject: RFS: wasmedge/<debian-version> -- <one-line summary>`,
   guidance at `https://mentors.debian.net/sponsors/`), and/or upload the
   package to `mentors.debian.net` and ask on the `debian-mentors` list.
3. **NMU** (needs a DD to perform it): a non-maintainer upload through the
   DELAYED queue. Conventions (devref 5.11): announce intent in the BTS,
   attach the patch (`nmudiff`), use DELAYED/15 for non-RC changes (2–5
   days for RC bugs), version the upload `<upstream>-<rev>.1` (e.g.
   `0.17.0-0.1` for a new-upstream NMU). Check the maintainer's stance on
   `https://wiki.debian.org/LowThresholdNmu` first.
4. **Package salvaging** (takes over maintainership of this one package):
   allowed when e.g. no visible maintainer activity for 6 months, or an
   unacknowledged NMU has sat for a month — full criteria at
   `https://wiki.debian.org/PackageSalvaging`. Procedure (devref ch. 5):
   file an ITS (Intent to Salvage) bug with all maintainers/uploaders in
   `X-Debbugs-Cc` (add `mia@qa.debian.org` too if the maintainer looks
   inactive), wait the **21-day objection window**, then upload with
   yourself as maintainer via **DELAYED/7 or longer** — not directly.
5. **MIA team** (questions the maintainer's overall activity): write to
   `mia@qa.debian.org` with the evidence trail. Slowest, affects more
   than one package; last resort.

Record every step in the BTS bug — the paper trail is what authorizes the
later steps.

## Exit criterion for this stage

Declare the Debian side done only when BOTH hold:
- the target version is in **testing** (or the excuses page shows it
  merely aging, with no blocking regressions), and
- reverse dependencies (crun) are installable and passing autopkgtest
  against the new version.

Then move to the Ubuntu side: see [ubuntu-path.md](ubuntu-path.md).
