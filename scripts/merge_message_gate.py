#!/usr/bin/env python3
"""Detect stale evidence in branch commits and verify reviewed squash messages.

This is a bounded provenance control. It makes unmanaged/default squash merges
detectable; it cannot prevent a repository administrator from bypassing GitHub
settings or fabricating a trailer outside the reviewed helper.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import subprocess
import sys
import tempfile

from release_claim_scan import find_claims


TRAILER_CONTENT = "SelfConnect-Reviewed-Content-SHA256"
TRAILER_EVIDENCE = "SelfConnect-Reviewed-Evidence-SHA256"
TRAILER_HEAD = "SelfConnect-Reviewed-Head-SHA"
RESERVED_TRAILER_RE = re.compile(
    r"(?mi)^SelfConnect-Reviewed-(?:Content-SHA256|Evidence-SHA256|Head-SHA):"
)

EVIDENCE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b\d+\s*/\s*\d+\s+(?:tests?|checks?|passed|green)\b", "numeric test/check result"),
    (r"\b\d+\s+(?:tests?|checks?)\s+(?:pass(?:ed)?|green)\b", "numeric test/check result"),
    (r"\b(?:all|full)\s+(?:tests?|suite|checks?)\s+(?:pass(?:ed)?|green)\b", "unbounded green-suite claim"),
    (r"\b(?:approved|mergeable|fully verified)\b", "review/readiness verdict"),
    (r"\b(?:no|zero)\s+(?:failures?|defects?|issues?)\b", "zero-defect/failure claim"),
)

TRAILER_RE = re.compile(
    rf"(?m)^(?:{TRAILER_CONTENT}|{TRAILER_EVIDENCE}):\s*([0-9a-f]{{64}})$"
)
HEAD_RE = re.compile(rf"(?m)^{TRAILER_HEAD}:\s*([0-9a-f]{{40}})$")


class GateError(RuntimeError):
    """A fail-closed gate error."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def evidence_hits(text: str) -> list[str]:
    hits = [hit["label"] for hit in find_claims(text)]
    for pattern, label in EVIDENCE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(label)
    return sorted(set(hits))


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8",
        errors="strict", timeout=120,
    )
    if result.returncode:
        raise GateError(f"git {' '.join(args)} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def commits_in_range(base: str, head: str) -> list[tuple[str, str]]:
    shas = [line for line in run_git("rev-list", "--reverse", f"{base}..{head}").splitlines() if line]
    return [(commit, run_git("show", "-s", "--format=%B", commit)) for commit in shas]


def scan_branch_messages(base: str, head: str) -> list[tuple[str, list[str]]]:
    failures = []
    for commit, message in commits_in_range(base, head):
        hits = evidence_hits(message)
        if hits:
            failures.append((commit, hits))
    return failures


def reviewed_content(subject: str, body: str) -> str:
    return f"{canonical_text(subject)}\n\n{canonical_text(body)}"


def compose_message(subject: str, body: str, evidence: bytes, head_sha: str) -> str:
    subject = canonical_text(subject)
    body = canonical_text(body)
    if not subject or "\n" in subject:
        raise GateError("subject must be one non-empty line")
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise GateError("head SHA must be 40 lowercase hexadecimal characters")
    if RESERVED_TRAILER_RE.search(f"{subject}\n{body}"):
        raise GateError("reviewed subject/body contains a reserved trailer name")
    claims = [hit["label"] for hit in find_claims(f"{subject}\n{body}")]
    if claims:
        raise GateError("reviewed message contains prohibited capability claims: " + ", ".join(sorted(set(claims))))
    content = reviewed_content(subject, body)
    return (
        f"{content}\n\n"
        f"{TRAILER_CONTENT}: {sha256(content.encode('utf-8'))}\n"
        f"{TRAILER_EVIDENCE}: {sha256(evidence)}\n"
        f"{TRAILER_HEAD}: {head_sha}\n"
    )


def merge_body(subject: str, body: str, evidence: bytes, head_sha: str) -> str:
    """Return reviewed body/trailers for `gh pr merge --subject ...`."""
    full = compose_message(subject, body, evidence, head_sha)
    prefix = canonical_text(subject) + "\n\n"
    if not full.startswith(prefix):
        raise GateError("composed message does not begin with the reviewed subject")
    return full[len(prefix) :]


def run_gh(*args: str) -> str:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8",
        errors="strict", timeout=120,
    )
    if result.returncode:
        raise GateError(f"gh {' '.join(args)} failed: {result.stderr.strip()[:300]}")
    return result.stdout


def fetch_pr(repo: str, pr: int) -> dict:
    import json

    try:
        value = json.loads(run_gh("api", f"repos/{repo}/pulls/{pr}"))
    except (ValueError, TypeError) as exc:
        raise GateError("GitHub returned malformed pull-request metadata") from exc
    if not isinstance(value, dict) or not isinstance(value.get("head"), dict):
        raise GateError("GitHub pull-request metadata has an unexpected shape")
    return value


def fetch_pr_commit_messages(repo: str, pr: int) -> list[tuple[str, str]]:
    import json

    try:
        pages = json.loads(run_gh(
            "api", "--paginate", "--slurp", f"repos/{repo}/pulls/{pr}/commits?per_page=100",
        ))
    except (ValueError, TypeError) as exc:
        raise GateError("GitHub returned malformed pull-request commit data") from exc
    if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
        raise GateError("GitHub pull-request pagination shape is invalid")
    commits: list[tuple[str, str]] = []
    for page in pages:
        for item in page:
            if not isinstance(item, dict) or not isinstance(item.get("commit"), dict):
                raise GateError("GitHub pull-request commit entry is invalid")
            commit_sha = item.get("sha")
            message = item["commit"].get("message")
            if not isinstance(commit_sha, str) or not isinstance(message, str):
                raise GateError("GitHub pull-request commit identity/message is invalid")
            commits.append((commit_sha, message))
    return commits


def merge_pr(repo: str, pr: int, subject: str, body: str, evidence: bytes, delete_branch: bool) -> str:
    """Squash with an explicit reviewed message and immutable head match."""
    metadata = fetch_pr(repo, pr)
    if metadata.get("state") != "open" or metadata.get("draft") is True:
        raise GateError("pull request must be open and non-draft")
    head_sha = metadata["head"].get("sha")
    if not isinstance(head_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise GateError("pull-request head SHA is missing or malformed")
    failures = []
    for commit, commit_message in fetch_pr_commit_messages(repo, pr):
        hits = evidence_hits(commit_message)
        if hits:
            failures.append(f"{commit[:12]}: {', '.join(hits)}")
    if failures:
        raise GateError("intermediate commit evidence must be removed before merge: " + "; ".join(failures))

    reviewed_body = merge_body(subject, body, evidence, head_sha)
    verify_reviewed_message(f"{canonical_text(subject)}\n\n{reviewed_body}")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", suffix=".md", delete=False) as fh:
        fh.write(reviewed_body)
        body_path = pathlib.Path(fh.name)
    try:
        args = [
            "pr", "merge", str(pr), "--repo", repo, "--squash",
            "--subject", canonical_text(subject), "--body-file", str(body_path),
            "--match-head-commit", head_sha,
        ]
        if delete_branch:
            args.append("--delete-branch")
        return run_gh(*args)
    finally:
        body_path.unlink(missing_ok=True)


def split_reviewed_message(message: str) -> tuple[str, dict[str, str]]:
    text = canonical_text(message)
    marker = f"\n\n{TRAILER_CONTENT}: "
    pos = text.rfind(marker)
    if pos < 0:
        raise GateError("reviewed content trailer is absent")
    content = text[:pos]
    trailer_block = text[pos + 2 :]
    trailers: dict[str, str] = {}
    for line in trailer_block.splitlines():
        if ": " not in line:
            raise GateError("unexpected text in reviewed trailer block")
        key, value = line.split(": ", 1)
        if key in trailers:
            raise GateError(f"duplicate trailer: {key}")
        trailers[key] = value
    if set(trailers) != {TRAILER_CONTENT, TRAILER_EVIDENCE, TRAILER_HEAD}:
        raise GateError("reviewed trailer set is incomplete or contains unknown fields")
    return content, trailers


def verify_reviewed_message(message: str) -> None:
    content, trailers = split_reviewed_message(message)
    if not re.fullmatch(r"[0-9a-f]{64}", trailers[TRAILER_CONTENT]):
        raise GateError("content digest is malformed")
    if not re.fullmatch(r"[0-9a-f]{64}", trailers[TRAILER_EVIDENCE]):
        raise GateError("evidence digest is malformed")
    if not re.fullmatch(r"[0-9a-f]{40}", trailers[TRAILER_HEAD]):
        raise GateError("reviewed head SHA is malformed")
    if sha256(content.encode("utf-8")) != trailers[TRAILER_CONTENT]:
        raise GateError("reviewed content digest mismatch")
    claims = [hit["label"] for hit in find_claims(content)]
    if claims:
        raise GateError("reviewed message contains prohibited capability claims")


def scan_main(baseline: str, head: str) -> list[tuple[str, str]]:
    failures = []
    shas = [line for line in run_git("rev-list", "--first-parent", "--reverse", f"{baseline}..{head}").splitlines() if line]
    for commit in shas:
        message = run_git("show", "-s", "--format=%B", commit)
        try:
            verify_reviewed_message(message)
        except GateError as exc:
            failures.append((commit, str(exc)))
    return failures


def read_text(path: str) -> str:
    return pathlib.Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan-range")
    scan.add_argument("--base", required=True)
    scan.add_argument("--head", required=True)

    compose = sub.add_parser("compose")
    compose.add_argument("--subject", required=True)
    compose.add_argument("--body-file", required=True)
    compose.add_argument("--evidence-file", required=True)
    compose.add_argument("--head-sha", required=True)
    compose.add_argument("--output", required=True)

    merge = sub.add_parser("merge-pr")
    merge.add_argument("--repo", required=True)
    merge.add_argument("--pr", required=True, type=int)
    merge.add_argument("--subject", required=True)
    merge.add_argument("--body-file", required=True)
    merge.add_argument("--evidence-file", required=True)
    merge.add_argument("--delete-branch", action="store_true")

    verify = sub.add_parser("verify-message")
    verify.add_argument("--message-file", required=True)

    main_scan = sub.add_parser("scan-main")
    main_scan.add_argument("--baseline", required=True)
    main_scan.add_argument("--head", default="HEAD")

    args = parser.parse_args(argv)
    try:
        if args.command == "scan-range":
            failures = scan_branch_messages(args.base, args.head)
            for commit, hits in failures:
                print(f"FAIL {commit}: {', '.join(hits)}")
            return 1 if failures else 0
        if args.command == "compose":
            message = compose_message(
                args.subject, read_text(args.body_file), pathlib.Path(args.evidence_file).read_bytes(), args.head_sha,
            )
            pathlib.Path(args.output).write_text(message, encoding="utf-8", newline="\n")
            verify_reviewed_message(message)
            return 0
        if args.command == "merge-pr":
            output = merge_pr(
                args.repo, args.pr, args.subject, read_text(args.body_file),
                pathlib.Path(args.evidence_file).read_bytes(), args.delete_branch,
            )
            if output.strip():
                print(output.strip())
            return 0
        if args.command == "verify-message":
            verify_reviewed_message(read_text(args.message_file))
            return 0
        baseline = args.baseline.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", baseline):
            raise GateError("baseline must be one full lowercase commit SHA")
        failures = scan_main(baseline, args.head)
        for commit, reason in failures:
            print(f"FAIL {commit}: {reason}")
        return 1 if failures else 0
    except (GateError, OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
