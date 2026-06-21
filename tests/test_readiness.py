import importlib.util
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
READINESS_PATH = ROOT / "scripts" / "readiness.py"

spec = importlib.util.spec_from_file_location("readiness", READINESS_PATH)
readiness = importlib.util.module_from_spec(spec)
sys.modules["readiness"] = readiness
assert spec.loader is not None
spec.loader.exec_module(readiness)


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

    def test_markdown_includes_external_gate_trackers(self) -> None:
        report = {
            "ok": False,
            "pka_root": "C:/repo",
            "checks": {
                "repos": {"ok": True, "repos": [{"ok": True}] * 9},
                "gemini": {"ok": False, "status": "provider_auth_required", "gemini_version": "0.46.0"},
                "tpm": {"ok": False, "probe": {"error": "NCryptCreateClaim -> 0x80090026"}},
                "msi_workflow": {"ok": True, "latest": {"databaseId": 27897466199, "conclusion": "success"}},
                "signing_secrets": {
                    "ok": False,
                    "present": {
                        "WINDOWS_SIGNING_CERT_BASE64": False,
                        "WINDOWS_SIGNING_CERT_PASSWORD": False,
                    },
                },
            },
        }

        markdown = readiness.emit_markdown(report)

        self.assertIn("| Gate | Status | Detail | Tracker |", markdown)
        self.assertIn(readiness.ISSUES["gemini"], markdown)
        self.assertIn(readiness.ISSUES["tpm"], markdown)
        self.assertIn(readiness.ISSUES["signing_secrets"], markdown)
        self.assertIn("9/9 repos clean", markdown)

    def test_collect_report_carries_issue_links(self) -> None:
        with patch.object(readiness, "check_repos", return_value={"ok": True, "repos": []}), patch.object(
            readiness, "check_gemini", return_value={"ok": False}
        ), patch.object(readiness, "check_tpm", return_value={"ok": False}), patch.object(
            readiness, "check_msi_workflow", return_value={"ok": True}
        ), patch.object(readiness, "check_signing_secrets", return_value={"ok": False}):
            report = readiness.collect()

        self.assertFalse(report["ok"])
        self.assertEqual(report["issues"], readiness.ISSUES)

    def test_main_fail_on_blockers_exit_code(self) -> None:
        fake_report = {
            "ok": False,
            "pka_root": "C:/repo",
            "checks": {
                "repos": {"ok": True, "repos": [{"ok": True}]},
                "gemini": {"ok": False, "status": "provider_auth_required", "gemini_version": "0.46.0"},
                "tpm": {"ok": False, "probe": {"error": "x"}},
                "msi_workflow": {"ok": True, "latest": {"databaseId": 1, "conclusion": "success"}},
                "signing_secrets": {"ok": False, "present": {}},
            },
        }

        with patch.object(readiness, "collect", return_value=fake_report), patch.object(
            sys, "argv", ["readiness.py", "--markdown", "--fail-on-blockers"]
        ), patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(readiness.main(), 2)


if __name__ == "__main__":
    unittest.main()
