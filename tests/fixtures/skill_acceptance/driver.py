#!/usr/bin/env python3
"""Concrete fixture driver; semantic judgments here are specific to this tiny CLI.

This is deliberately not an installed universal packaging driver or an LLM test.
All writes and commits occur in the disposable cwd supplied by the test harness.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipapp

ROOT = Path.cwd()
REPO = ROOT / "candidate"
INPUT = ROOT / "inputs"
CHANGE = "Update the smoke test to use the required --name option."
EXPECTED = {"src/greet.py", "debian/changelog", "debian/tests/basic"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")


def load(name):
    return json.loads((ROOT / name).read_text())


def require(value, message):
    if not value:
        raise ValueError(message)


def config():
    data = load("intent.json")
    require(data["identity"]["confirmed"] is True, "fixture identity not confirmed")
    require(data["version"] == "1.1-1", "unexpected fixture target")
    return data


def git(*args):
    identity = config()["identity"]
    env = dict(os.environ, GIT_AUTHOR_NAME=identity["name"],
               GIT_COMMITTER_NAME=identity["name"], GIT_AUTHOR_EMAIL=identity["email"],
               GIT_COMMITTER_EMAIL=identity["email"])
    return subprocess.check_output(["git", "-C", str(REPO), *args], env=env, text=True).strip()


def candidate():
    return {"head": git("rev-parse", "HEAD"), "base": load("prepare.json")["base"],
            "tree": git("rev-parse", "HEAD^{tree}")}


def prepare():
    data = config()
    require(not REPO.exists(), "never overwrite an existing candidate")
    shutil.copytree(INPUT / "baseline", REPO)
    (REPO / "debian/tests/basic").chmod(0o755)
    git("init", "-q")
    git("checkout", "-qb", "debian/latest")
    git("add", ".")
    git("commit", "-qm", "Fixture canonical maintainer baseline")
    base = git("rev-parse", "HEAD")
    old_test = subprocess.run([str(REPO / "debian/tests/basic")], cwd=REPO,
                              capture_output=True, text=True, stdin=subprocess.DEVNULL)
    require(old_test.returncode == 0, "baseline functional test did not pass")
    git("checkout", "-qb", "debian/fixture-1.1")
    shutil.copyfile(INPUT / "upstream/greet.py", REPO / "src/greet.py")
    changelog = REPO / "debian/changelog"
    identity = data["identity"]
    changelog.write_text(
        "fixture-greeter (1.1-1) UNRELEASED; urgency=medium\n\n"
        "  * New upstream release.\n\n"
        f" -- {identity['name']} <{identity['email']}>  Tue, 02 Jan 2024 00:00:00 +0000\n\n"
        + changelog.read_text())
    incompatible = subprocess.run([str(REPO / "debian/tests/basic")], cwd=REPO,
                                  capture_output=True, text=True, stdin=subprocess.DEVNULL)
    (ROOT / "old-consumer.log").write_text(incompatible.stdout + incompatible.stderr)
    require(incompatible.returncode != 0 and "--name" in incompatible.stderr,
            "expected an observed old-consumer failure after the upstream change")
    save("prepare.json", {"base": base, "version": data["version"], "identity": identity,
                          "baseline_test_exit": old_test.returncode,
                          "old_consumer_exit": incompatible.returncode,
                          "baseline_changelog_sha256": sha(INPUT / "baseline/debian/changelog")})
    print("Imported 1.1; baseline consumer really fails: --name is now required")


def inspect():
    base = load("prepare.json")["base"]
    changes = set(git("diff", "--name-only", base).splitlines())
    require(changes == EXPECTED, "unexpected candidate diff: " + repr(changes))
    old = subprocess.check_output(["git", "-C", str(REPO), "show", base + ":debian/changelog"], text=True)
    changelog = (REPO / "debian/changelog").read_text()
    require(changelog.endswith(old), "historical changelog was rewritten")
    top = changelog[:-len(old)]
    identity = config()["identity"]
    require(top.startswith("fixture-greeter (1.1-1) UNRELEASED;"), "wrong version/suite")
    require(f" -- {identity['name']} <{identity['email']}>" in top, "wrong changelog author")
    allowed = {"  * New upstream release.", "  * " + CHANGE}
    require(all(line in allowed for line in top.splitlines() if line.startswith("  *")),
            "unsupported changelog claim")
    source = (REPO / "src/greet.py").read_text()
    require('parser.add_argument("--name", required=True)' in source, "unreviewed CLI contract")
    test = (REPO / "debian/tests/basic").read_text()
    require(test == (INPUT / "packaging/basic").read_text(), "unreviewed packaging test")
    # Unchanged paths are checked byte-for-byte, not assumed from a checklist.
    preserved = {}
    for name in ["control", "watch", "copyright", "install", "tests/control"]:
        path = "debian/" + name
        require((REPO / path).read_bytes() == (INPUT / "baseline" / path).read_bytes(),
                "maintainer metadata changed: " + path)
        preserved[path] = sha(REPO / path)
    return {"changed_paths": sorted(changes), "preserved": preserved,
            "historical_changelog_sha256": hashlib.sha256(old.encode()).hexdigest(),
            "missing_changelog_entries": [] if "  * " + CHANGE in top.splitlines() else [CHANGE]}


def review():
    shutil.copyfile(INPUT / "packaging/basic", REPO / "debian/tests/basic")
    (REPO / "debian/tests/basic").chmod(0o755)
    before = inspect()
    require(before["missing_changelog_entries"] == [CHANGE], "expected missing packaging explanation")
    changelog = REPO / "debian/changelog"
    changelog.write_text(changelog.read_text().replace("  * New upstream release.\n",
                         "  * New upstream release.\n  * " + CHANGE + "\n", 1))
    after = inspect()
    require(not after["missing_changelog_entries"], "unreconciled changelog")
    git("add", "src/greet.py", "debian/changelog", "debian/tests/basic")
    git("commit", "-qm", "Import fixture 1.1 and adapt CLI smoke test")
    data = config()["identity"]
    author = git("show", "-s", "--format=%an <%ae>|%cn <%ce>", "HEAD")
    expected = f"{data['name']} <{data['email']}>"
    require(author == expected + "|" + expected, "Git author/committer mismatch")
    patch = subprocess.check_output(["git", "-C", str(REPO), "diff", "--binary", candidate()["base"], "HEAD"])
    (ROOT / "candidate.diff").write_bytes(patch)
    save("review.json", dict(candidate(), before=before, after=after, author=author,
         rationale="Upstream requires --name; observed old consumer failure requires a Debian smoke-test change.",
         scope={"abi": "Not applicable: Python CLI, no shared library.",
                "licensing": "No added/deleted source paths; fixture copyright coverage retained.",
                "bugs_and_archives": "Offline: not queried; no Closes or current archive claims.",
                "policy_watch": "Retained maintainer baseline without speculative bumps."}))
    print("Found and repaired missing changelog explanation; preserved historical entries and maintainer metadata")


def validate():
    require(not git("status", "--porcelain"), "validation requires clean committed candidate")
    review_data = load("review.json")
    require(all(review_data[k] == v for k, v in candidate().items()), "stale review")
    build = ROOT / "build"
    build.mkdir()
    shutil.copyfile(REPO / "src/greet.py", build / "__main__.py")
    artifact = ROOT / "fixture-greeter.pyz"
    zipapp.create_archive(build, artifact)
    runs = []
    transcript = []
    for label, app in [("source", REPO / "src/greet.py"), ("built zipapp", artifact)]:
        cmd = [str(REPO / "debian/tests/basic")]
        result = subprocess.run(cmd, cwd=REPO, env=dict(os.environ, FIXTURE_APP=str(app)),
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        runs.append({"label": label, "argv": cmd, "app": str(app), "exit": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
        transcript.append(f"{label}: exit {result.returncode}\n{result.stdout}{result.stderr}")
    (ROOT / "functional.log").write_text("\n".join(transcript))
    save("validation.json", dict(candidate(), runs=runs, artifact_sha256=sha(artifact),
         skips=["Real Debian package build and lintian are outside this stdlib fixture acceptance test.",
                "No network, live BTS/archives, native ABI, or cross-architecture checks."]))
    require(all(r["exit"] == 0 for r in runs), "functional validation failed; see functional.log")
    require(all("named greeting: OK\nversion 1.1: OK\nold positional invocation rejected: OK\n" == r["stdout"] for r in runs),
            "unexpected functional output")
    # Synthetic gate records test runner wiring, not Debian validation.
    save("gate-fixture.json", {"semantic_review": "passed", "checks": [
        {"category": category, "status": "passed", "exit_code": 0,
         "command": ["synthetic-fixture-not-debian-validation", category],
         "log": "functional.log", "sha256": sha(ROOT / "functional.log")}
        for category in ["build", "lintian", "runtime"]]})
    print((ROOT / "functional.log").read_text())


def handoff():
    checked = load("validation.json")
    require(all(checked[k] == v for k, v in candidate().items()), "stale tests")
    require(all(r["exit"] == 0 for r in checked["runs"]), "failed tests cannot produce a handoff")
    title = "Update fixture-greeter to 1.1"
    body = ("Import version 1.1 and adapt the Debian smoke test to the required --name option.\n\n"
            "The historical changelog and maintainer metadata are preserved.\n\n"
            "Tests: the executable Debian smoke test passed against source and the built Python zipapp "
            "(greeting, version, rejected positional invocation).\n\n"
            "Limitations: scripted offline fixture only; no Debian package build, lintian, live bug/archive "
            "lookup or native ABI checks. Not WasmEdge validation or archive acceptance.\n"
            "AI-assisted acceptance fixture; please review the CLI compatibility change.\n")
    (ROOT / "MR-DRAFT.md").write_text(title + "\n\n" + body)
    save("handoff.json", dict(candidate(), title=title, body=body))
    print("English MR draft linked to tested commit " + checked["head"])


def audit():
    # Separate audit after LOCAL_PLAN_COMPLETE: the runner does not certify readiness.
    state = load("state/state.json")
    require(state["result"] == "LOCAL_PLAN_COMPLETE", "local workflow is not complete")
    require(not git("status", "--porcelain"), "candidate changed after testing")
    for stage in state["stages"].values():
        require(stage["status"] == "passed", "stage did not pass")
        for path, expected in stage["outputs"].items():
            require(sha(path) == expected, "retained output changed")
    require(not inspect()["missing_changelog_entries"], "semantic reconciliation is incomplete")
    for name in ["review.json", "validation.json", "handoff.json"]:
        require(all(load(name)[k] == v for k, v in candidate().items()), "stale evidence: " + name)
    validation = load("validation.json")
    require(all(r["exit"] == 0 for r in validation["runs"]), "failed validation cannot become ready")
    require(validation["artifact_sha256"] == sha(ROOT / "fixture-greeter.pyz"), "built artifact changed")
    evidence = ["intent.json", "prepare.json", "old-consumer.log", "review.json", "candidate.diff",
                "validation.json", "functional.log", "fixture-greeter.pyz", "MR-DRAFT.md", "handoff.json"]
    save("ready.json", dict(candidate(), status="READY_FOR_REVIEW", scope="Scripted offline fixture only",
         limitations=validation["skips"], evidence=[{"path": str(ROOT / p), "sha256": sha(ROOT / p)} for p in evidence]))
    print("READY_FOR_REVIEW: fixture 1.1-1; scripted offline checks only; no publication permission")


if __name__ == "__main__":
    try:
        {"prepare": prepare, "review": review, "validate": validate, "handoff": handoff, "audit": audit}[sys.argv[1]]()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
