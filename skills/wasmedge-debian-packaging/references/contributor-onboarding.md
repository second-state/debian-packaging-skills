# Contributor onboarding

Run this before any preparation that creates commits or changelog entries. The assistant gathers facts and sets invocation-local variables; the contributor should not need to know Debian environment-variable names. The shell helper remains non-interactive.

## 1. Inspect existing decisions first

Read the owner's actual prior answers for this task. Reuse an explicit identity and scope if still applicable; do not ask again just because a process or agent changed. A past commit, profile, assistant statement or tool receipt is not consent. Report the missing decision or actual conflict before asking.

When the harness provides original-answer context, inspect it before asking for repeated consent. Do not treat discovery, a model-delegated answer, a GitHub login or maintainer encouragement as fresh authorization. Cancelled or unanswered questionnaires leave preparation paused, without choosing a default identity.

Before collecting identity, apply [workspace-lifecycle.md](workspace-lifecycle.md): resolve the actual target repo/workdir and inspect existing runs. Show the target version and exact create/resume/cleanup paths in the same preflight. Group any missing workspace decision with the human identity questions; do not silently delete old runs.

## 2. Detect candidates (read-only)

Inspect only the relevant fields; never print tokens, credential stores, all environment variables or complete Git configuration.

- GitHub, if gh is available and authenticated: `gh api user --jq '{login, name, email}'`. This reads the active account's profile, not private email lists. If unavailable, say so and continue with local candidates; do not log in, switch accounts, expand scopes or change credentials.
- Git identity in the target packaging repository, if it exists: `git -C <repo> var GIT_AUTHOR_IDENT` and `git -C <repo> var GIT_COMMITTER_IDENT`. These include environment overrides. Label the exact repository/source; if it does not exist yet, label detected caller-directory identity as provisional and recheck in the actual clone.
- Debian identity: read only DEBFULLNAME and DEBEMAIL.
- Resumed candidate: inspect the newest debian/changelog signature and relevant local preparation commits for test identities or mismatches. Do not infer the contributor identity from debian/control Maintainer or old historical entries.

Display name/email only in the local conversation. A GitHub handle is not a Git author name, a public profile email may be null, and GitHub authentication does not establish Salsa authentication or Debian upload authority. Never guess an email from a handle or silently select a private address.

If author, committer, Debian or GitHub identities differ, show that difference briefly. Different platform accounts can be legitimate; do not require all usernames to match. For a new contribution normally use one owner-approved name/email for newly created Git records and changelog, unless the owner explicitly requests distinct attribution.

## 3. Ask one compact human questionnaire

Use the user's conversation language. Group only genuinely missing decisions into one questionnaire, normally one or two questions. Select routine technical defaults from existing package conventions rather than asking the contributor to design a build system.

First show a short preview:

```text
Target: <package/version and suite>; local preparation only
GitHub account: <login, or unavailable>
Git author: <name/email, source>
Git committer: <same, or differing name/email>
Debian changelog: <name/email, or unset>
Your name/email will be visible if the commits or changelog are later published.
Nothing will be pushed, sent or uploaded by this confirmation.
```

If run purpose is unknown, ask: "What should this run prepare?"
- Submission draft: real contributor identity, local reviewable package and text; no publication.
- Local validation only: explicit test identity, not submission-ready.

Ask: "Which contributor identity should this run use?"
- Use detected Git identity: show the exact name/email and intended author/committer/changelog scope. Recommend only if complete and consistent with run purpose.
- Use detected Debian identity: include only when complete and distinct from the Git candidate.
- Specify another identity: ask the user to supply a name and email; selecting this alone is not a complete answer.
- Local test identity: Local Validation <validation@example.invalid>; label the run test-only. This choice does not satisfy a request for a real submission draft without resolving that conflict.

Adapt to 2–4 meaningful choices; omit missing/duplicate candidates. If no real identity is available, offer Specify another identity and Local test identity. A GitHub public profile can be offered as a candidate when both name and email exist, but never equate it with verified Git/Salsa authority. Users may also type a custom answer. Do not put secrets or unverifiable defaults in an option.

The core skill is harness-neutral: identity and new scope/authorization questions must be answered by the owner through the host's human-input mechanism. A host adapter may map this to a questionnaire, form or ordinary conversation, but it must not delegate the decision to a model or infer consent from login state. On another harness, use its documented human-input path; if unavailable, ask in ordinary conversation and wait for the owner's reply. Do not create a new extension solely for this interaction. Do not reinterpret an existing human answer as permission to publish.

## 4. Apply only to this invocation

Validate that the chosen name/email are non-empty single-line strings. Treat answers as data: pass environment values through a subprocess environment map or safely quoted variables, never interpolate them as executable shell code. Avoid shell history or logs containing unnecessary identity details.

For a new preparation, set these invocation-local values from the approved identity:

```text
DEBFULLNAME / DEBEMAIL
GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL
GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL
```

Do not change host global Git configuration. Pass the same approved values into the isolated container, and verify git var inside the actual preparation repo before import. Repository-local config must not silently override the agreed identity. Preserve upstream/historical authors and debian/control Maintainer.

When resuming, changing environment values does not rewrite existing commits or a changelog already at the target version. Surface mismatches first. Do not amend/rebase or relabel existing test work as a real contribution without scoped permission; offer fresh preparation if appropriate.

Keep a minimal local run note: target repo/version, purpose, approved identity, source of owner confirmation and local actions authorized. No tokens. The note documents the decision; it is not a portable authorization token or blanket consent for another project.

## 5. Verify and return a contributor-sized result

After preparation inspect the newly created Git author/committer and top changelog signature against the approved identity. Check version, branch and handoff. On mismatch stop and explain; do not silently correct historical records.

Report only: what was prepared, important test results/warnings, remaining decisions, location of the draft, and that nothing was published. Keep JSON and detailed evidence internal. If a public action is requested later, separately show the destination, acting account and exact draft/diff, and apply the existing publication-approval rule.

## UX acceptance scenarios

1. Matching Git/Debian identity and a known submission target: ask one identity confirmation, not repeated version or scope questions.
2. GitHub profile email is absent: offer complete Git identity or custom input, never guess an address.
3. Git/Debian identities differ: show both; no silent preference.
4. No gh or offline: local preparation can proceed with owner-confirmed identity; live-state checks remain unverified.
5. Questionnaire cancelled: no import, commits or changelog mutations.
6. Custom option selected without values: request the missing name/email only.
7. Same-task resume with valid prior answer: do not re-ask; recheck actual identity and candidate state.
8. Resumed Local Validation commits with a real contributor request: stop for a migration/fresh-preparation decision; no silent attribution rewrite.
9. Identity approved: no push, email, MR or upload is authorized by that answer.
10. Two repositories or changed GitHub account: review applicability of prior scope; confirm the actual acting account before any separately authorized publication.
