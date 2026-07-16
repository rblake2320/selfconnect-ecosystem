#!/usr/bin/env python3
"""Release claim scan — portfolio gate for public GitHub release title/body claims.

Scans release titles and bodies for compliance/authorization claims that a
repository cannot self-establish (FIPS validation, DoD Impact Level
authorization, ATO, production-readiness declarations). Titles must always be
clean. Body hits are tolerated only when a dated bounded correction notice
supersedes them (the pattern used to retain implementation history while
retracting claims).

Usage:
    python scripts/release_claim_scan.py --repo rblake2320/bpc-protocol \
        --repo rblake2320/tsk-protocol --repo rblake2320/selfconnect-enterprise
    python scripts/release_claim_scan.py --json-file fixtures.json

Exit codes: 0 = all clean or bounded, 1 = violations, 2 = fetch/parse error.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys

DEFAULT_ALLOWLIST = pathlib.Path(__file__).with_name("claim_scan_allowlist.json")

CLAIM_PATTERNS: list[tuple[str, str]] = [
    (r"\bIL\s*[4-7]\s*[-/–]\s*[4-7]\b", "DoD Impact Level range claim (e.g. IL4-7)"),
    (r"\bIL\s*[4-7]\s*/\s*[4-7]\s*/\s*[4-7]", "DoD Impact Level list claim (e.g. IL4/5/6)"),
    (r"\bcomply\s+with\s+IL", "IL compliance assertion"),
    (r"\bFIPS\s*140(?:-\d(?:/\d)?)?\s*(?:complian|validated|certified)", "FIPS validation/compliance claim"),
    (r"\bcomply\b[^.\n]{0,80}\bFIPS\s*140", "FIPS compliance assertion"),
    (r"\bproduction[- ]ready\b", "production-ready declaration"),
    (r"\bProduction\s+Release\b", "Production Release label"),
    (r"\bATO\b[^.\n]{0,40}\b(?:granted|holds|achieved|obtained)", "ATO possession claim"),
    (r"\b(?:NIST\s+SP\s*800-53\s+High)\b[^.\n]{0,60}\bcompl", "NIST SP 800-53 High compliance claim"),
]

NOTICE_MARKERS = ("claim correction", "retracted")
NOTICE_LINK_RE = re.compile(r"\b(?:SECURITY|PARKED)\.md\b", re.IGNORECASE)
NOTICE_DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")


def find_claims(text: str) -> list[dict]:
    hits = []
    for pattern, label in CLAIM_PATTERNS:
        for m in re.finditer(pattern, text or "", re.IGNORECASE):
            hits.append({"label": label, "match": m.group(0), "offset": m.start()})
    return hits


def notice_position(body: str) -> int:
    """Offset of a valid bounded correction notice, or -1.

    Valid requires: all markers present, an ISO date (YYYY-MM-DD), and a link
    to the maintained SECURITY/PARKED boundary. The returned offset is where
    the notice starts ("claim correction" marker); callers must enforce that
    it precedes every claim, so a marker appended after claims cannot bypass.
    """
    text = body or ""
    low = text.lower()
    pos = low.find(NOTICE_MARKERS[0])
    if pos < 0:
        return -1
    if not all(marker in low for marker in NOTICE_MARKERS):
        return -1
    if not NOTICE_LINK_RE.search(text):
        return -1
    if not NOTICE_DATE_RE.search(text):
        return -1
    return pos


def has_bounded_notice(body: str) -> bool:
    return notice_position(body) >= 0


def leading_notice_block(body: str) -> str:
    """The blockquote notice that must OPEN the body, up to the first ---.

    Returns "" unless the body's first non-blank content is a '>' blockquote
    and a '---' separator follows. Only elements inside this leading block
    count toward notice validity: scattering marker/date/link elsewhere in
    the body can never assemble a valid notice (split-element bypass), and a
    notice appended after claims is not leading (order bypass). Claims quoted
    INSIDE the block are the retracted ones by construction.
    """
    text = body or ""
    sep = text.find("\n---")
    if sep < 0:
        return ""
    head = text[:sep]
    if not head.lstrip().startswith(">"):
        return ""
    return head


def load_allowlist(path: pathlib.Path | str | None = None) -> dict:
    """Map (repo, tag) -> allowlist entry. Missing file = empty allowlist."""
    p = pathlib.Path(path) if path else DEFAULT_ALLOWLIST
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as fh:
        data = json.load(fh)
    return {(e["repo"], e["tag"]): e for e in data.get("entries", [])}


def allowlist_verdict(entry: dict | None, body: str, today: datetime.date | None = None) -> tuple[bool, str]:
    """Bounded status is an exact, expiring exception — not a blanket notice.

    Requires an allowlist entry for this repo@tag whose body_sha256 matches
    the CURRENT body (so any later edit — e.g. new claims appended under the
    old notice — voids the exception) and whose review_by date has not
    passed (so every exception gets re-reviewed, enforced by the daily CI
    run).
    """
    if entry is None:
        return False, "release not in claim_scan_allowlist.json (bounded status requires an exact reviewed exception)"
    digest = hashlib.sha256((body or "").encode("utf-8")).hexdigest()
    if digest != entry.get("body_sha256"):
        return False, "body changed since allowlist review (sha256 mismatch — new content is unreviewed)"
    today = today or datetime.date.today()
    review_by = datetime.date.fromisoformat(entry.get("review_by", "1970-01-01"))
    if today > review_by:
        return False, f"allowlist exception expired (review_by {review_by.isoformat()})"
    return True, "exact allowlisted exception (sha256 match, within review window)"


def scan_release(release: dict, repo: str = "?", allowlist: dict | None = None) -> dict:
    title = release.get("name") or ""
    body = release.get("body") or ""
    tag = release.get("tag_name") or "?"
    title_hits = find_claims(title)
    body_hits = find_claims(body)
    # Every required notice element (marker, retraction, ISO date, boundary
    # link) must validate inside the LEADING blockquote notice: elements
    # scattered after claims can never assemble a valid notice.
    has_leading_notice = notice_position(leading_notice_block(body)) >= 0
    entry = (allowlist or {}).get((repo, tag))
    allowed, allow_reason = allowlist_verdict(entry, body)
    bounded = bool(body_hits) and has_leading_notice and allowed
    if title_hits:
        status = "fail"
        reason = "title carries claims (titles must always be clean)"
    elif body_hits and has_leading_notice and not allowed:
        status = "fail"
        reason = allow_reason
    elif body_hits and not has_leading_notice and notice_position(body) >= 0:
        status = "fail"
        reason = "notice elements not in a valid leading notice block (bypass attempt)"
    elif body_hits and not bounded:
        status = "fail"
        reason = "body carries claims with no valid dated correction notice preceding them"
    elif body_hits and bounded:
        status = "bounded"
        reason = f"historical claims under dated leading notice; {allow_reason}"
    else:
        status = "clean"
        reason = "no claim patterns found"
    return {
        "tag": tag,
        "title": title,
        "status": status,
        "reason": reason,
        "title_hits": title_hits,
        "body_hits": body_hits,
    }


def fetch_releases(repo: str) -> list[dict]:
    out = subprocess.run(
        ["gh", "api", f"repos/{repo}/releases"],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise RuntimeError(f"gh api failed for {repo}: {out.stderr.strip()[:200]}")
    return json.loads(out.stdout)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", action="append", default=[], help="owner/name (repeatable)")
    ap.add_argument("--json-file", help="offline mode: JSON file with {repo: [releases...]}")
    ap.add_argument("--allowlist", help=f"allowlist JSON path (default: {DEFAULT_ALLOWLIST.name})")
    args = ap.parse_args(argv)

    try:
        allowlist = load_allowlist(args.allowlist)
    except Exception as exc:  # noqa: BLE001 - malformed allowlist must fail closed
        print(f"ERROR: allowlist unreadable: {exc}", file=sys.stderr)
        return 2

    sources: dict[str, list[dict]] = {}
    try:
        if args.json_file:
            with open(args.json_file, encoding="utf-8") as fh:
                sources = json.load(fh)
        for repo in args.repo:
            sources[repo] = fetch_releases(repo)
    except Exception as exc:  # noqa: BLE001 - gate must report, not crash silently
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not sources:
        print("ERROR: no --repo or --json-file given", file=sys.stderr)
        return 2

    failed = False
    for repo, releases in sources.items():
        if not releases:
            print(f"{repo}: no releases (clean by absence)")
            continue
        for release in releases:
            result = scan_release(release, repo=repo, allowlist=allowlist)
            flag = {"clean": "OK ", "bounded": "OK*", "fail": "FAIL"}[result["status"]]
            print(f"{flag} {repo}@{result['tag']} [{result['status']}] {result['reason']}")
            for hit in result["title_hits"] + result["body_hits"]:
                print(f"     - {hit['label']}: {hit['match']!r}")
            if result["status"] == "fail":
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
