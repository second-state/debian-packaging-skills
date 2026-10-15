#!/usr/bin/env python3
"""Preview or submit one owner-approved Salsa MR. Defaults to read-only preview."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote, urlencode


class Client:
    def api(self, path, fields=None):
        cmd = ["glab", "api", "--hostname", "salsa.debian.org", path]
        if fields is not None:
            cmd += ["--method", "POST"]
            for key, value in fields.items():
                cmd += ["-f", key + "=" + str(value)]
        return json.loads(subprocess.check_output(cmd, text=True))

    def git(self, repo, *args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def check(plan, client):
    required = ["repo", "source_project", "target_project", "source_branch", "target_branch", "head", "base", "account", "title", "body", "ready_report"]
    if any(not isinstance(plan.get(k), str) or not plan[k] for k in required):
        raise ValueError("incomplete submission plan")
    if any(plan[k].startswith("-") or "\n" in plan[k] for k in ["source_branch", "target_branch"]):
        raise ValueError("invalid branch")
    if plan["source_project"] == plan["target_project"]:
        raise ValueError("use a reviewed fork, not a canonical push destination")
    if not all(len(plan[k]) == 40 and all(c in "0123456789abcdef" for c in plan[k]) for k in ["head", "base"]):
        raise ValueError("full immutable commit IDs required")
    repo = Path(plan["repo"]).resolve(strict=True)
    if client.git(repo, "status", "--porcelain"):
        raise ValueError("candidate working tree must be clean")
    if client.git(repo, "rev-parse", "HEAD") != plan["head"]:
        raise ValueError("candidate HEAD changed")
    if client.git(repo, "rev-parse", "refs/heads/" + plan["source_branch"]) != plan["head"]:
        raise ValueError("source branch differs from reviewed HEAD")
    report_path = Path(plan["ready_report"])
    if hashlib.sha256(report_path.read_bytes()).hexdigest() != plan.get("ready_report_sha256"):
        raise ValueError("readiness report changed or not pinned")
    report = json.loads(report_path.read_text())
    if report.get("status") != "READY_FOR_REVIEW" or report.get("head") != plan["head"] or report.get("base") != plan["base"]:
        raise ValueError("readiness report does not match candidate")
    # Report is an audited assistant artifact, not an authorization token.
    for evidence in report.get("evidence", []):
        path = Path(evidence["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != evidence["sha256"]:
            raise ValueError("validation evidence changed")
    if not report.get("evidence"):
        raise ValueError("missing readiness evidence")
    user = client.api("user")
    if user["username"] != plan["account"]:
        raise ValueError("active Salsa account differs from approved account")
    source = client.api("projects/" + quote(plan["source_project"], safe=""))
    target = client.api("projects/" + quote(plan["target_project"], safe=""))
    if source["path_with_namespace"] != plan["source_project"] or target["path_with_namespace"] != plan["target_project"]:
        raise ValueError("project identity mismatch")
    if plan["source_project"].split("/")[0] != user["username"]:
        raise ValueError("source must be in the contributor's own namespace")
    if source.get("forked_from_project", {}).get("id") != target["id"]:
        raise ValueError("source must be a fork of the reviewed target")
    try:
        rewrites = client.git(repo, "config", "--get-regexp", r"^url\..*\.(insteadof|pushinsteadof)$")
    except subprocess.CalledProcessError as exc:
        if exc.returncode != 1:
            raise
        rewrites = ""
    if rewrites:
        raise ValueError("Git URL rewrites configured; inspect effective destination before submission")
    expected_url = "git@salsa.debian.org:" + plan["source_project"] + ".git"
    if source["ssh_url_to_repo"] != expected_url:
        raise ValueError("unexpected source push destination")
    refs = [{"ref": "refs/heads/" + plan["source_branch"], "sha": plan["head"]}] + plan.get("supporting_refs", [])
    branch = client.api("projects/%s/repository/branches/%s" % (target["id"], quote(plan["target_branch"], safe="")))
    # Canonical advancement blocks new effects, but existing exact proposals
    # must remain recoverable after their target branch advances.
    if branch["commit"]["id"] != plan["base"]:
        return repo, source, target, refs, "advanced"

    seen = set()
    for item in refs:
        ref = item["ref"]
        if not ref.startswith(("refs/heads/", "refs/tags/")) or ref in seen or ":" in ref:
            raise ValueError("invalid or duplicate push ref")
        seen.add(ref)
        client.git(repo, "check-ref-format", ref)
        if client.git(repo, "rev-parse", ref) != item["sha"]:
            raise ValueError("reviewed supporting ref changed")
    return repo, source, target, refs


def existing(plan, client, source, target):
    query = urlencode({"scope": "all", "state": "all", "source_branch": plan["source_branch"], "target_branch": plan["target_branch"], "per_page": 100})
    found = []
    page = 1
    while True:
        batch = client.api("projects/%s/merge_requests?%s&page=%s" % (target["id"], query, page))
        found += [m for m in batch if m["source_project_id"] == source["id"] and m["target_project_id"] == target["id"]]
        if len(batch) < 100:
            break
        page += 1
    return found


def verify_mr(plan, mr, source, target, allow_content_drift=False):
    identity = {"source_project_id": source["id"], "target_project_id": target["id"], "source_branch": plan["source_branch"], "target_branch": plan["target_branch"], "sha": plan["head"]}
    if any(mr.get(k) != v for k, v in identity.items()):
        raise ValueError("MR identity differs from reviewed proposal")
    if not allow_content_drift and (mr.get("title") != plan["title"] or mr.get("description") != plan["body"]):
        raise ValueError("MR content differs from reviewed proposal; do not overwrite")
    if not mr["web_url"].startswith("https://salsa.debian.org/" + plan["target_project"] + "/-/merge_requests/"):
        raise ValueError("unexpected MR URL")
    return mr["web_url"]


def submit_once(plan, client, approved_digest=None, journal=None):
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    checked = check(plan, client)
    repo, source, target, refs = checked[:4]
    base_state = checked[4] if len(checked) > 4 else "current"
    matches = existing(plan, client, source, target)
    if matches:
        if len(matches) != 1:
            raise ValueError("multiple existing proposals; inspect manually")
        mr = matches[0]
        if mr.get("sha") != plan["head"]:
            raise ValueError("existing proposal source head changed; inspect manually")
        if any(mr.get(k) != v for k, v in {"source_project_id": source["id"], "target_project_id": target["id"], "source_branch": plan["source_branch"], "target_branch": plan["target_branch"]}.items()):
            raise ValueError("existing proposal identity differs; inspect manually")
        try:
            url = verify_mr(plan, mr, source, target, allow_content_drift=True)
            drift = mr.get("title") != plan["title"] or mr.get("description") != plan["body"]
        except ValueError:
            url = mr["web_url"]
            drift = True
        return {"status": "EXISTING", "url": url, "state": mr["state"], "content_drift": drift}
    if journal is not None and journal.exists():
        prior = json.loads(journal.read_text())
        if prior["digest"] != digest:
            raise ValueError("submission journal belongs to a different plan")
        if prior["status"] in {"creating", "unknown", "submitted"}:
            raise ValueError("prior MR result not found; inspect server state before any retry")
    if base_state == "advanced":
        raise ValueError("canonical branch advanced; no matching existing MR; reconcile before submission")
    if approved_digest is None:
        return {"status": "AWAITING_OWNER_APPROVAL", "digest": digest, "plan": plan, "push_destination": source["ssh_url_to_repo"], "refs": refs}
    if approved_digest != digest:
        raise ValueError("approval digest differs; no effects permitted")
    # The invoking assistant MUST verify original owner consent separately.
    # A digest is only an exact-plan guard, never proof that a human approved.
    client.git(repo, "-c", "push.followTags=false", "-c", "push.pushOption=", "-c", "push.recurseSubmodules=no", "push", "--no-follow-tags", "--recurse-submodules=no", "--atomic", source["ssh_url_to_repo"], *[item["sha"] + ":" + item["ref"] for item in refs])
    if journal is not None:
        journal.write_text(json.dumps({"digest": digest, "status": "creating"}) + "\n")
    try:
        mr = client.api("projects/%s/merge_requests" % source["id"], {"source_branch": plan["source_branch"], "target_branch": plan["target_branch"], "target_project_id": target["id"], "title": plan["title"], "description": plan["body"]})
    except Exception:
        matches = existing(plan, client, source, target)
        if len(matches) != 1:
            if journal is not None:
                journal.write_text(json.dumps({"digest": digest, "status": "unknown"}) + "\n")
            raise ValueError("MR create result unknown; inspect before retrying")
        mr = matches[0]
    verified = client.api("projects/%s/merge_requests/%s" % (target["id"], mr["iid"]))
    result = {"status": "SUBMITTED", "url": verify_mr(plan, verified, source, target)}
    if journal is not None:
        journal.write_text(json.dumps({"digest": digest, "status": "submitted", "url": result["url"]}) + "\n")
    return result


def submit(plan, client, approved_digest=None, state_dir=None):
    if state_dir is None:
        # Tests may inject a transport without a journal; CLI always supplies one.
        return submit_once(plan, client, approved_digest)
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    lock = state_dir / "submit.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        return submit_once(plan, client, approved_digest, state_dir / "submission.json")
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path, help="stable candidate-specific submission journal directory")
    parser.add_argument("--approved-plan-sha256", help="exact-plan guard; invoking agent must already hold verified owner approval")
    args = parser.parse_args()
    try:
        print(json.dumps(submit(json.loads(args.plan.read_text()), Client(), args.approved_plan_sha256, args.state_dir), indent=2))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
