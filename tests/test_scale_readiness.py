from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "scale_readiness", ROOT / "scripts" / "scale_readiness.py"
)
assert SPEC and SPEC.loader
scale = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scale)

NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
HEAD = "a" * 40
IDENTITY = {
    "remote_url": scale.CORE_REMOTE,
    "branch": scale.CORE_BRANCH,
    "head_sha": HEAD,
}


def source_result(agent_count: int) -> dict:
    providers = scale.RUNGS[agent_count]["provider_counts"]
    agents = []
    index = 0
    for provider, count in providers.items():
        for _ in range(count):
            agents.append(
                {
                    "provider": provider,
                    "role": f"agent-{index:02d}",
                    "nonce_hash": f"{index + 1:064x}",
                    "expected_hash": f"{index + 101:064x}",
                    "log_exact_ack": True,
                    "uia_exact_ack": False,
                    "status": "pass",
                    "diagnosis": "",
                }
            )
            index += 1
    return {
        "schema": scale.SOURCE_SCHEMA,
        "run_id": "SC_REAL5_20260717_120000",
        "verdict": "PASS",
        "agent_count": agent_count,
        "provider_counts": providers,
        "logical_simulation": False,
        "visible_windows": True,
        "completion_policy": "visible_window_plus_exact_ack_from_uia_or_provider_log",
        "failure_counters": {
            "missed_acks": 0,
            "visible_window_missing": 0,
            "uia_readback_failures": 0,
            "wrong_window_guard_failures": 0,
            "drift_or_narration_events": 0,
            "approval_stalls": 0,
            "wrong_ack_format": 0,
            "provider_auth_required": 0,
            "provider_quota_exceeded": 0,
            "provider_failures": {provider: 0 for provider in providers},
        },
        "agents": agents,
    }


def build_bundle(path: Path, *, generated_at: datetime = NOW) -> None:
    rungs = []
    for count in scale.RUNGS:
        evidence = scale.validate_source_result(source_result(count), count)
        evidence_path = path / f"rung-{count}.json"
        scale.write_json(evidence_path, evidence)
        rungs.append(
            {
                "agent_count": count,
                "provider_counts": scale.RUNGS[count]["provider_counts"],
                "file": evidence_path.name,
                "sha256": scale.sha256_file(evidence_path),
                "size_bytes": evidence_path.stat().st_size,
            }
        )
    scale.write_json(
        path / "manifest.json",
        {
            "schema": scale.SCHEMA,
            "generated_at": generated_at.isoformat(),
            "core": IDENTITY,
            "rungs": rungs,
        },
    )


class ScaleReadinessTests(unittest.TestCase):
    def assert_status(self, status: str, callback) -> None:
        with self.assertRaises(scale.ScaleReadinessError) as raised:
            callback()
        self.assertEqual(raised.exception.status, status)

    def test_valid_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            with patch.object(scale, "current_core_identity", return_value=IDENTITY):
                report = scale.validate_bundle(bundle, core_repo=Path("core"), now=NOW)
        self.assertTrue(report["ok"])
        self.assertEqual(report["rungs"], [10, 15, 20])

    def test_stale_bundle_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle, generated_at=NOW - timedelta(hours=169))
            with patch.object(scale, "current_core_identity", return_value=IDENTITY):
                self.assert_status(
                    "evidence_stale",
                    lambda: scale.validate_bundle(bundle, core_repo=Path("core"), now=NOW),
                )

    def test_wrong_current_head_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            other = {**IDENTITY, "head_sha": "b" * 40}
            with patch.object(scale, "current_core_identity", return_value=other):
                self.assert_status(
                    "evidence_wrong_core_head",
                    lambda: scale.validate_bundle(bundle, core_repo=Path("core"), now=NOW),
                )

    def test_missing_rung_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            (bundle / "rung-15.json").unlink()
            with patch.object(scale, "current_core_identity", return_value=IDENTITY):
                self.assert_status(
                    "rung_file_missing",
                    lambda: scale.validate_bundle(bundle, core_repo=Path("core"), now=NOW),
                )

    def test_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            (bundle / "rung-10.json").write_text("{}\n", encoding="utf-8")
            with patch.object(scale, "current_core_identity", return_value=IDENTITY):
                self.assert_status(
                    "rung_artifact_mismatch",
                    lambda: scale.validate_bundle(bundle, core_repo=Path("core"), now=NOW),
                )

    def test_quota_failed_result_fails(self) -> None:
        result = source_result(10)
        result["failure_counters"]["provider_quota_exceeded"] = 1
        self.assert_status(
            "provider_quota_exceeded",
            lambda: scale.validate_source_result(result, 10),
        )

    def test_forged_agent_count_fails(self) -> None:
        result = source_result(10)
        result["agents"].pop()
        self.assert_status(
            "agent_evidence_count_mismatch",
            lambda: scale.validate_source_result(result, 10),
        )

    def test_forged_provider_counts_fail(self) -> None:
        result = source_result(15)
        result["provider_counts"] = {"claude": 5, "codex": 4, "gemini": 6}
        self.assert_status(
            "provider_counts_mismatch",
            lambda: scale.validate_source_result(result, 15),
        )

    def test_missing_exact_ack_fails(self) -> None:
        result = source_result(20)
        result["agents"][0]["log_exact_ack"] = False
        self.assert_status(
            "exact_ack_missing",
            lambda: scale.validate_source_result(result, 20),
        )

    def test_duplicate_json_keys_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
            self.assert_status("evidence_json_invalid", lambda: scale.load_json(path))

    def test_sanitized_rung_rejects_wrong_schema(self) -> None:
        evidence = scale.validate_source_result(source_result(10), 10)
        evidence["schema"] = "attacker.schema"
        self.assert_status(
            "rung_schema_invalid",
            lambda: scale.validate_rung_evidence(evidence, 10),
        )

    def test_sanitized_rung_rejects_malformed_counters(self) -> None:
        evidence = scale.validate_source_result(source_result(10), 10)
        evidence["failure_counters"] = []
        self.assert_status(
            "failure_counters_invalid",
            lambda: scale.validate_rung_evidence(evidence, 10),
        )

    def test_manifest_count_cannot_hide_extra_or_duplicate_rung(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            manifest = scale.load_json(bundle / "manifest.json")
            manifest["rungs"][2] = dict(manifest["rungs"][1])
            scale.write_json(bundle / "manifest.json", manifest)
            with patch.object(scale, "current_core_identity", return_value=IDENTITY):
                self.assert_status(
                    "rung_manifest_invalid",
                    lambda: scale.validate_bundle(bundle, core_repo=Path("core"), now=NOW),
                )

    def test_report_contains_status_not_provider_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "report.json"
            scale.write_report(
                report,
                {"schema": scale.SCHEMA, "ok": False, "status": "rung_10_execution_failed"},
            )
            text = report.read_text(encoding="utf-8")
        self.assertIn("rung_10_execution_failed", text)
        self.assertNotIn("stdout", text)
        self.assertNotIn("stderr", text)

    def test_workflow_is_manual_self_hosted_and_fail_closed(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "scale-readiness.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("self-hosted", workflow)
        self.assertIn("selfconnect-readiness", workflow)
        self.assertIn("scale_readiness.py collect", workflow)
        self.assertIn("refs/heads/main", workflow)
        self.assertNotIn("continue-on-error", workflow)
        self.assertNotIn("--report-only", workflow)


if __name__ == "__main__":
    unittest.main()
