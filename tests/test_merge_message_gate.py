from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "scripts"))

from merge_message_gate import (  # noqa: E402
    GateError,
    compose_message,
    evidence_hits,
    fetch_pr_commit_messages,
    merge_body,
    merge_pr,
    split_reviewed_message,
    verify_reviewed_message,
)


HEAD = "a" * 40


def message(body: str = "Bounded change with linked evidence.") -> str:
    return compose_message("fix: bind reviewed merge evidence", body, b'{"checks":"green"}', HEAD)


@pytest.mark.parametrize("text", [
    "13/13 tests green",
    "216 tests passed",
    "all checks green",
    "fully verified and mergeable",
    "zero failures",
    "production-ready IL4-7 implementation",
])
def test_intermediate_evidence_is_rejected(text):
    assert evidence_hits(text)


def test_normal_commit_message_is_clean():
    assert evidence_hits("fix: verify receiver-bound acknowledgement") == []


def test_compose_and_verify_round_trip():
    value = message()
    verify_reviewed_message(value)
    content, trailers = split_reviewed_message(value)
    assert content.startswith("fix: bind reviewed merge evidence")
    assert trailers["SelfConnect-Reviewed-Head-SHA"] == HEAD


def test_tampered_content_fails():
    with pytest.raises(GateError, match="digest mismatch"):
        verify_reviewed_message(message().replace("Bounded change", "Different change"))


def test_missing_and_duplicate_trailers_fail():
    original = message()
    with pytest.raises(GateError, match="incomplete"):
        verify_reviewed_message("\n".join(original.splitlines()[:-1]))
    with pytest.raises(GateError, match="duplicate"):
        verify_reviewed_message(original + "SelfConnect-Reviewed-Head-SHA: " + HEAD + "\n")


def test_malformed_head_and_evidence_fail():
    with pytest.raises(GateError, match="head SHA"):
        compose_message("fix: subject", "body", b"evidence", "ABC")
    with pytest.raises(GateError, match="evidence digest"):
        verify_reviewed_message(message().replace("SelfConnect-Reviewed-Evidence-SHA256: ", "SelfConnect-Reviewed-Evidence-SHA256: zz"))


def test_reviewed_public_overclaim_fails_even_with_digest():
    with pytest.raises(GateError, match="prohibited capability"):
        compose_message("release: production-ready", "body", b"evidence", HEAD)


def test_unknown_trailer_text_fails():
    with pytest.raises(GateError, match="unknown"):
        verify_reviewed_message(message() + "Unknown-Trailer: value\n")


def test_merge_body_does_not_duplicate_subject():
    body = merge_body("fix: subject", "reviewed body", b"evidence", HEAD)
    assert not body.startswith("fix: subject")
    verify_reviewed_message("fix: subject\n\n" + body)


def test_paginated_commit_messages_are_strict(monkeypatch):
    payload = [[{"sha": "1" * 40, "commit": {"message": "fix: one"}}],
               [{"sha": "2" * 40, "commit": {"message": "fix: two"}}]]
    monkeypatch.setattr("merge_message_gate.run_gh", lambda *args: json.dumps(payload))
    assert fetch_pr_commit_messages("o/r", 1) == [("1" * 40, "fix: one"), ("2" * 40, "fix: two")]


def test_merge_helper_uses_explicit_message_and_head_guard(monkeypatch):
    calls = []
    monkeypatch.setattr("merge_message_gate.fetch_pr", lambda repo, pr: {
        "state": "open", "draft": False, "head": {"sha": HEAD},
    })
    monkeypatch.setattr("merge_message_gate.fetch_pr_commit_messages", lambda repo, pr: [("b" * 40, "fix: bounded change")])
    monkeypatch.setattr("merge_message_gate.run_gh", lambda *args: calls.append(args) or "merged")
    assert merge_pr("o/r", 7, "fix: reviewed", "body", b"evidence", False) == "merged"
    argv = calls[0]
    assert argv[:3] == ("pr", "merge", "7")
    assert "--squash" in argv and "--subject" in argv and "--body-file" in argv
    assert "--match-head-commit" in argv and HEAD in argv
    assert "--admin" not in argv and "--auto" not in argv


def test_merge_helper_rejects_intermediate_evidence(monkeypatch):
    monkeypatch.setattr("merge_message_gate.fetch_pr", lambda repo, pr: {
        "state": "open", "draft": False, "head": {"sha": HEAD},
    })
    monkeypatch.setattr("merge_message_gate.fetch_pr_commit_messages", lambda repo, pr: [("b" * 40, "13/13 tests green")])
    with pytest.raises(GateError, match="intermediate commit evidence"):
        merge_pr("o/r", 7, "fix: reviewed", "body", b"evidence", False)
