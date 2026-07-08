# <PACKAGE> — package-specific facts to fill in

Everything else in the Debian-to-Ubuntu flow is generic and lives in the
`wasmedge-debian-packaging` skill as the worked example. Only the facts below
change per package. Fill each in, then delete this notice.

| Fact | Where it is used | Value for <PACKAGE> |
|---|---|---|
| Salsa packaging repo | `debian/watch`, clone URL, prepare `--repo` | `https://salsa.debian.org/<team-or-maint>/<package>` |
| Source package name | `debian/control`, `debian/changelog` | `<package>` |
| Library binary package + SONAME | `debian/control`; rename only if SONAME bumps | `lib<name><N>` |
| Symbols file | `debian/lib<name><N>.symbols` | `debian/lib<name><N>.symbols` |
| Upstream version macro(s) | detect file version vs SONAME | e.g. `FOO_VERSION` / `FOO_SOVERSION` |
| Symbol version nodes (if versioned) | `.symbols` minver, ABI tracking | e.g. `FOO_1.0` |
| dfsg exclusions | `debian/copyright` `Files-Excluded`, `debian/watch` `Repacksuffix` | list non-free paths, or "none" |
| Reverse dependencies to check | `apt-cache rdepends lib<name><N>` before ABI changes | ... |
| BTS bug number | `changelog` `Closes:`, MR wiring | `#NNNNNNN` |
| Ubuntu package name (if different) | `requestsync` / Launchpad sync bug | `<package>` |

## ABI / SONAME decision (same rule as wasmedge)
Rename the library binary package (e.g. `lib<name>0` -> `lib<name>1`) if and
only if the SONAME changed. If the SONAME is kept but symbols were
removed/changed, absorb the break with ELF symbol versioning or a SONAME bump;
name both options in the maintainer handoff and let upstream/maintainer choose.
Regenerate `debian/lib<name><N>.symbols` from the `dpkg-gensymbols` diff.
