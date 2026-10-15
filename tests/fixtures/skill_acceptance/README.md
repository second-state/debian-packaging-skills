# Scripted offline slash-workflow acceptance fixture

This miniature Python CLI is **not WasmEdge**. Version 1.1 switches from a
positional name to `--name`, so Debian's executable smoke test must change.
The baseline contains a historical changelog and maintainer-owned metadata.
`driver.py` performs real preparation, semantic reconciliation, Git commits,
build/runtime checks and an audited local handoff in a temporary directory.
Only fixture repositories are committed; the project repository is untouched.

The harness preloads a known version and confirmed **fictional test identity**;
no user supplies technical plans or additional answers. Submission approval is
also explicitly fictional and confined to an injected no-network transport.
The actual runner and adapter execute, but this is scripted acceptance of the
workflow, not a guarantee that an LLM will make the same decisions unattended.
No real Debian build, lintian, live archive/bug lookup, credentials, server
permissions, archive acceptance or real publication is tested.

## Verified UX contract

Run `python3 -B -m unittest discover -s tests -p 'test_skill_acceptance.py' -v`.
The five scenarios cover ready-for-review preparation and exact mocked submission,
failed functional validation, unsupported changelog/history changes, live candidate
drift and changed evidence. Default preview and denied approval cause no transport
effects. Exact fixture consent allows one mocked push/create; unchanged retry returns
the existing MR without further effects. All Git repositories are disposable local
fixtures; no actual contribution or network destination is modified.
