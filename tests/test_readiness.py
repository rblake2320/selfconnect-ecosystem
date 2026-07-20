import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = ROOT / "scripts" / "readiness.py"

spec = importlib.util.spec_from_file_location("readiness", READINESS_PATH)
readiness = importlib.util.module_from_spec(spec)
sys.modules["readiness"] = readiness
assert spec.loader is not None
spec.loader.exec_module(readiness)


NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
HEAD = "a" * 40
SIGNER = "B" * 64
REPO_SPEC = readiness.RepoSpec(
    "repo",
    "https://github.com/rblake2320/repo",
    "main",
)


def good_report(*, ok: bool = True) -> dict:
    return {
        "schema": "selfconnect.ecosystem_readiness.v2",
        "evaluated_at": NOW.isoformat(),
        "max_evidence_age_hours": 168.0,
        "ok": ok,
        "pka_root": "C:/repo",
        "issues": readiness.ISSUES,
        "checks": {
            "repos": {
                "ok": ok,
                "status": "ready" if ok else "repo_set_not_current",
                "repos": [{"ok": ok}] * 9,
            },
            "gemini": {
                "ok": ok,
                "status": "ready" if ok else "provider_probe_failed",
                "gemini_version": "1.0.0",
            },
            "tpm": {
                "ok": ok,
                "status": "ready" if ok else "unsupported_on_this_host",
                "probe": {"supported": ok},
            },
            "msi_workflow": {
                "ok": ok,
                "status": "ready" if ok else "workflow_evidence_stale",
                "latest": {"databaseId": 1},
            },
            "signing_secrets": {
                "ok": ok,
                "status": "configured" if ok else "missing_signing_secrets",
                "present": {},
            },
        },
    }


def write_msi_artifact(
    directory: Path,
    *,
    signed: bool = True,
    generated: datetime = NOW,
    evidence_sha: str | None = None,
) -> None:
    payload = b"real-msi-test-payload"
    msi = directory / "selfconnect-enterprise-1.2.3.msi"
    msi.write_bytes(payload)
    actual_sha = readiness.sha256_file(msi)
    evidence = {
        "artifact": msi.name,
        "size_bytes": len(payload),
        "sha256": evidence_sha or actual_sha,
        "workflow": readiness.MSI_WORKFLOW,
        "run_id": "123",
        "run_attempt": "1",
        "git_sha": HEAD,
        "ref": "refs/heads/master",
        "generated_utc": generated.isoformat().replace("+00:00", "Z"),
        "signed": signed,
    }
    (directory / "msi-evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
    (directory / "msi-sha256.txt").write_text(
        f"{actual_sha} *{msi.name}\n",
        encoding="ascii",
    )


class ReadinessContractTests(unittest.TestCase):
    def test_primary_repo_coverage_matches_status_table(self) -> None:
        expected = {
            "selfconnect",
            "selfconnect-enterprise",
            "selfconnect-ecosystem",
            "selfconnect-terminal",
            "selfconnect-linux",
            "selfconnect-alt",
            "bpc-protocol",
            "tsk-protocol",
            "patent-portfolio",
        }
        self.assertEqual(set(readiness.REPOS), expected)

    def test_parse_secret_names_uses_first_column(self) -> None:
        output = "WINDOWS_SIGNING_CERT_BASE64 2026-06-21\nWINDOWS_SIGNING_CERT_PASSWORD 2026-06-21\n"
        self.assertEqual(
            readiness.parse_secret_names(output),
            {"WINDOWS_SIGNING_CERT_BASE64", "WINDOWS_SIGNING_CERT_PASSWORD"},
        )

    def test_env_presence_reports_scopes_without_values(self) -> None:
        with patch.dict(os.environ, {"GEMINI_API_KEY": "process-secret"}, clear=False), patch.object(
            readiness,
            "windows_registry_env",
            side_effect=lambda name, scope: f"{scope.lower()}-secret" if name == "GEMINI_API_KEY" else "",
        ):
            report = readiness.env_presence("GEMINI_API_KEY")

        self.assertEqual(report["process"], {"present": True, "length": len("process-secret")})
        self.assertEqual(report["user"], {"present": True, "length": len("user-secret")})
        self.assertEqual(report["machine"], {"present": True, "length": len("machine-secret")})

    def test_first_env_value_falls_back_to_user_then_machine(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(
            readiness,
            "windows_registry_env",
            side_effect=lambda name, scope: "user-secret" if scope == "User" else "machine-secret",
        ):
            self.assertEqual(readiness.first_env_value("GEMINI_API_KEY"), "user-secret")

    def test_git_repo_status_compares_live_remote_head(self) -> None:
        results = [
            readiness.CmdResult(0, "", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, "main", ""),
            readiness.CmdResult(0, "origin", ""),
            readiness.CmdResult(0, "refs/heads/main", ""),
            readiness.CmdResult(0, "https://github.com/rblake2320/repo.git", ""),
            readiness.CmdResult(0, f"{HEAD}\trefs/heads/main", ""),
        ]
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            readiness, "run_cmd", side_effect=results
        ):
            report = readiness.git_repo_status("repo", REPO_SPEC, Path(temp_dir))
        self.assertTrue(report["ok"])
        self.assertEqual(report["remote_head"], HEAD)

    def test_git_repo_status_rejects_stale_cached_upstream(self) -> None:
        results = [
            readiness.CmdResult(0, "", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, "main", ""),
            readiness.CmdResult(0, "origin", ""),
            readiness.CmdResult(0, "refs/heads/main", ""),
            readiness.CmdResult(0, "git@github.com:rblake2320/repo.git", ""),
            readiness.CmdResult(0, f"{'b' * 40}\trefs/heads/main", ""),
        ]
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            readiness, "run_cmd", side_effect=results
        ):
            report = readiness.git_repo_status("repo", REPO_SPEC, Path(temp_dir))
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "remote_drift")

    def test_git_repo_status_rejects_unavailable_remote(self) -> None:
        results = [
            readiness.CmdResult(0, "", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, "main", ""),
            readiness.CmdResult(0, "origin", ""),
            readiness.CmdResult(0, "refs/heads/main", ""),
            readiness.CmdResult(0, "https://github.com/rblake2320/repo", ""),
            readiness.CmdResult(2, "", "unavailable"),
        ]
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            readiness, "run_cmd", side_effect=results
        ):
            report = readiness.git_repo_status("repo", REPO_SPEC, Path(temp_dir))
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "remote_head_unavailable")

    def test_git_repo_status_rejects_fork_remote(self) -> None:
        results = [
            readiness.CmdResult(0, "", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, "main", ""),
            readiness.CmdResult(0, "origin", ""),
            readiness.CmdResult(0, "refs/heads/main", ""),
            readiness.CmdResult(0, "https://github.com/example/repo", ""),
        ]
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            readiness, "run_cmd", side_effect=results
        ):
            report = readiness.git_repo_status("repo", REPO_SPEC, Path(temp_dir))
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "wrong_remote_identity")

    def test_git_repo_status_rejects_non_default_branch(self) -> None:
        results = [
            readiness.CmdResult(0, "", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, "feature/unreleased", ""),
        ]
        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            readiness, "run_cmd", side_effect=results
        ):
            report = readiness.git_repo_status("repo", REPO_SPEC, Path(temp_dir))
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "wrong_branch")

    def test_gemini_requires_live_exact_nonce_probe(self) -> None:
        def fake_command(args, **_kwargs):
            if "--version" in args:
                return readiness.CmdResult(0, "1.0.0", "")
            return readiness.CmdResult(1, "", "auth rejected")

        with patch.object(
            readiness.shutil,
            "which",
            side_effect=lambda name: f"C:/{name}.exe",
        ), patch.object(readiness, "run_cmd", side_effect=fake_command), patch.object(
            readiness, "first_env_value", side_effect=lambda name: "configured" if name == "GEMINI_API_KEY" else ""
        ), patch.object(readiness, "env_presence", return_value={}), patch.object(
            readiness, "default_adc_paths", return_value=[]
        ):
            report = readiness.check_gemini()
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "provider_probe_failed")

    def test_empty_adc_file_does_not_pass_failed_provider_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            adc = Path(temp_dir) / "adc.json"
            adc.write_text("", encoding="utf-8")

            def fake_command(args, **_kwargs):
                if "--version" in args:
                    return readiness.CmdResult(0, "1.0.0", "")
                return readiness.CmdResult(1, "", "invalid ADC")

            with patch.object(
                readiness.shutil,
                "which",
                side_effect=lambda name: f"C:/{name}.exe",
            ), patch.object(readiness, "run_cmd", side_effect=fake_command), patch.object(
                readiness, "first_env_value", return_value=""
            ), patch.object(readiness, "env_presence", return_value={}), patch.object(
                readiness, "default_adc_paths", return_value=[adc]
            ):
                report = readiness.check_gemini()
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "provider_probe_failed")

    def test_gemini_exact_nonce_response_passes(self) -> None:
        def fake_command(args, **_kwargs):
            if "--version" in args:
                return readiness.CmdResult(0, "1.0.0", "")
            prompt = args[args.index("-p") + 1]
            nonce = prompt.rsplit(": ", 1)[1]
            return readiness.CmdResult(0, nonce, "")

        with patch.object(
            readiness.shutil,
            "which",
            side_effect=lambda name: f"C:/{name}.exe",
        ), patch.object(readiness, "run_cmd", side_effect=fake_command), patch.object(
            readiness, "first_env_value", side_effect=lambda name: "configured" if name == "GOOGLE_API_KEY" else ""
        ), patch.object(readiness, "env_presence", return_value={}), patch.object(
            readiness, "default_adc_paths", return_value=[]
        ):
            report = readiness.check_gemini()
        self.assertTrue(report["ok"])
        self.assertEqual(report["probe"], "exact_nonce_returned")

    def test_tpm_truthy_string_does_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "selfconnect-enterprise").mkdir()
            with patch.dict(
                readiness.os.environ,
                {"READINESS_TPM_PUBLIC_KEY_SHA256": "a" * 64},
            ), patch.object(
                readiness,
                "run_cmd",
                return_value=readiness.CmdResult(
                    0,
                    json.dumps({"supported": "true", "claim_size": 10}),
                    "",
                ),
            ):
                report = readiness.check_tpm(Path(temp_dir))
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "attestation_verification_failed")

    def test_tpm_requires_independent_public_key_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            readiness.os.environ,
            {"READINESS_TPM_PUBLIC_KEY_SHA256": ""},
        ):
            (Path(temp_dir) / "selfconnect-enterprise").mkdir()
            report = readiness.check_tpm(Path(temp_dir))
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "missing_or_invalid_public_key_pin")

    def test_tpm_accepts_only_complete_verified_pinned_evidence(self) -> None:
        key_digest = "a" * 64
        evidence = {
            "supported": True,
            "verified": True,
            "platform_key_bound": True,
            "identity_key_bound": False,
            "manufacturer_chain_verified": False,
            "replay_checked": True,
            "claim_size": 1187,
            "claim_sha256": "b" * 64,
            "nonce_sha256": "c" * 64,
            "public_key_sha256": key_digest,
            "pcr_mask": 0xFFFFFF,
            "pcr_algorithm": 11,
            "pcr_values_sha256": "d" * 64,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "selfconnect-enterprise").mkdir()

            def fake_run(*args, **kwargs):
                self.assertEqual(
                    kwargs["env"]["SELFCONNECT_TPM_PUBLIC_KEY_SHA256"],
                    key_digest,
                )
                return readiness.CmdResult(0, json.dumps(evidence), "")

            with patch.dict(
                readiness.os.environ,
                {"READINESS_TPM_PUBLIC_KEY_SHA256": key_digest},
            ), patch.object(readiness, "run_cmd", side_effect=fake_run):
                report = readiness.check_tpm(Path(temp_dir))
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "ready")
        self.assertFalse(report["probe"]["manufacturer_chain_verified"])

    def test_tpm_rejects_key_substitution_and_incomplete_evidence(self) -> None:
        key_digest = "a" * 64
        evidence = {
            "supported": True,
            "verified": True,
            "platform_key_bound": True,
            "replay_checked": True,
            "claim_size": 1187,
            "claim_sha256": "b" * 64,
            "nonce_sha256": "c" * 64,
            "public_key_sha256": "e" * 64,
            "pcr_mask": 0xFFFFFF,
            "pcr_algorithm": 11,
            "pcr_values_sha256": "d" * 64,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "selfconnect-enterprise").mkdir()
            with patch.dict(
                readiness.os.environ,
                {"READINESS_TPM_PUBLIC_KEY_SHA256": key_digest},
            ), patch.object(
                readiness,
                "run_cmd",
                return_value=readiness.CmdResult(0, json.dumps(evidence), ""),
            ):
                substituted = readiness.check_tpm(Path(temp_dir))
                evidence["public_key_sha256"] = key_digest
                del evidence["nonce_sha256"]
                incomplete = readiness.check_tpm(Path(temp_dir))
        self.assertFalse(substituted["ok"])
        self.assertFalse(incomplete["ok"])

    def test_authenticode_requires_valid_status_pinned_signer_and_timestamp(self) -> None:
        evidence = {
            "status": "Valid",
            "signer_sha256": SIGNER,
            "signer_subject": "CN=SelfConnect Test",
            "timestamped": True,
            "timestamp_signer_sha256": "C" * 64,
        }
        with patch.object(readiness.sys, "platform", "win32"), patch.object(
            readiness.shutil, "which", return_value="powershell.exe"
        ), patch.object(
            readiness,
            "run_cmd",
            return_value=readiness.CmdResult(0, json.dumps(evidence), ""),
        ):
            report = readiness.verify_authenticode(
                Path("artifact.msi"),
                expected_signer_sha256=SIGNER,
            )
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "valid")
        self.assertTrue(report["timestamped"])

    def test_authenticode_rejects_signer_mismatch(self) -> None:
        evidence = {
            "status": "Valid",
            "signer_sha256": "D" * 64,
            "timestamped": True,
            "timestamp_signer_sha256": "C" * 64,
        }
        with patch.object(readiness.sys, "platform", "win32"), patch.object(
            readiness.shutil, "which", return_value="powershell.exe"
        ), patch.object(
            readiness,
            "run_cmd",
            return_value=readiness.CmdResult(0, json.dumps(evidence), ""),
        ):
            report = readiness.verify_authenticode(
                Path("artifact.msi"),
                expected_signer_sha256=SIGNER,
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "authenticode_signer_mismatch")

    def test_authenticode_rejects_missing_timestamp(self) -> None:
        evidence = {
            "status": "Valid",
            "signer_sha256": SIGNER,
            "timestamped": False,
            "timestamp_signer_sha256": None,
        }
        with patch.object(readiness.sys, "platform", "win32"), patch.object(
            readiness.shutil, "which", return_value="powershell.exe"
        ), patch.object(
            readiness,
            "run_cmd",
            return_value=readiness.CmdResult(0, json.dumps(evidence), ""),
        ):
            report = readiness.verify_authenticode(
                Path("artifact.msi"),
                expected_signer_sha256=SIGNER,
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "authenticode_timestamp_missing")

    def test_authenticode_rejects_invalid_signer_policy_before_probe(self) -> None:
        with patch.object(readiness, "run_cmd") as command:
            report = readiness.verify_authenticode(
                Path("artifact.msi"),
                expected_signer_sha256="not-a-thumbprint",
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "signer_policy_invalid")
        command.assert_not_called()

    def test_validate_msi_artifact_accepts_current_signed_exact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            write_msi_artifact(path)
            with patch.object(
                readiness,
                "verify_authenticode",
                return_value={
                    "ok": True,
                    "status": "valid",
                    "signer_sha256": SIGNER,
                    "timestamped": True,
                },
            ):
                report = readiness.validate_msi_artifact(
                    path,
                    run_id=123,
                    head_sha=HEAD,
                    branch="master",
                    now=NOW,
                    max_age=timedelta(hours=168),
                    expected_signer_sha256=SIGNER,
                )
        self.assertTrue(report["ok"])
        self.assertEqual(report["signature"]["signer_sha256"], SIGNER)

    def test_validate_msi_artifact_rejects_unsigned_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            write_msi_artifact(path, signed=False)
            report = readiness.validate_msi_artifact(
                path,
                run_id=123,
                head_sha=HEAD,
                branch="master",
                now=NOW,
                max_age=timedelta(hours=168),
                expected_signer_sha256=SIGNER,
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "artifact_evidence_mismatch")

    def test_validate_msi_artifact_rejects_tampered_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            write_msi_artifact(path, evidence_sha="0" * 64)
            report = readiness.validate_msi_artifact(
                path,
                run_id=123,
                head_sha=HEAD,
                branch="master",
                now=NOW,
                max_age=timedelta(hours=168),
                expected_signer_sha256=SIGNER,
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "artifact_evidence_mismatch")

    def test_validate_msi_artifact_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            write_msi_artifact(path)
            evidence_path = path / "msi-evidence.json"
            original = evidence_path.read_text(encoding="utf-8").rstrip("}")
            evidence_path.write_text(
                original + ', "signed": false}',
                encoding="utf-8",
            )
            report = readiness.validate_msi_artifact(
                path,
                run_id=123,
                head_sha=HEAD,
                branch="master",
                now=NOW,
                max_age=timedelta(hours=168),
                expected_signer_sha256=SIGNER,
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "artifact_evidence_invalid")

    def test_validate_msi_artifact_rejects_stale_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            write_msi_artifact(path, generated=NOW - timedelta(days=8))
            report = readiness.validate_msi_artifact(
                path,
                run_id=123,
                head_sha=HEAD,
                branch="master",
                now=NOW,
                max_age=timedelta(hours=168),
                expected_signer_sha256=SIGNER,
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "artifact_evidence_stale")

    def test_validate_msi_artifact_rejects_self_attested_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir)
            write_msi_artifact(path, signed=True)
            with patch.object(
                readiness,
                "verify_authenticode",
                return_value={"ok": False, "status": "authenticode_invalid"},
            ):
                report = readiness.validate_msi_artifact(
                    path,
                    run_id=123,
                    head_sha=HEAD,
                    branch="master",
                    now=NOW,
                    max_age=timedelta(hours=168),
                    expected_signer_sha256=SIGNER,
                )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "authenticode_invalid")

    def test_msi_workflow_rejects_stale_success_without_download(self) -> None:
        old = (NOW - timedelta(days=8)).isoformat().replace("+00:00", "Z")
        run = [{
            "databaseId": 123,
            "status": "completed",
            "conclusion": "success",
            "headSha": HEAD,
            "headBranch": "master",
            "createdAt": old,
        }]
        results = [
            readiness.CmdResult(0, "master", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, json.dumps(run), ""),
        ]
        with patch.object(readiness, "first_env_value", return_value=SIGNER), patch.object(
            readiness.shutil, "which", return_value="gh"
        ), patch.object(readiness, "run_cmd", side_effect=results):
            report = readiness.check_msi_workflow(now=NOW)
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "workflow_evidence_stale")

    def test_msi_workflow_rejects_success_for_old_head(self) -> None:
        run = [{
            "databaseId": 123,
            "status": "completed",
            "conclusion": "success",
            "headSha": "b" * 40,
            "headBranch": "master",
            "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        }]
        results = [
            readiness.CmdResult(0, "master", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, json.dumps(run), ""),
        ]
        with patch.object(readiness, "first_env_value", return_value=SIGNER), patch.object(
            readiness.shutil, "which", return_value="gh"
        ), patch.object(readiness, "run_cmd", side_effect=results):
            report = readiness.check_msi_workflow(now=NOW)
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "workflow_not_current_success")

    def test_msi_workflow_rejects_unavailable_artifact(self) -> None:
        run = [{
            "databaseId": 123,
            "status": "completed",
            "conclusion": "success",
            "headSha": HEAD,
            "headBranch": "master",
            "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        }]
        results = [
            readiness.CmdResult(0, "master", ""),
            readiness.CmdResult(0, HEAD, ""),
            readiness.CmdResult(0, json.dumps(run), ""),
            readiness.CmdResult(1, "", "artifact expired"),
        ]
        with patch.object(readiness, "first_env_value", return_value=SIGNER), patch.object(
            readiness.shutil, "which", return_value="gh"
        ), patch.object(readiness, "run_cmd", side_effect=results):
            report = readiness.check_msi_workflow(now=NOW)
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "workflow_artifact_unavailable")

    def test_required_check_rejects_truthy_non_boolean_ok(self) -> None:
        report = readiness.run_required_check(
            "adversarial",
            lambda: {"ok": "yes", "status": "ready"},
            expected_status="ready",
        )
        self.assertFalse(report["ok"])

    def test_required_check_converts_exception_to_failure_without_message(self) -> None:
        report = readiness.run_required_check(
            "adversarial",
            lambda: (_ for _ in ()).throw(RuntimeError("secret detail")),
            expected_status="ready",
        )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "check_exception")
        self.assertNotIn("secret detail", json.dumps(report))

    def test_required_check_rejects_contradictory_success_status(self) -> None:
        report = readiness.run_required_check(
            "adversarial",
            lambda: {"ok": True, "status": "unavailable"},
            expected_status="ready",
        )
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "unexpected_success_status")
        self.assertEqual(report["observed_status"], "unavailable")

    def test_markdown_never_renders_unavailable_tpm_as_na(self) -> None:
        report = good_report(ok=False)
        markdown = readiness.emit_markdown(report)
        self.assertIn("| TPM platform attestation | FAIL |", markdown)
        self.assertNotIn("| TPM platform attestation | NA |", markdown)

    def test_markdown_report_only_is_explicitly_not_evidence(self) -> None:
        markdown = readiness.emit_markdown(good_report(ok=False), report_only=True)
        self.assertIn("REPORT ONLY - not readiness evidence", markdown)

    def test_markdown_escapes_untrusted_probe_detail(self) -> None:
        report = good_report(ok=False)
        report["checks"]["tpm"]["probe"] = {"error": "bad|cell\ninjected"}
        markdown = readiness.emit_markdown(report)
        self.assertIn(r"bad\|cell injected", markdown)
        self.assertNotIn("|cell\n", markdown)

    def test_collect_requires_exact_boolean_success_from_every_check(self) -> None:
        with patch.object(
            readiness,
            "check_repos",
            return_value={"ok": True, "status": "ready", "repos": []},
        ), patch.object(
            readiness,
            "check_gemini",
            return_value={"ok": True, "status": "ready"},
        ), patch.object(
            readiness,
            "check_tpm",
            return_value={"ok": True, "status": "ready"},
        ), patch.object(
            readiness,
            "check_msi_workflow",
            return_value={"ok": True, "status": "ready"},
        ), patch.object(
            readiness,
            "check_signing_secrets",
            return_value={"ok": "true", "status": "configured"},
        ):
            report = readiness.collect(now=NOW)
        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["signing_secrets"]["ok"])

    def test_collect_does_not_execute_tpm_code_when_repositories_fail(self) -> None:
        with patch.object(
            readiness,
            "check_repos",
            return_value={"ok": False, "status": "repo_set_not_current", "repos": []},
        ), patch.object(readiness, "check_gemini", return_value={"ok": True, "status": "ready"}), patch.object(
            readiness, "check_tpm"
        ) as tpm, patch.object(
            readiness,
            "check_msi_workflow",
            return_value={"ok": True, "status": "ready"},
        ), patch.object(
            readiness,
            "check_signing_secrets",
            return_value={"ok": True, "status": "configured"},
        ):
            report = readiness.collect(now=NOW)
        tpm.assert_not_called()
        self.assertFalse(report["ok"])
        self.assertEqual(
            report["checks"]["tpm"]["status"],
            "repo_precondition_failed",
        )

    def test_signing_secret_names_do_not_override_missing_signed_artifact(self) -> None:
        with patch.object(
            readiness,
            "check_repos",
            return_value={"ok": True, "status": "ready", "repos": []},
        ), patch.object(
            readiness,
            "check_gemini",
            return_value={"ok": True, "status": "ready"},
        ), patch.object(
            readiness,
            "check_tpm",
            return_value={"ok": True, "status": "ready"},
        ), patch.object(
            readiness,
            "check_msi_workflow",
            return_value={"ok": False, "status": "workflow_artifact_unavailable"},
        ), patch.object(
            readiness,
            "check_signing_secrets",
            return_value={"ok": True, "status": "configured"},
        ):
            report = readiness.collect(now=NOW)
        self.assertFalse(report["ok"])
        self.assertTrue(report["checks"]["signing_secrets"]["ok"])
        self.assertFalse(report["checks"]["msi_workflow"]["ok"])

    def test_main_defaults_to_nonzero_when_any_gate_fails(self) -> None:
        with patch.object(readiness, "collect", return_value=good_report(ok=False)), patch.object(
            sys, "argv", ["readiness.py", "--markdown"]
        ), patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(readiness.main(), 2)

    def test_main_report_only_is_explicit_zero_exit_escape_hatch(self) -> None:
        output = io.StringIO()
        with patch.object(readiness, "collect", return_value=good_report(ok=False)), patch.object(
            sys, "argv", ["readiness.py", "--markdown", "--report-only"]
        ), patch("sys.stdout", new=output):
            self.assertEqual(readiness.main(), 0)
        self.assertIn("REPORT ONLY - not readiness evidence", output.getvalue())

    def test_main_rejects_evidence_age_above_policy_ceiling(self) -> None:
        with patch.object(
            sys,
            "argv",
            [
                "readiness.py",
                "--markdown",
                "--max-evidence-age-hours",
                str(readiness.MAX_EVIDENCE_AGE_HOURS + 1),
            ],
        ), patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                readiness.main()
        self.assertEqual(raised.exception.code, 2)

    def test_hosted_workflow_is_named_as_contract_not_readiness_evidence(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "readiness.yml").read_text(encoding="utf-8")
        self.assertIn("name: Readiness Gate Contract", workflow)
        self.assertIn("readiness:", workflow)
        self.assertIn("name: readiness", workflow)
        self.assertNotIn("Smoke-run readiness report", workflow)
        self.assertNotIn("continue-on-error", workflow)

    def test_live_workflow_invokes_default_fail_closed_checker(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "live-readiness.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("self-hosted", workflow)
        self.assertIn("python scripts\\readiness.py --json", workflow)
        self.assertIn("READINESS_PKA_ROOT", workflow)
        self.assertIn("READINESS_TPM_PUBLIC_KEY_SHA256", workflow)
        self.assertIn("READINESS_WINDOWS_SIGNER_SHA256", workflow)
        self.assertIn("READINESS_GH_TOKEN", workflow)
        self.assertIn("may tighten but never exceed 168", workflow)
        self.assertIn("environment: live-readiness", workflow)
        self.assertIn("refs/heads/main", workflow)
        self.assertNotIn("--report-only", workflow)
        self.assertNotIn("continue-on-error", workflow)


if __name__ == "__main__":
    unittest.main()
