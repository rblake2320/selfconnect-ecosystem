"""Tests for scripts/release_claim_scan.py — the release title/body claim gate."""
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from release_claim_scan import find_claims, has_bounded_notice, scan_release  # noqa: E402

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "release_claim_scan.py"

NOTICE = (
    "> **[2026-07-16] Claim correction (bounded, dated).** Statements below are "
    "retracted as unsupported. Maintained boundary: SECURITY.md and PARKED.md.\n\n---\n\n"
)
OVERCLAIM_BODY = (
    "All changes are production-ready and comply with IL4/5/6/7 requirements "
    "(NIST SP 800-53 High, FIPS 140-2/3, zero-trust architecture)."
)


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
    r = scan_release({"tag_name": "v0.2.0", "name": "v0.2.0 — Security Release",
                      "body": NOTICE + OVERCLAIM_BODY})
    assert r["status"] == "bounded"


def test_production_release_label_detected():
    r = scan_release({"tag_name": "v1.0.0", "name": "v1.0.0 — Production Release", "body": ""})
    assert r["status"] == "fail"


def test_notice_requires_all_markers():
    assert not has_bounded_notice("Claim correction only, no retraction word")
    assert not has_bounded_notice("retracted, but no correction marker or link")
    assert has_bounded_notice(NOTICE)


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
