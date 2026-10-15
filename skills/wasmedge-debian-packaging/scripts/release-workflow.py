#!/usr/bin/env python3
"""Durable local stage runner. No implicit publication or readiness certification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

STAGES = ["prepare", "review", "validate", "handoff"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)


def candidate_identity(cwd, plan):
    identities = {}
    for name in plan.get("candidate_repos", []):
        repo = (cwd / name).resolve()
        if not repo.exists():
            identities[str(repo)] = None
            continue
        def git(*args):
            return subprocess.check_output(["git", "-C", str(repo), *args])
        head = git("rev-parse", "HEAD").decode().strip()
        tree = git("diff", "--binary", "HEAD")
        untracked = {}
        for raw in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
            if raw:
                path = repo / os.fsdecode(raw)
                untracked[os.fsdecode(raw)] = hashlib.sha256(os.readlink(path).encode() if path.is_symlink() else path.read_bytes()).hexdigest()
        identities[str(repo)] = {"head": head, "diff": hashlib.sha256(tree).hexdigest(), "untracked": untracked}
    return identities


def run(plan_path, state_dir):
    raw = plan_path.read_bytes()
    plan = json.loads(raw)
    fingerprint = hashlib.sha256(raw).hexdigest()
    cwd = Path(plan["cwd"]).resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("cwd must be a directory")
    inputs = {}
    for name in plan.get("inputs", []):
        path = (cwd / name).resolve(strict=True)
        inputs[str(path)] = digest(path)
    if not inputs:
        raise ValueError("plan requires candidate/driver input files to detect stale work")
    if not plan.get("candidate_repos"):
        raise ValueError("candidate_repos required for live resume validation")
    validation_report = plan.get("validation_report")
    if not isinstance(validation_report, str) or not validation_report:
        raise ValueError("validation_report path required before handoff")
    stages = plan["stages"]
    if [s["name"] for s in stages] != STAGES:
        raise ValueError("require prepare, review, validate, handoff in order")
    for stage in stages:
        if not stage.get("commands") or not stage.get("outputs"):
            raise ValueError("each stage needs commands and retained outputs")
        for cmd in stage["commands"]:
            if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
                raise ValueError("commands must be nonempty argv arrays")
            binary = Path(cmd[0]).name
            if binary in {"dput", "dupload", "sendmail", "mail", "mailx", "requestsync", "requestbackport"}:
                raise ValueError("external submission command forbidden in local plan")
            if binary == "git" and "push" in cmd or binary in {"gh", "glab"} and any(x in cmd for x in ["create", "edit", "comment", "merge", "upload"]):
                raise ValueError("publication command forbidden in local plan")
        for output in stage["outputs"]:
            if not isinstance(output, str):
                raise ValueError("output paths must be strings")
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "run.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError("run already locked; inspect active process before recovery")
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        state_path = state_dir / "state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {"plan_sha256": fingerprint, "stages": {}, "publication_authorized": False, "inputs": inputs}
        if state["plan_sha256"] != fingerprint:
            raise ValueError("plan changed; use a new state directory")
        if state.get("inputs") != inputs:
            raise ValueError("candidate/driver inputs changed; replan affected stages")
        if state.get("candidate_identity") is not None and state["candidate_identity"] != candidate_identity(cwd, plan):
            raise ValueError("live candidate changed; replan affected stages")
        # Validate all completed evidence before executing anything.
        for record in state["stages"].values():
            if record["status"] == "passed":
                for name, expected in record["outputs"].items():
                    path = Path(name)
                    if not path.is_file() or digest(path) != expected:
                        raise ValueError("completed output changed; replan affected stages: " + name)
        resuming = bool(state["stages"])
        if resuming:
            passed = [stage for stage in stages if state["stages"].get(stage["name"], {}).get("status") == "passed"]
            if passed:
                latest = passed[-1]
                if state["stages"][latest["name"]].get("candidate_identity") != candidate_identity(cwd, plan):
                    state["result"] = "STALE_CANDIDATE"
                    save(state_path, state)
                    raise ValueError("candidate changed after completed stage; replan and rerun affected stages")
        for index, stage in enumerate(stages):
            name = stage["name"]
            previous = state["stages"].get(name, {})
            if previous.get("status") == "passed":
                print(name + ": retained")
                continue
            if previous.get("status") in {"running", "failed"}:
                raise ValueError("interrupted/failed stage requires recovery review and a new plan: " + name)
            state["stages"][name] = {"status": "running"}
            state["result"] = "RUNNING"
            save(state_path, state)
            with (state_dir / (name + ".log")).open("w") as log:
                code = 0
                commands = list(stage["commands"])
                if name == "handoff":
                    commands.insert(0, [sys.executable, str(Path(__file__).with_name("check-validation.py")),
                                        "--report", str(cwd / validation_report)])
                for cmd in commands:
                    try:
                        code = subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT).returncode
                    except OSError as exc:
                        log.write(str(exc) + "\n")
                        code = 127
                    if code:
                        break
            outputs = {}
            if not code:
                retained_outputs = list(stage["outputs"])
                if name == "validate":
                    retained_outputs.append(validation_report)
                for output in retained_outputs:
                    path = (cwd / output).resolve()
                    if not path.is_file():
                        code = 1
                        break
                    outputs[str(path)] = digest(path)
            state["stages"][name] = {"status": "failed" if code else "passed", "exit": code, "outputs": outputs, "candidate_identity": candidate_identity(cwd, plan)}
            if code:
                state["result"] = "BLOCKED"
                save(state_path, state)
                print(name + ": BLOCKED; see " + str(state_dir / (name + ".log")))
                return 1
            state["candidate_identity"] = candidate_identity(cwd, plan)
            save(state_path, state)
            print(name + ": passed")
        state["result"] = "LOCAL_PLAN_COMPLETE"
        save(state_path, state)
        print("LOCAL_PLAN_COMPLETE: semantic readiness review and separate publication permission still required")
        return 0
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        return run(args.plan, args.state_dir)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
