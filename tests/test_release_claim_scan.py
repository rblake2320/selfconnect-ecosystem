"""Tests for scripts/release_claim_scan.py — the release title/body claim gate."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from release_claim_scan import (  # noqa: E402
    allowlist_verdict, find_claims, has_bounded_notice, scan_release,
)

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "release_claim_scan.py"

NOTICE = (
    "> **[2026-07-16] Claim correction (bounded, dated).** Statements below are "
    "retracted as unsupported. Maintained boundary: SECURITY.md and PARKED.md.\n\n---\n\n"
)
OVERCLAIM_BODY = (
    "All changes are production-ready and comply with IL4/5/6/7 requirements "
    "(NIST SP 800-53 High, FIPS 140-2/3, zero-trust architecture)."
)


def allow(repo, tag, body, review_by="2099-01-01"):
    """Allowlist fixture with the exact sha of the given body."""
    return {(repo, tag): {
        "repo": repo, "tag": tag,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "corrected": "2026-07-16", "review_by": review_by, "reason": "test",
    }}


def test_clean_release_passes():
    r = scan_release({"tag_name": "v1.0", "name": "v1.0", "body": "Bug fixes and tests."})
    assert r["status"] == "clean"


def test_overclaim_title_always_fails_even_with_notice():
    r = scan_release({
        "tag_name": "v0.2.0",
        "name": "v0.2.0 — Security Release (IL4-7 Hardening)",
        "body": NOTICE + OVERCLAIM_BODY,
    })
    assert r["status"] == "fail"
    assert "title" in r["reason"]


def test_overclaim_body_without_notice_fails():
    r = scan_release({"tag_name": "v0.2.0", "name": "v0.2.0", "body": OVERCLAIM_BODY})
    assert r["status"] == "fail"
    labels = {h["label"] for h in r["body_hits"]}
    assert any("Impact Level" in l for l in labels)
    assert any("production-ready" in l for l in labels)


def test_corrected_release_with_bounded_notice_passes():
    body = NOTICE + OVERCLAIM_BODY
    r = scan_release({"tag_name": "v0.2.0", "name": "v0.2.0 — Security Release", "body": body},
                     repo="o/r", allowlist=allow("o/r", "v0.2.0", body))
    assert r["status"] == "bounded"


def test_production_release_label_detected():
    r = scan_release({"tag_name": "v1.0.0", "name": "v1.0.0 — Production Release", "body": ""})
    assert r["status"] == "fail"


def test_notice_requires_all_markers():
    assert not has_bounded_notice("Claim correction only, no retraction word")
    assert not has_bounded_notice("retracted, but no correction marker or link")
    assert has_bounded_notice(NOTICE)


def test_undated_notice_is_rejected():
    undated = ("> **Claim correction (bounded).** Statements below are retracted "
               "as unsupported. See SECURITY.md and PARKED.md.\n\n---\n\n")
    assert not has_bounded_notice(undated)
    r = scan_release({"tag_name": "v1", "name": "v1", "body": undated + OVERCLAIM_BODY})
    assert r["status"] == "fail"


def test_notice_after_claim_bypass_fails():
    body = OVERCLAIM_BODY + "\n\n" + NOTICE  # marker appended AFTER the claims
    r = scan_release({"tag_name": "v1", "name": "v1", "body": body})
    assert r["status"] == "fail"


def test_split_marker_date_after_claim_bypass_fails():
    # Fake marker before the claim; retraction/date/link scattered after it.
    body = ("Claim correction pending.\n\n" + OVERCLAIM_BODY +
            "\n\nretracted 2026-07-16, see SECURITY.md and PARKED.md")
    r = scan_release({"tag_name": "v1", "name": "v1", "body": body})
    assert r["status"] == "fail"
    assert "bypass" in r["reason"] or "no valid" in r["reason"]


def test_all_elements_before_claim_passes():
    body = NOTICE + OVERCLAIM_BODY
    r = scan_release({"tag_name": "v1", "name": "v1", "body": body},
                     repo="o/r", allowlist=allow("o/r", "v1", body))
    assert r["status"] == "bounded"


def test_valid_notice_without_allowlist_entry_fails():
    body = NOTICE + OVERCLAIM_BODY
    r = scan_release({"tag_name": "v1", "name": "v1", "body": body}, repo="o/r", allowlist={})
    assert r["status"] == "fail"
    assert "allowlist" in r["reason"]


def test_body_edited_after_allowlist_review_fails():
    body = NOTICE + OVERCLAIM_BODY
    al = allow("o/r", "v1", body)
    tampered = body + "\n\nNEW: also production-ready for IL4-7 workloads."
    r = scan_release({"tag_name": "v1", "name": "v1", "body": tampered}, repo="o/r", allowlist=al)
    assert r["status"] == "fail"
    assert "sha256 mismatch" in r["reason"]


def test_expired_allowlist_exception_fails():
    body = NOTICE + OVERCLAIM_BODY
    al = allow("o/r", "v1", body, review_by="2026-01-01")
    r = scan_release({"tag_name": "v1", "name": "v1", "body": body}, repo="o/r", allowlist=al)
    assert r["status"] == "fail"
    assert "expired" in r["reason"]


def test_allowlist_verdict_helper_dates():
    entry = {"body_sha256": hashlib.sha256(b"x").hexdigest(), "review_by": "2026-06-01"}
    ok, _ = allowlist_verdict(entry, "x", today=datetime.date(2026, 5, 31))
    assert ok
    ok, reason = allowlist_verdict(entry, "x", today=datetime.date(2026, 6, 2))
    assert not ok and "expired" in reason


def test_find_claims_is_case_insensitive():
    assert find_claims("this is PRODUCTION-READY software")
    assert find_claims("Comply With il4/5/6 requirements")


def test_cli_json_file_mode(tmp_path):
    data = {
        "owner/clean": [{"tag_name": "v1", "name": "v1", "body": "fixes"}],
        "owner/dirty": [{"tag_name": "v2", "name": "v2 Production Release", "body": ""}],
    }
    f = tmp_path / "fixtures.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPT), "--json-file", str(f)],
                          capture_output=True, text=True)
    assert proc.returncode == 1
    assert "FAIL owner/dirty@v2" in proc.stdout
    assert "OK  owner/clean@v1" in proc.stdout


def test_cli_no_input_errors():
    proc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert proc.returncode == 2
