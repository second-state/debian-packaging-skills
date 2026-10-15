#!/usr/bin/env python3
"""Validate local check records; never run tests or authorize publication."""
import argparse
import hashlib
import json
from pathlib import Path


def inspect_report(path):
    report = json.loads(path.read_text())
    problems = []
    if report.get("semantic_review") != "passed":
        problems.append("semantic review is incomplete")
    checks = report.get("checks")
    if not isinstance(checks, list):
        return problems + ["checks must be a list"]
    categories = set()
    for check in checks:
        if not isinstance(check, dict):
            problems.append("invalid check record")
            continue
        category = check.get("category")
        if not isinstance(category, str) or not category:
            problems.append("missing category")
            continue
        categories.add(category)
        if check.get("status") == "not-applicable":
            if category in {"build", "lintian", "runtime"}:
                problems.append(category + ": required check cannot be skipped")
            if not isinstance(check.get("reason"), str) or not check["reason"].strip():
                problems.append(category + ": missing exception rationale")
            continue
        if check.get("status") != "passed" or type(check.get("exit_code")) is not int or check["exit_code"] != 0:
            problems.append(category + ": not passed")
        command = check.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
            problems.append(category + ": missing argv command")
        log = check.get("log")
        if not isinstance(log, str) or not log:
            problems.append(category + ": missing log")
            continue
        try:
            actual = hashlib.sha256((path.parent / log).read_bytes()).hexdigest()
            if actual != check.get("sha256"):
                problems.append(category + ": log changed")
        except OSError:
            problems.append(category + ": log unavailable")
    for required in ["build", "lintian", "runtime"]:
        if required not in categories:
            problems.append(required + ": missing required check")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        problems = inspect_report(args.report)
    except (OSError, ValueError, AttributeError) as exc:
        parser.exit(1, "BLOCKED: " + str(exc) + "\n")
    if problems:
        print("BLOCKED: " + "; ".join(problems))
        return 1
    print("VALIDATION_RECORDS_COMPLETE: semantic truth/candidate binding remain reviewer responsibilities; no publication authorized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
