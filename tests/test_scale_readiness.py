from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
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

NOW = datetime(2026, 7, 17, 18, 0, tzinfo=timezone.utc)
CORE_HEAD = "a" * 40
ECOSYSTEM_SHA = "b" * 40
PRODUCER_RUN_ID = 123456


def digest(text: str) -> str:
    return scale.sha256_bytes(text.encode("utf-8"))


def argv_policy(provider: str) -> list[str]:
    return {
        "codex": ["exec", "--sandbox", "read-only", "--ephemeral", "--ignore-user-config"],
        "claude": [
            "--print",
            "--bare",
            "--safe-mode",
            "--permission-mode",
            "plan",
            "--tools",
            "",
        ],
        "gemini": ["--prompt", "--approval-mode", "plan", "--sandbox", "--admin-policy"],
    }[provider]


def agent(provider: str, ordinal: int, *, seed: str, observed_at: datetime) -> dict:
    role = f"real{provider}-{ordinal}"
    nonce = digest(f"nonce:{seed}:{provider}:{ordinal}")
    expected = scale.expected_ack(provider, role, nonce)
    claim = {
        "pre_guard_ok": True,
        "post_guard_ok": True,
        "spawn_alive_during_guard": True,
        "provider_in_spawn_tree": True,
        "same_session": True,
        "spawn_pid": 1000 + ordinal,
        "provider_pid": 2000 + ordinal,
        "window_pid": 1000 + ordinal,
        "session_id": 3,
        "class_name": "CASCADIA_HOSTING_WINDOW_CLASS",
        "exe_name": "WindowsTerminal.exe",
        "title_sha256": digest(f"SC_SCALE {provider} {role} {nonce}"),
        "process_tree_sha256": digest(f"tree:{seed}:{provider}:{ordinal}"),
        "provider_entrypoint_sha256": scale.PROVIDER_PINS[provider][
            "entrypoint_sha256"
        ],
    }
    return {
        "provider": provider,
        "role": role,
        "nonce": nonce,
        "nonce_sha256": digest(nonce),
        "expected_sha256": digest(expected),
        "observed_acks": {
            "process_stdout": {
                "sha256": digest(expected),
                "captured_at_utc": observed_at.isoformat(),
            },
            "uia_terminal": {
                "sha256": digest(expected),
                "captured_at_utc": (observed_at + timedelta(seconds=1)).isoformat(),
            },
        },
        "status": "pass",
        "provider_outcome": {"auth_failed": False, "quota_exceeded": False},
        "started_at_utc": (observed_at - timedelta(minutes=1)).isoformat(),
        "completed_at_utc": (observed_at + timedelta(minutes=1)).isoformat(),
        "invocation": {
            "provider": provider,
            "exit_code": 0,
            "requested_auth_mode": "api-key",
            "credential_env_allowlist": [
                {
                    "codex": "OPENAI_API_KEY",
                    "claude": "ANTHROPIC_API_KEY",
                    "gemini": "GEMINI_API_KEY",
                }[provider]
            ],
            "argv_policy": argv_policy(provider),
            "cli_version": scale.PROVIDER_PINS[provider]["cli_version"],
            "help_policy_sha256": scale.PROVIDER_PINS[provider]["help_policy_sha256"],
            "tool_policy_sha256": scale.PROVIDER_PINS[provider]["tool_policy_sha256"],
            "entrypoint_sha256": scale.PROVIDER_PINS[provider]["entrypoint_sha256"],
        },
        "producer_guard_assertion": {
            "claim": claim,
            "digest": scale.sha256_bytes(scale.canonical_json(claim)),
        },
    }


def rung(agent_count: int, *, start: datetime) -> dict:
    agents = [
        agent(
            provider,
            ordinal,
            seed=str(agent_count),
            observed_at=start + timedelta(minutes=2),
        )
        for provider, count in scale.RUNGS[agent_count].items()
        for ordinal in range(1, count + 1)
    ]
    return {
        "schema": scale.RUNG_SCHEMA,
        "run_id": "SC_SCALE_" + digest(f"run:{agent_count}")[:32],
        "verdict": "PASS",
        "agent_count": agent_count,
        "provider_counts": scale.RUNGS[agent_count],
        "logical_simulation": False,
        "visible_windows": True,
        "started_at_utc": start.isoformat(),
        "completed_at_utc": (start + timedelta(minutes=5)).isoformat(),
        "cli_invocation_accounting": {"cli_invocations_total": agent_count},
        "agents": agents,
    }


def refresh_row(bundle: Path, count: int) -> None:
    manifest = scale.load_json(bundle / "manifest.json")
    row = next(row for row in manifest["rungs"] if row["agent_count"] == count)
    path = bundle / f"rung-{count}.json"
    row["sha256"] = scale.sha256_file(path)
    row["size_bytes"] = path.stat().st_size
    scale.write_json(bundle / "manifest.json", manifest)


def mutate_rung(bundle: Path, count: int, callback) -> None:
    path = bundle / f"rung-{count}.json"
    value = scale.load_json(path)
    callback(value)
    scale.write_json(path, value)
    refresh_row(bundle, count)


def build_bundle(path: Path, *, generated_at: datetime = NOW - timedelta(hours=1)) -> None:
    rows = []
    base = generated_at - timedelta(minutes=45)
    for index, count in enumerate(scale.RUNGS):
        rung_path = path / f"rung-{count}.json"
        scale.write_json(rung_path, rung(count, start=base + timedelta(minutes=index * 10)))
        rows.append(
            {
                "agent_count": count,
                "file": rung_path.name,
                "sha256": scale.sha256_file(rung_path),
                "size_bytes": rung_path.stat().st_size,
            }
        )
    scale.write_json(
        path / "manifest.json",
        {
            "schema": scale.SCHEMA,
            "generated_at": generated_at.isoformat(),
            "producer_context": {
                "repository": "rblake2320/selfconnect",
                "workflow": scale.PRODUCER_WORKFLOW,
                "environment": scale.PRODUCER_ENVIRONMENT,
                "runner_group": scale.PRODUCER_RUNNER_GROUP,
                "ref": "refs/heads/master",
                "producer_run_id": PRODUCER_RUN_ID,
                "producer_run_attempt": 1,
                "actor": "restricted-producer",
                "ephemeral_runner": True,
                "dedicated_runner": True,
                "sensitive_repositories_present": False,
                "runner_image_sha256": digest("runner-image"),
                "ecosystem_contract_sha": ECOSYSTEM_SHA,
                "core_head_sha": CORE_HEAD,
            },
            "code_identity": {
                "core_remote": scale.CORE_REMOTE,
                "core_branch": scale.CORE_BRANCH,
                "core_head_sha": CORE_HEAD,
                "fresh_detached_checkout": True,
                "git_config_cleared": True,
                "python_env_cleared": True,
                "core_tree_sha256": digest("core-tree"),
                "producer_sha256": digest("producer"),
                "guard_module_sha256": digest("guard-module"),
            },
            "provider_pins": scale.PROVIDER_PINS,
            "rungs": rows,
        },
    )


class ScaleReadinessTests(unittest.TestCase):
    def assert_status(self, status: str, callback) -> None:
        with self.assertRaises(scale.ScaleReadinessError) as raised:
            callback()
        self.assertEqual(raised.exception.status, status)

    def validate(self, bundle: Path, **kwargs):
        with patch.object(scale, "remote_core_head", return_value=CORE_HEAD):
            return scale.validate_bundle(
                bundle,
                expected_ecosystem_sha=ECOSYSTEM_SHA,
                expected_producer_run_id=PRODUCER_RUN_ID,
                now=NOW,
                producer_archive_sha256=digest("archive"),
                verified_attestation_result_sha256=digest("attestation-result"),
                **kwargs,
            )

    def test_valid_attested_contract_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            report = self.validate(bundle)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["rungs"], [10, 15, 20])
        self.assertEqual(report["producer_archive_sha256"], digest("archive"))
        self.assertEqual(
            report["verified_attestation_result_sha256"],
            digest("attestation-result"),
        )
        self.assertEqual(report["producer_run_id"], PRODUCER_RUN_ID)
        self.assertEqual(report["producer_run_attempt"], 1)
        self.assertEqual(report["producer_actor"], "restricted-producer")
        self.assertEqual(
            report["verified_attestation_identity"],
            {
                "repository": "rblake2320/selfconnect",
                "signer_workflow": scale.PRODUCER_SIGNER_WORKFLOW,
                "source_ref": scale.PRODUCER_SOURCE_REF,
                "source_digest": CORE_HEAD,
            },
        )

    def test_legacy_v3_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            mutate_rung(bundle, 10, lambda value: value.update(schema=scale.LEGACY_SCHEMA))
            self.assert_status("legacy_unsafe_producer_rejected", lambda: self.validate(bundle))

    def test_stale_and_future_manifests_fail(self) -> None:
        for generated, status in (
            (NOW - timedelta(hours=169), "evidence_stale"),
            (NOW + timedelta(minutes=6), "evidence_from_future"),
        ):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle, generated_at=generated)
                self.assert_status(status, lambda: self.validate(bundle))

    def test_stale_rung_fails_even_with_fresh_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            def make_stale(value):
                value.update(
                    started_at_utc="2000-01-01T00:00:00+00:00",
                    completed_at_utc="2000-01-01T00:05:00+00:00",
                )
                for agent_value in value["agents"]:
                    agent_value["started_at_utc"] = "2000-01-01T00:01:00+00:00"
                    agent_value["completed_at_utc"] = "2000-01-01T00:03:00+00:00"
                    for observation in agent_value["observed_acks"].values():
                        observation["captured_at_utc"] = "2000-01-01T00:02:00+00:00"
            mutate_rung(
                bundle,
                10,
                make_stale,
            )
            self.assert_status("rung_time_invalid", lambda: self.validate(bundle))

    def test_wrong_remote_core_head_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            with patch.object(scale, "remote_core_head", return_value="c" * 40):
                self.assert_status(
                    "evidence_wrong_core_head",
                    lambda: scale.validate_bundle(
                        bundle,
                        expected_ecosystem_sha=ECOSYSTEM_SHA,
                        expected_producer_run_id=PRODUCER_RUN_ID,
                        now=NOW,
                        producer_archive_sha256=digest("archive"),
                        verified_attestation_result_sha256=digest("attestation-result"),
                    ),
                )

    def test_missing_tampered_and_extra_files_fail(self) -> None:
        cases = ("missing", "tampered", "extra")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                if case == "missing":
                    (bundle / "rung-15.json").unlink()
                    status = "bundle_contents_invalid"
                elif case == "tampered":
                    (bundle / "rung-15.json").write_text("{}\n", encoding="utf-8")
                    status = "rung_artifact_mismatch"
                else:
                    (bundle / "provider.log").write_text("unsafe", encoding="utf-8")
                    status = "bundle_contents_invalid"
                self.assert_status(status, lambda: self.validate(bundle))

    def test_unsafe_provider_mode_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            mutate_rung(
                bundle,
                10,
                lambda value: value["agents"][0]["invocation"]["argv_policy"].append("--yolo"),
            )
            self.assert_status("provider_mode_not_restricted", lambda: self.validate(bundle))

    def test_provider_environment_is_an_exact_singleton(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            mutate_rung(
                bundle,
                15,
                lambda value: value["agents"][0]["invocation"].update(
                    credential_env_allowlist=["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
                ),
            )
            self.assert_status("provider_env_not_isolated", lambda: self.validate(bundle))

    def test_requested_auth_mode_is_only_a_bounded_assertion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            mutate_rung(
                bundle,
                15,
                lambda value: value["agents"][0]["invocation"].update(requested_auth_mode="oauth"),
            )
            self.assert_status("requested_auth_mode_invalid", lambda: self.validate(bundle))

    def test_runner_must_be_ephemeral_dedicated_and_isolated(self) -> None:
        for field, value, status in (
            ("ephemeral_runner", False, "producer_runner_not_ephemeral"),
            ("dedicated_runner", False, "producer_runner_not_dedicated"),
            ("sensitive_repositories_present", True, "producer_runner_not_isolated"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                manifest = scale.load_json(bundle / "manifest.json")
                manifest["producer_context"][field] = value
                scale.write_json(bundle / "manifest.json", manifest)
                self.assert_status(status, lambda: self.validate(bundle))

    def test_checkout_and_import_identity_must_be_pinned(self) -> None:
        for field, value in (
            ("fresh_detached_checkout", False),
            ("git_config_cleared", False),
            ("python_env_cleared", False),
            ("producer_sha256", "bad"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                manifest = scale.load_json(bundle / "manifest.json")
                manifest["code_identity"][field] = value
                scale.write_json(bundle / "manifest.json", manifest)
                self.assert_status("producer_code_identity_invalid", lambda: self.validate(bundle))

    def test_cli_version_help_and_gemini_deny_policy_are_pinned(self) -> None:
        self.assertEqual(
            {provider: scale.policy_projection_sha256(provider) for provider in scale.PROVIDER_PINS},
            {
                "codex": "008845ea35aa87cdf84f1f87d287213e877a4e7caac8cfa1899ab37d81716d7b",
                "claude": "2a0d78a6685bca211a77b2d06acdca5efe6bfe54f366e5500832c45dc9ae6f12",
                "gemini": "183a476458c2db6d5530e088ee742b28ec460cd5d35e9347eef7c1b1ef6965a2",
            },
        )
        for provider, field, value in (
            ("codex", "cli_version", "future-version"),
            ("claude", "help_policy_sha256", "0" * 64),
            ("gemini", "tool_policy_sha256", "0" * 64),
        ):
            with self.subTest(provider=provider, field=field), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                manifest = scale.load_json(bundle / "manifest.json")
                manifest["provider_pins"][provider][field] = value
                scale.write_json(bundle / "manifest.json", manifest)
                self.assert_status("provider_cli_policy_not_pinned", lambda: self.validate(bundle))

    def test_contract_sha_and_run_id_are_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            with patch.object(scale, "remote_core_head", return_value=CORE_HEAD):
                self.assert_status(
                    "producer_context_invalid",
                    lambda: scale.validate_bundle(
                        bundle,
                        expected_ecosystem_sha="c" * 40,
                        expected_producer_run_id=PRODUCER_RUN_ID,
                        now=NOW,
                        producer_archive_sha256=digest("archive"),
                        verified_attestation_result_sha256=digest("attestation-result"),
                    ),
                )

    def test_run_attempt_and_actor_are_bound_to_actions_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            with patch.object(scale, "remote_core_head", return_value=CORE_HEAD):
                for kwargs in (
                    {"expected_producer_run_attempt": 2},
                    {"expected_producer_actor": "different-actor"},
                ):
                    with self.subTest(kwargs=kwargs):
                        self.assert_status(
                            "producer_context_invalid",
                            lambda: scale.validate_bundle(
                                bundle,
                                expected_ecosystem_sha=ECOSYSTEM_SHA,
                                expected_producer_run_id=PRODUCER_RUN_ID,
                                now=NOW,
                                producer_archive_sha256=digest("archive"),
                                verified_attestation_result_sha256=digest(
                                    "attestation-result"
                                ),
                                **kwargs,
                            ),
                        )

    def test_agent_count_provider_mix_and_exact_roles_are_enforced(self) -> None:
        mutations = (
            lambda value: value["agents"].pop(),
            lambda value: value.update(provider_counts={"claude": 6, "codex": 4, "gemini": 5}),
            lambda value: value["agents"][0].update(role="invented-role"),
        )
        statuses = ("agent_evidence_count_mismatch", "provider_counts_mismatch", "agent_role_invalid")
        for mutation, status in zip(mutations, statuses, strict=True):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                mutate_rung(bundle, 15, mutation)
                self.assert_status(status, lambda: self.validate(bundle))

    def test_role_cannot_be_reassigned_to_another_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            def swap(value):
                claude = next(agent for agent in value["agents"] if agent["provider"] == "claude")
                codex = next(agent for agent in value["agents"] if agent["provider"] == "codex")
                claude["role"], codex["role"] = codex["role"], claude["role"]
            mutate_rung(bundle, 15, swap)
            self.assert_status("agent_role_invalid", lambda: self.validate(bundle))

    def test_invocation_must_repeat_approved_provider_pins(self) -> None:
        for field, value in (
            ("entrypoint_sha256", "0" * 64),
            ("cli_version", "different"),
            ("help_policy_sha256", "0" * 64),
            ("tool_policy_sha256", "0" * 64),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                mutate_rung(
                    bundle,
                    10,
                    lambda rung_value: rung_value["agents"][0]["invocation"].update(
                        {field: value}
                    ),
                )
                self.assert_status(
                    "provider_invocation_not_pinned", lambda: self.validate(bundle)
                )

    def test_nonce_and_expected_hashes_are_recomputed(self) -> None:
        for field in ("nonce_sha256", "expected_sha256"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                mutate_rung(bundle, 10, lambda value: value["agents"][0].update({field: "0" * 64}))
                self.assert_status("agent_hash_invalid", lambda: self.validate(bundle))

    def test_nonce_reuse_within_and_across_rungs_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            def reuse_within(value):
                source = value["agents"][0]
                target = value["agents"][1]
                provider, role = target["provider"], target["role"]
                nonce = source["nonce"]
                target["nonce"] = nonce
                target["nonce_sha256"] = digest(nonce)
                target["expected_sha256"] = digest(scale.expected_ack(provider, role, nonce))
                for observation in target["observed_acks"].values():
                    observation["sha256"] = target["expected_sha256"]
                claim = target["producer_guard_assertion"]["claim"]
                claim["title_sha256"] = digest(f"SC_SCALE {provider} {role} {nonce}")
                target["producer_guard_assertion"]["digest"] = scale.sha256_bytes(
                    scale.canonical_json(claim)
                )
            mutate_rung(bundle, 10, reuse_within)
            self.assert_status("agent_nonce_invalid", lambda: self.validate(bundle))
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            source = scale.load_json(bundle / "rung-10.json")["agents"][0]
            def reuse(value):
                target = value["agents"][-1]
                provider, role = target["provider"], target["role"]
                nonce = source["nonce"]
                target["nonce"] = nonce
                target["nonce_sha256"] = digest(nonce)
                target["expected_sha256"] = digest(scale.expected_ack(provider, role, nonce))
                for observation in target["observed_acks"].values():
                    observation["sha256"] = target["expected_sha256"]
                claim = target["producer_guard_assertion"]["claim"]
                claim["title_sha256"] = digest(f"SC_SCALE {provider} {role} {nonce}")
                target["producer_guard_assertion"]["digest"] = scale.sha256_bytes(
                    scale.canonical_json(claim)
                )
            mutate_rung(bundle, 15, reuse)
            self.assert_status("cross_rung_nonce_reuse", lambda: self.validate(bundle))

    def test_guard_digest_condition_title_and_tree_are_enforced(self) -> None:
        cases = (
            (lambda guard: guard.update(digest="0" * 64), "guard_digest_invalid"),
            (lambda guard: guard["claim"].update(pre_guard_ok=False), "guard_digest_invalid"),
            (lambda guard: guard["claim"].update(title_sha256="0" * 64), "guard_digest_invalid"),
            (lambda guard: guard["claim"].update(process_tree_sha256="bad"), "guard_digest_invalid"),
        )
        for mutation, status in cases:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                mutate_rung(
                    bundle,
                    10,
                    lambda value: mutation(
                        value["agents"][0]["producer_guard_assertion"]
                    ),
                )
                self.assert_status(status, lambda: self.validate(bundle))

    def test_semantically_invalid_but_rehashed_guard_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            def invalidate(value):
                guard = value["agents"][0]["producer_guard_assertion"]
                guard["claim"]["provider_in_spawn_tree"] = False
                guard["digest"] = scale.sha256_bytes(scale.canonical_json(guard["claim"]))
            mutate_rung(bundle, 10, invalidate)
            self.assert_status("guard_assertion_invalid", lambda: self.validate(bundle))

    def test_both_observed_acks_and_provider_outcomes_are_required(self) -> None:
        for mutation, status in (
            (
                lambda agent: agent["observed_acks"].pop("uia_terminal"),
                "observed_ack_invalid",
            ),
            (
                lambda agent: agent["observed_acks"]["process_stdout"].update(
                    sha256="0" * 64
                ),
                "observed_ack_invalid",
            ),
            (
                lambda agent: agent["observed_acks"]["uia_terminal"].update(
                    captured_at_utc="2000-01-01T00:00:00+00:00"
                ),
                "observed_ack_invalid",
            ),
            (
                lambda agent: agent.update(provider_outcome={"auth_failed": True, "quota_exceeded": False}),
                "provider_outcome_invalid",
            ),
        ):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                bundle = Path(temp)
                build_bundle(bundle)
                mutate_rung(bundle, 10, lambda value: mutation(value["agents"][0]))
                self.assert_status(status, lambda: self.validate(bundle))

    def test_model_call_claims_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            mutate_rung(bundle, 10, lambda value: value.update(real_model_calls_total=10))
            self.assert_status("unsupported_model_call_claim", lambda: self.validate(bundle))

    def test_rungs_must_be_ordered_and_nonoverlapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            first = scale.load_json(bundle / "rung-10.json")
            mutate_rung(
                bundle,
                15,
                lambda value: value.update(started_at_utc=first["started_at_utc"]),
            )
            self.assert_status("rung_order_invalid", lambda: self.validate(bundle))

    def test_agents_must_have_a_shared_concurrency_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            def make_sequential(value):
                last = value["agents"][-1]
                last["started_at_utc"] = (
                    datetime.fromisoformat(value["completed_at_utc"]) - timedelta(seconds=30)
                ).isoformat()
                last["completed_at_utc"] = value["completed_at_utc"]
                for observation in last["observed_acks"].values():
                    observation["captured_at_utc"] = last["completed_at_utc"]
            mutate_rung(bundle, 10, make_sequential)
            self.assert_status(
                "agent_concurrency_not_established", lambda: self.validate(bundle)
            )

    def test_run_ids_must_be_unique_across_rungs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            reused = scale.load_json(bundle / "rung-10.json")["run_id"]
            mutate_rung(bundle, 15, lambda value: value.update(run_id=reused))
            self.assert_status("cross_rung_run_id_reuse", lambda: self.validate(bundle))

    def test_unvalidated_extra_claims_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            mutate_rung(bundle, 10, lambda value: value.update(provider_receipt="not-validated"))
            self.assert_status("rung_schema_invalid", lambda: self.validate(bundle))

    def test_malformed_provider_type_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            build_bundle(bundle)
            mutate_rung(bundle, 10, lambda value: value["agents"][0].update(provider=[]))
            self.assert_status("agent_role_invalid", lambda: self.validate(bundle))

    def test_duplicate_keys_and_oversized_json_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text('{"schema":"one","schema":"two"}', encoding="utf-8")
            self.assert_status("evidence_json_invalid", lambda: scale.load_json(path))
            path.write_bytes(b" " * (scale.MAX_JSON_BYTES + 1))
            self.assert_status("evidence_json_too_large", lambda: scale.load_json(path))

    def test_verified_attestation_result_must_be_nonempty_json_array(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "verified-attestation.json"
            for payload in ("", "{}", "[]", '[{"ok":true,"ok":false}]'):
                with self.subTest(payload=payload):
                    path.write_text(payload, encoding="utf-8")
                    self.assert_status(
                        "attestation_result_invalid",
                        lambda: scale.attestation_result_sha256(path),
                    )
            path.write_text('[{"verificationResult":{}}]', encoding="utf-8")
            self.assertEqual(scale.attestation_result_sha256(path), scale.sha256_file(path))

    def test_archive_extraction_accepts_only_exact_flat_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            build_bundle(source)
            archive = root / "evidence.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
                for path in source.iterdir():
                    handle.write(path, path.name)
            destination = root / "destination"
            scale.extract_archive(archive, destination)
            self.assertEqual({path.name for path in destination.iterdir()}, {
                "manifest.json", "rung-10.json", "rung-15.json", "rung-20.json"
            })

    def test_archive_traversal_and_unexpected_entries_fail_before_write(self) -> None:
        for unsafe_name in ("../escaped.json", "nested/manifest.json"):
            with self.subTest(name=unsafe_name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = root / "evidence.zip"
                with zipfile.ZipFile(archive, "w") as handle:
                    handle.writestr(unsafe_name, "{}")
                destination = root / "destination"
                self.assert_status(
                    "evidence_archive_contents_invalid",
                    lambda: scale.extract_archive(archive, destination),
                )
                self.assertFalse(destination.exists())

    def test_workflow_verifies_attestation_before_parsing_and_attests_report(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "scale-readiness.yml").read_text(encoding="utf-8")
        self.assertLess(workflow.index("gh attestation verify"), workflow.index("scale_readiness.py verify"))
        self.assertIn("--signer-workflow github.com/rblake2320/selfconnect/.github/workflows/restricted-scale-producer.yml", workflow)
        self.assertIn("--source-ref refs/heads/master", workflow)
        self.assertIn("--source-digest $run.head_sha", workflow)
        self.assertIn("scale_readiness.py extract", workflow)
        self.assertIn("--producer-archive (Join-Path $env:RUNNER_TEMP", workflow)
        self.assertIn("--verified-attestation-result (Join-Path $env:RUNNER_TEMP", workflow)
        self.assertIn("--format json | Set-Content", workflow)
        self.assertIn("--expected-producer-run-attempt $env:PRODUCER_RUN_ATTEMPT", workflow)
        self.assertIn("--expected-producer-actor $env:PRODUCER_ACTOR", workflow)
        self.assertIn("actions/attest-build-provenance@0f67c3f", workflow)
        self.assertIn("restricted-scale-evidence", workflow)
        self.assertIn("scale-evidence.zip", workflow)

    def test_workflow_has_no_provider_credentials_or_execution(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "scale-readiness.yml").read_text(encoding="utf-8")
        for forbidden in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "real-agent-baseline-v3.py"):
            self.assertNotIn(forbidden, workflow)
        self.assertIn("READINESS_GH_TOKEN", workflow)

    def test_workflow_serializes_runs_and_always_cleans(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "scale-readiness.yml").read_text(encoding="utf-8")
        self.assertIn("group: scale-readiness-${{ github.repository }}", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("Clean temporary evidence", workflow)
        self.assertGreaterEqual(workflow.count("if: always()"), 2)


if __name__ == "__main__":
    unittest.main()
