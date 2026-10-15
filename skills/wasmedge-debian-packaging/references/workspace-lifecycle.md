# Workspace discovery and cleanup UX

This is an assistant-operated preflight, not an automatic deletion feature in the shell helper. Run before clone/import, alongside contributor-onboarding.md. Never treat a request to inspect or prepare as permission to delete prior work.

## Discover and show

1. Resolve the invocation directory, enclosing Git root, installed skill real path and candidate parent directory. The helper's default is a sibling of the enclosing Git repo, or a child of cwd outside Git. That default is only a proposal, not evidence that an existing directory belongs to this run.
2. Confirm the requested series/version. For latest 0.17, select the highest stable 0.17.x tag/release, not the repository-wide latest (possibly 0.18), and exclude alpha/beta/rc. If offline, label latest status unverified. Keep upstream version, prospective Debian version and suite distinct; the final Debian version depends on the verified orig/repack result and canonical packaging state.
3. Inspect bounded known locations: the proposed workdir, relevant sibling packaging directories and previously recorded trial roots. Do not scan the entire home directory. List exact absolute paths, sizes, existence, detected version, Git branch/HEAD, dirty/untracked state, upstream tag ancestry, orig artifacts and handoff where available. Use authoritative Git/changelog/artifact evidence rather than directory names alone. Conflicting or missing evidence means unknown, not disposable.
4. Check relevant named containers for state and bind mounts; do not inspect unrelated credentials or services. If Docker is unavailable, mark container cleanup unverified rather than reporting success.
5. Recommend a new unused workdir for a new candidate, outside the upstream and skill repositories. An explicitly approved existing candidate may be resumed only after helper preconditions and identity checks. Never silently fallback to another version or reuse old artifacts after a failed preparation.

For `status`, show the current state and stop. For `draft`, show one short plan before mutation, for example (values are illustrative):

```text
Invocation: /work/WasmEdge
Upstream target: 0.17.2 (stable 0.17 series; checked <time/source>)
Debian target: 0.17.2-1 provisional, unstable preparation / UNRELEASED
Canonical packaging base: <commit>
New workdir: /work/wasmedge-debian-contribution-0.17.2-<run-id>
Will create: packaging clone/branch, orig/pristine-tar data, changelog,
             HANDOFF and selected build artifacts
Existing work: <absolute path> — <version/status/size>
Preserve: upstream repo, skill repo, previous submission and evidence
External actions: none
```

Do not promise a fixed disk/time cost. Distinguish environment downloads from preparation, compilation and tests; state architecture and emulation. Reuse trusted toolchain caches where appropriate, never stale candidate output.

## One human choice, not repeated prompts

Group this with the identity questionnaire (at most four questions total). An unused isolated workspace is an announced default, not a question. Ask only for destructive cleanup, an explicit resume request with unresolved state, or a material location conflict; never require a fresh-workspace choice merely because none was previously selected:

- New isolated run (Recommended): use the displayed unused path; keep old work.
- Resume existing candidate: show exact path/version/state; disable this option when prerequisites are unresolved.
- Clean selected trial then start fresh: show exact deletion and retention lists. If those lists are not yet known, selection authorizes only inventory, NOT deletion; ask once more with the concrete plan.

Use the human-only route described in contributor-onboarding.md, including Pi responseMode:user where auto-reply is enabled. Cancellation pauses mutations. Do not ask the user to type shell paths unless overriding the proposal. Recheck scope for symlinks, ownership or state changes before applying prior consent.

## Safe cleanup

- Separate cleaning generated object trees, removing a disposable trial, and deleting a Git repository/history. They require different scopes; an old name or a matching prefix is not authorization.
- Present exact canonical paths, estimated reclaimable bytes, named containers, retained report/log/patch/reproducer paths, and any unique artifacts or dirty Git work. Material findings change the plan and require review.
- Resolve symlinks and mount destinations. Reject root/home, upstream/skill repos, overlapping retained paths and unrelated directories. Unknown provenance or unexpected contents means stop. A local run record aids discovery, never grants deletion authority.
- Never reset/delete a dirty or unique contribution history just to make the helper run. Archive approved evidence first and verify it is readable. Do not assume old v1/v2/v3 trials are safe merely because a past summary calls them failed.
- Check active processes/containers referencing the target. Obtain scoped permission to stop them before cleanup. Remove only approved named resources; never use broad docker system prune or a wildcard rm over sibling directories.
- Check every operation's exit code. If file cleanup succeeds but Docker is unavailable, report partial cleanup. Do not hide errors with `|| true` and announce completion.
- Verify paths/resources removed and retained evidence intact; report measured space after cleanup. A container's storage and a host bind directory are separate usage, not interchangeable estimates.

## Local run record and finish

Keep a small run record OUTSIDE the packaging Git tree to avoid dirtying it: run ID, purpose, exact source/base refs, resolved workdir and skill path, approved identity/scope reference (no tokens), architecture, container name/mounts, stage/exit, artifact paths and retention plan. This is assistant bookkeeping, not required reviewer reading. Explicit --workdir should match the displayed plan.

At completion show: target actually prepared, exact path, tests/warnings, publication state and retained size. Keep concise reports and selected evidence; offer cleanup of bulky generated files rather than retaining repeated full environments indefinitely. Cleanup remains separately scoped. Neither the record nor preparation authorizes public submission.

## Acceptance scenarios

- Invoked from upstream repo: propose a sibling, never nest a packaging clone in upstream.
- Invoked elsewhere: show cwd-based default; do not assume it is the upstream repo.
- Existing 0.17.0-named directory actually contains 0.17.1: report observed version, do not delete/reuse by name.
- Existing dirty or mismatched candidate: offer new workdir, not forced reset.
- Latest 0.17 request with a newer 0.18 release: keep series constraint.
- Docker unavailable during cleanup: local and container results reported separately.
- Symlink points outside approved scope: stop before deleting.
- Failed helper: preserve stage/exit and stop; no build against stale baseline.
- Identity and path already approved for same run: verify and continue without repeated questionnaire.
