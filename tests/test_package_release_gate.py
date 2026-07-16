"""Tests for the Python package source and artifact release gate."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import pathlib
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from package_release_gate import (  # noqa: E402
    claim_hits,
    inspect_wheel,
    safe_member_name,
    source_version,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "packages" / "selfconnect-py"


def test_repository_source_contract_version():
    assert source_version(PACKAGE_DIR) == "1.1.1"


def test_prohibited_claim_examples_are_detected():
    samples = [
        "IL7 deployment",
        "immutable audit trail",
        "compliance for every framework",
        "Every LLM call",
        "Every tool invocation",
        "hard budget enforcement",
        "hardware-bound identity",
        "replay-proof",
        "suitable for compliance export",
    ]
    for sample in samples:
        assert claim_hits("fixture", sample), sample


def test_bounded_language_is_not_rejected():
    text = (
        "The client retrieves server-reported retained event hash-chain data. "
        "Authorization and regulatory conclusions are deployment-specific."
    )
    assert claim_hits("fixture", text) == []


def test_archive_member_path_validation():
    assert safe_member_name("selfconnect-1.1.1/selfconnect/client.py")
    assert not safe_member_name("../escape")
    assert not safe_member_name("/absolute")


def make_wheel(path: pathlib.Path, *, tamper: bool = False, unrecorded: bool = False):
    files = {
        "selfconnect/_version.py": b'__version__ = "1.1.1"\n',
        "selfconnect-1.1.1.dist-info/METADATA": (
            b"Metadata-Version: 2.4\nName: selfconnect\nVersion: 1.1.1\n\n"
        ),
        "selfconnect-1.1.1.dist-info/WHEEL": (
            b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
    }
    rows = []
    for name, data in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        rows.append([name, f"sha256={digest}", str(len(data))])
    record = "selfconnect-1.1.1.dist-info/RECORD"
    rows.append([record, "", ""])
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    files[record] = buffer.getvalue().encode()
    if tamper:
        files["selfconnect/_version.py"] = b'__version__ = "9.9.9"\n'
    if unrecorded:
        files["selfconnect/payload.bin"] = b"not listed in RECORD"
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)


def test_wheel_record_integrity_passes(tmp_path):
    wheel = tmp_path / "selfconnect-1.1.1-py3-none-any.whl"
    make_wheel(wheel)
    assert inspect_wheel(wheel, "1.1.1") == []


def test_wheel_record_tampering_fails(tmp_path):
    wheel = tmp_path / "selfconnect-1.1.1-py3-none-any.whl"
    make_wheel(wheel, tamper=True)
    errors = inspect_wheel(wheel, "1.1.1")
    assert any("digest mismatch" in error for error in errors)
    assert any("runtime version mismatch" in error for error in errors)


def test_unrecorded_wheel_payload_fails(tmp_path):
    wheel = tmp_path / "selfconnect-1.1.1-py3-none-any.whl"
    make_wheel(wheel, unrecorded=True)
    errors = inspect_wheel(wheel, "1.1.1")
    assert any("unexpected non-Python package payload" in error for error in errors)
    assert any("member missing from RECORD" in error for error in errors)
