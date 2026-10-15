# Maintainer-ready local preparation

Follow [command-contract.md](command-contract.md): default invocation targets ready-for-review, not helper-only completion. The assistant owns all routine stages; do not make the user repeatedly ask for unfinished local work. The optional finalizer is a consistency aid, not the workflow driver or proof of readiness.

## Ask before execution

Use [contributor-onboarding.md](contributor-onboarding.md) for read-only identity detection, the human questionnaire and invocation-local setup. The assistant gathers and applies settings; the contributor selects an identity, not environment-variable syntax. Read prior scoped answers before asking again.

Group missing decisions only when needed: exact version/suite/base; approved public contributor identity versus local test identity; material resource costs; destructive cleanup; or a substantive packaging choice. A `draft` request already authorizes ordinary local preparation, new local commits and standard validation in the announced isolated workspace. Do not repeatedly ask for already-scoped permission. Submission preparation is NOT consent to push, email, upload or publish.

Verify Debian identity (DEBFULLNAME/DEBEMAIL) and Git author/committer independently. Never infer Git identity from dch settings or modify host global configuration. A test identity must not silently become a real submission identity. Preserve debian/control Maintainer and historical changelog authors.

## Contributor experience and public writing

The assistant does the evidence gathering and drafts the contribution; the contributor supplies intent, identity, substantive decisions and approval. Do not ask the contributor to fill in JSON, compute hashes or repeat facts already available. Choose routine technical defaults from the package's existing conventions and explain only material trade-offs.

Public issues, MR descriptions, email drafts, commit messages and changelog entries are English unless the project requires otherwise. Follow the current project template, including required fields. Write like a contributor explaining a concrete patch: what changed, why it matters, how it was tested, and what remains uncertain. Use specific commands/results, short sentences and logical bullets. Avoid promotional claims, repeated summaries, boilerplate gratitude, unnecessary headings, emoji status tables and phrases such as 'comprehensive robust enhancement'. Concision must not remove reproducible steps, relevant warnings or required template information.

Do not invent authorship, first-hand experience, test results or maintainer preferences. Natural writing does not mean hiding assistance: retain required Assisted-by/co-author/disclosure conventions and human approval. Never sign on behalf of another person.

Default handoff: a focused diff, concise changelog, short test summary and only unresolved decisions the maintainer actually needs to make. Keep internal matrices, hashes, failed-attempt diaries and full logs local; provide selected evidence through approved channels if requested or needed to reproduce a failure. A packaging MR need not contain the full upstream changelog, all historical discussion, or unrelated Ubuntu plans.

Group changelog entries by logical change, not by file. Several files may share one accurate entry. Record meaningful packaging changes; do not add noisy entries for unchanged metadata or mechanically enumerate every edited line. Respect a team's documented changelog-at-merge convention rather than inventing a universal per-commit requirement.

## Work expected before review

- Compare against the current canonical maintainer baseline, not an old contribution branch. Record its commit and inspect existing MRs before any submission.
- Audit renamed/deleted AND added files against copyright Files patterns, licenses, attribution and exclusions. No-match does not prove removal. Do not increment years without source evidence.
- Review Debian bugs and fixed upstream commits; use Closes only for verified fixes. In offline mode record this as not checked; do not invent historical bug availability or closure.
- Preserve watch stable/prerelease policy, repack decisions, rules conventions, package relationships and symbols unless the release requires a justified change.
- Assess applicable Policy changes before changing Standards-Version. A newer Policy version is not by itself a mandatory bump.
- Reconcile EACH substantive Debian diff with the top changelog entry after changes. dch creates the skeleton; it does not inspect the diff or upstream notes. Do not rewrite older entries or claim unchanged symbols were refreshed.
- Inspect actual shipped headers/libraries/components and old-consumer behavior. A passing symbol-name list alone is not ABI evidence.
- Validate the final candidate and record exact version, architecture, source identity, commands, exit codes and skips. A regenerated file or new patch invalidates prior applicable evidence.

## Lessons from 0.17.1 (not universal hardcoded rules)

The submitted c0d339b symbols file is identical to maintainer release 8336e3f. The actionable metadata omission was the Android wrapper path relocation and year review. The maintainer also selected stable-only watch, updated Policy and reorganized VERSION generation. Preserve those decisions in subsequent preparation; do not require every project to use those exact versions/styles. The GCC16 Closes entry calls for bug triage, not automatically adding a new patch. UNRELEASED-to-unstable and release signature are uploader actions, not omissions the contributor must preempt. Closed without merge does not establish rejection of technical content.

## Optional internal consistency record

A final diff/changelog/evidence review is required; this particular JSON tool is not a Debian requirement or a required attachment. Use it when it helps prevent stale evidence. The assistant prepares the JSON from inspected facts; do not delegate bookkeeping to the contributor or maintainer. A documented manual review can serve the same purpose without this tool.

After edits, stage reviewed new Debian files if needed (do not commit unless authorized). If using the finalizer, save a review JSON outside the candidate repository, then run:

```sh
python3 scripts/finalize-debian-handoff.py --repo <candidate> \
  --base <canonical-commit> --review <review.json> --output <new-report.json>
```

Multiple changed files may reference the same logical changelog entry. The finalizer does not edit the candidate, overwrite preparation HANDOFF.md, run tests or publish. It checks consistency, not truth of reviewer assertions. INCOMPLETE is an expected result for test-only drafts. Never fill in pass just to obtain exit 0.

Review JSON shape:

```json
{
  "base": "<full base commit>",
  "head": "<full candidate HEAD>",
  "diff_sha256": "<sha256 of git diff --binary BASE -- debian/>",
  "changes": {
    "debian/tests/basic": {
      "reason": "Native artifacts now require explicit AOT mode",
      "changelog_entry": "Update native shared-library tests to use explicit AOT mode."
    }
  },
  "checks": {
    "identity": {"status": "not-tested", "evidence": "Public identity not confirmed"},
    "copyright_paths": {"status": "not-tested", "evidence": "Pending source audit"},
    "source_repack": {"status": "not-tested", "evidence": "Pending archive verification"},
    "bugs": {"status": "not-tested", "evidence": "Pending BTS review"},
    "policy_watch": {"status": "not-tested", "evidence": "Pending baseline comparison"},
    "abi": {"status": "not-tested", "evidence": "Pending ELF/consumer tests"},
    "tests": {"status": "not-tested", "evidence": "Pending candidate build"},
    "freshness": {"status": "not-tested", "evidence": "Pending final canonical/archive check"}
  },
  "artifacts": [{"path": "build.log", "sha256": "<actual digest>"}]
}
```

Use statuses pass, not-applicable (with justification), blocked, or not-tested. Log hashes protect evidence identity, not its interpretation; review failures and warnings. The Debian diff binding does not replace verification of full upstream tree/archive/build inputs. Keep preparation, validation results and publication approval distinct.

## Test levels and cleanup

Every helper change: syntax + offline contracts. Import/identity/branch changes: real clean preparation with explicit local identity. Build/symbol/test changes: affected real build/test gates, including previous negative cases. Documentation-only changes: references and decision-scenario review. Do not claim a stubbed sbuild test proves real sbuild integration.

Keep a single timestamped active run with stage/exit records. Fail immediately if prepare fails; verify package version/architecture before linting. Preserve small logs, review, patches, hashes and needed candidate artifacts; remove only approved disposable containers/objects. Never hide lintian failure with `|| true` and a fabricated zero status.
