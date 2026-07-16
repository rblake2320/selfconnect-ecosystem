#!/usr/bin/env python3
"""Resolve commit-pinned GitHub security-policy references."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


REFERENCE_PATTERN = re.compile(
    r"https://github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+)/blob/"
    r"(?P<commit>[0-9a-fA-F]{40})/"
    r"(?P<path>[^)\s]+)"
)


@dataclass(frozen=True)
class SecurityReference:
    owner: str
    repo: str
    commit: str
    path: str
    url: str

    @property
    def api_url(self) -> str:
        encoded_path = urllib.parse.quote(self.path, safe="/")
        encoded_ref = urllib.parse.quote(self.commit, safe="")
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/"
            f"{encoded_path}?ref={encoded_ref}"
        )


def extract_references(text: str) -> list[SecurityReference]:
    references: list[SecurityReference] = []
    seen: set[str] = set()
    for match in REFERENCE_PATTERN.finditer(text):
        url = match.group(0)
        if url in seen:
            continue
        seen.add(url)
        references.append(
            SecurityReference(
                owner=match.group("owner"),
                repo=match.group("repo"),
                commit=match.group("commit").lower(),
                path=match.group("path"),
                url=url,
            )
        )
    return references


def resolve_reference(reference: SecurityReference, token: str = "") -> dict[str, str | bool]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "selfconnect-security-reference-check/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(reference.api_url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return {"ok": False, "url": reference.url, "status": "unresolved"}
    if not isinstance(payload, dict) or payload.get("type") != "file":
        return {"ok": False, "url": reference.url, "status": "not_file"}
    if payload.get("sha") in (None, ""):
        return {"ok": False, "url": reference.url, "status": "missing_blob_sha"}
    return {"ok": True, "url": reference.url, "status": "resolved"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    args = parser.parse_args()

    text = args.policy.read_text(encoding="utf-8")
    references = extract_references(text)
    if not references:
        print("no commit-pinned security references found", file=sys.stderr)
        return 2

    token = os.environ.get("GITHUB_TOKEN", "")
    results = [resolve_reference(reference, token) for reference in references]
    print(json.dumps(results, indent=2))
    return 0 if all(result["ok"] is True for result in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
