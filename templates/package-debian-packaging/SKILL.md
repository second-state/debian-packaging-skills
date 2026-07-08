---
name: PACKAGE-debian-packaging
description: TEMPLATE, not a live skill. Copy this directory to skills/<package>-debian-packaging/ and replace the package-specific facts to onboard a new package to the Debian-to-Ubuntu release flow. Do not invoke directly.
metadata:
  short-description: Skeleton for a per-package Debian-to-Ubuntu skill
---

# <PACKAGE> Debian Packaging (TEMPLATE)

Starting skeleton for onboarding a new package to the Debian-to-Ubuntu
release flow. The *method* is identical for every package; only a handful
of package-specific facts change (see
[references/package-facts.md](references/package-facts.md)).

## How to use this template
1. Copy this directory to `skills/<package>-debian-packaging/`.
2. Set `name:` and the title to the real package; delete the TEMPLATE markers.
3. Replace every `<PACKAGE>` placeholder and fill in
   [references/package-facts.md](references/package-facts.md).
4. For the generic Debian mechanics — gbp three-branch layout, +dfsg repack,
   the symbols/shlibs gate, Salsa fork/push/MR, Ubuntu sync/merge/backport/SRU,
   and archive authority boundaries — the `wasmedge-debian-packaging` skill is
   the worked reference implementation. Read its `references/` and adapt.
5. The prepare helper is already generic: reuse
   `wasmedge-debian-packaging/scripts/prepare-wasmedge-debian-update.sh`
   with `--repo <salsa-url>`, or copy it under a package-specific name.
6. Delete this "How to use" section once filled in.

## Scope (keep, adjust wording)
Upstream maintainers usually cannot directly update Ubuntu archive packages.
The official route is: update the Debian package first, get it accepted by a
Debian Developer/Maintainer or sponsor, then let Ubuntu auto-sync or request a
manual sync/merge into the development release. Released Ubuntu series usually
require backports or SRU, not a normal feature-version update. An AI agent may
coordinate the handoff only if it respects these authority boundaries and
produces reviewable artifacts instead of assuming upload rights.
