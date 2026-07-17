#!/usr/bin/env python3
"""Collect and verify real-agent 10/15/20 scale-ladder evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA = "selfconnect.scale_readiness_evidence.v1"
RUNG_SCHEMA = "selfconnect.scale_readiness_rung.v1"
SOURCE_SCHEMA = "selfconnect.real_agent_baseline.v3"
CORE_REMOTE = "https://github.com/rblake2320/selfconnect"
CORE_BRANCH = "master"
DEFAULT_MAX_EVIDENCE_AGE_HOURS = 168.0
MAX_EVIDENCE_AGE_HOURS = 168.0
MAX_FUTURE_SKEW = timedelta(minutes=5)
MAX_JSON_BYTES = 2 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^SC_REAL5_\d{8}_\d{6}$")

RUNGS: dict[int, dict[str, Any]] = {
    10: {
        "providers": "gemini:10",
        "provider_counts": {"gemini": 10},
        "timeout": 1200,
    },
    15: {
        "providers": "codex:5,claude:5,gemini:5",
        "provider_counts": {"claude": 5, "codex": 5, "gemini": 5},
        "timeout": 900,
    },
    20: {
        "providers": "codex:7,claude:7,gemini:6",
        "provider_counts": {"claude": 7, "codex": 7, "gemini": 6},
        "timeout": 1200,
    },
}


class ScaleReadinessError(RuntimeError):
    """A bounded readiness failure safe to expose in CI."""

    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.status = status


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ScaleReadinessError("evidence_json_too_large")
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {value}")
            ),
        )
    except ScaleReadinessError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScaleReadinessError("evidence_json_invalid") from exc
    if not isinstance(value, dict):
        raise ScaleReadinessError("evidence_json_invalid")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise ScaleReadinessError("evidence_timestamp_invalid")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ScaleReadinessError("evidence_timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise ScaleReadinessError("evidence_timestamp_invalid")
    return parsed.astimezone(timezone.utc)


def normalize_remote_url(value: str) -> str:
    remote = value.strip().replace("\\", "/")
    match = re.fullmatch(r"git@github\.com:(.+)", remote, flags=re.IGNORECASE)
    if match:
        remote = f"https://github.com/{match.group(1)}"
    elif remote.lower().startswith("ssh://git@github.com/"):
        remote = "https://github.com/" + remote[len("ssh://git@github.com/") :]
    remote = remote.rstrip("/")
    if remote.lower().endswith(".git"):
        remote = remote[:-4]
    return remote.lower()


def run_command(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise ScaleReadinessError("command_failed") from exc


def current_core_identity(core_repo: Path) -> dict[str, str]:
    if not core_repo.is_dir():
        raise ScaleReadinessError("core_repo_missing")

    commands = {
        "status": ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
        "head": ["git", "rev-parse", "HEAD"],
        "branch": ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        "remote": ["git", "remote", "get-url", "origin"],
    }
    results = {
        name: run_command(command, cwd=core_repo)
        for name, command in commands.items()
    }
    if any(result.returncode != 0 for result in results.values()):
        raise ScaleReadinessError("core_repo_query_failed")
    if results["status"].stdout.strip():
        raise ScaleReadinessError("core_repo_dirty")
    if results["branch"].stdout.strip() != CORE_BRANCH:
        raise ScaleReadinessError("core_repo_wrong_branch")
    if normalize_remote_url(results["remote"].stdout) != normalize_remote_url(CORE_REMOTE):
        raise ScaleReadinessError("core_repo_wrong_remote")

    remote = run_command(
        ["git", "ls-remote", "--exit-code", CORE_REMOTE, f"refs/heads/{CORE_BRANCH}"],
        cwd=core_repo,
    )
    fields = remote.stdout.split()
    if remote.returncode != 0 or len(fields) != 2:
        raise ScaleReadinessError("core_remote_head_unavailable")
    local_head = results["head"].stdout.strip().lower()
    remote_head = fields[0].lower()
    if not re.fullmatch(r"[0-9a-f]{40}", local_head) or local_head != remote_head:
        raise ScaleReadinessError("core_repo_not_current")
    return {
        "remote_url": CORE_REMOTE,
        "branch": CORE_BRANCH,
        "head_sha": local_head,
    }


def exact_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def exact_provider_counts(value: Any, expected: dict[str, int]) -> bool:
    if not isinstance(value, dict) or set(value) != set(expected):
        return False
    return all(exact_int(value.get(name)) == count for name, count in expected.items())


def validate_source_result(source: dict[str, Any], agent_count: int) -> dict[str, Any]:
    expected = RUNGS[agent_count]
    if source.get("schema") != SOURCE_SCHEMA:
        raise ScaleReadinessError("source_schema_invalid")
    if source.get("verdict") != "PASS":
        raise ScaleReadinessError("rung_not_passed")
    if exact_int(source.get("agent_count")) != agent_count:
        raise ScaleReadinessError("agent_count_mismatch")
    if not exact_provider_counts(source.get("provider_counts"), expected["provider_counts"]):
        raise ScaleReadinessError("provider_counts_mismatch")
    if source.get("logical_simulation") is not False:
        raise ScaleReadinessError("logical_simulation_rejected")
    if source.get("visible_windows") is not True:
        raise ScaleReadinessError("visible_windows_required")
    if source.get("uia_readback_attempted") is not True:
        raise ScaleReadinessError("uia_readback_required")
    if source.get("gemini_auth_type") != "gemini-api-key":
        raise ScaleReadinessError("gemini_auth_mode_invalid")
    if source.get("completion_policy") != "visible_window_plus_exact_ack_from_uia_or_provider_log":
        raise ScaleReadinessError("completion_policy_invalid")
    accounting = source.get("model_call_accounting")
    if (
        not isinstance(accounting, dict)
        or exact_int(accounting.get("real_model_calls_total")) != agent_count
        or type(accounting.get("real_model_calls_per_ack_task")) is not float
        or accounting.get("real_model_calls_per_ack_task") != 1.0
        or accounting.get("known_deterministic_task") is not False
    ):
        raise ScaleReadinessError("real_model_call_evidence_invalid")
    run_id = source.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ScaleReadinessError("run_id_invalid")

    counters = source.get("failure_counters")
    if not isinstance(counters, dict):
        raise ScaleReadinessError("failure_counters_invalid")
    zero_counters = (
        "missed_acks",
        "visible_window_missing",
        "uia_readback_failures",
        "wrong_window_guard_failures",
        "drift_or_narration_events",
        "approval_stalls",
        "wrong_ack_format",
        "provider_auth_required",
        "provider_quota_exceeded",
    )
    for name in zero_counters:
        if exact_int(counters.get(name)) != 0:
            status = "provider_quota_exceeded" if name == "provider_quota_exceeded" else "failure_counter_nonzero"
            raise ScaleReadinessError(status)
    provider_failures = counters.get("provider_failures")
    if not exact_provider_counts(
        provider_failures,
        {provider: 0 for provider in expected["provider_counts"]},
    ):
        raise ScaleReadinessError("provider_failure_nonzero")

    agents = source.get("agents")
    if not isinstance(agents, list) or len(agents) != agent_count:
        raise ScaleReadinessError("agent_evidence_count_mismatch")
    expected_providers = expected["provider_counts"]
    observed_providers = {provider: 0 for provider in expected_providers}
    roles: set[str] = set()
    nonce_hashes: set[str] = set()
    expected_hashes: set[str] = set()
    sanitized_agents: list[dict[str, Any]] = []
    for agent in agents:
        if not isinstance(agent, dict):
            raise ScaleReadinessError("agent_evidence_invalid")
        provider = agent.get("provider")
        role = agent.get("role")
        if not isinstance(provider, str) or provider not in observed_providers:
            raise ScaleReadinessError("agent_provider_invalid")
        if not isinstance(role, str) or not role or role in roles:
            raise ScaleReadinessError("agent_role_invalid")
        if (
            exact_int(agent.get("hwnd")) is None
            or int(agent["hwnd"]) <= 0
            or exact_int(agent.get("pid")) is None
            or int(agent["pid"]) <= 0
            or not isinstance(agent.get("title"), str)
            or not agent["title"]
        ):
            raise ScaleReadinessError("visible_agent_identity_invalid")
        roles.add(role)
        observed_providers[provider] += 1
        log_ack = agent.get("log_exact_ack") is True
        uia_ack = agent.get("uia_exact_ack") is True
        if not (log_ack or uia_ack):
            raise ScaleReadinessError("exact_ack_missing")
        if agent.get("status") != "pass" or agent.get("diagnosis") != "":
            raise ScaleReadinessError("agent_not_passed")
        nonce_hash = agent.get("nonce_hash")
        expected_hash = agent.get("expected_hash")
        if not isinstance(nonce_hash, str) or not SHA256_RE.fullmatch(nonce_hash.lower()):
            raise ScaleReadinessError("agent_hash_invalid")
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash.lower()):
            raise ScaleReadinessError("agent_hash_invalid")
        nonce_hash = nonce_hash.lower()
        expected_hash = expected_hash.lower()
        if nonce_hash in nonce_hashes or expected_hash in expected_hashes:
            raise ScaleReadinessError("agent_hash_reused")
        nonce_hashes.add(nonce_hash)
        expected_hashes.add(expected_hash)
        expected_ack_source = (
            "uia+log" if uia_ack and log_ack else "uia" if uia_ack else "log"
        )
        if agent.get("ack_source") != expected_ack_source:
            raise ScaleReadinessError("ack_source_invalid")
        sanitized_agents.append(
            {
                "provider": provider,
                "role": role,
                "nonce_hash": nonce_hash,
                "expected_hash": expected_hash,
                "log_exact_ack": log_ack,
                "uia_exact_ack": uia_ack,
                "ack_source": expected_ack_source,
                "status": "pass",
                "diagnosis": "",
            }
        )
    if observed_providers != expected_providers:
        raise ScaleReadinessError("agent_provider_counts_mismatch")

    return {
        "schema": RUNG_SCHEMA,
        "run_id": run_id,
        "verdict": "PASS",
        "agent_count": agent_count,
        "provider_counts": expected_providers,
        "gemini_auth_type": "gemini-api-key",
        "logical_simulation": False,
        "visible_windows": True,
        "uia_readback_attempted": True,
        "completion_policy": source["completion_policy"],
        "model_call_accounting": {
            "real_model_calls_total": agent_count,
            "real_model_calls_per_ack_task": 1.0,
            "known_deterministic_task": False,
        },
        "failure_counters": {name: 0 for name in zero_counters},
        "agents": sanitized_agents,
    }


def validate_rung_evidence(evidence: dict[str, Any], agent_count: int) -> str:
    # The sanitized artifact is intentionally accepted through the same strict
    # proposition checks as raw runner output.
    if evidence.get("schema") != RUNG_SCHEMA:
        raise ScaleReadinessError("rung_schema_invalid")
    counters = evidence.get("failure_counters")
    if not isinstance(counters, dict):
        raise ScaleReadinessError("failure_counters_invalid")
    agents = evidence.get("agents")
    if not isinstance(agents, list) or any(not isinstance(agent, dict) for agent in agents):
        raise ScaleReadinessError("agent_evidence_invalid")
    source = dict(evidence)
    source["schema"] = SOURCE_SCHEMA
    source["agents"] = [
        {
            **agent,
            # The reduced artifact deliberately omits live machine identifiers.
            # Positive sentinels allow reuse of proposition validation without
            # representing them as retained evidence.
            "hwnd": 1,
            "pid": 1,
            "title": "redacted-after-validation",
        }
        for agent in agents
    ]
    source["failure_counters"] = {
        **counters,
        "provider_failures": {
            provider: 0 for provider in RUNGS[agent_count]["provider_counts"]
        },
    }
    validate_source_result(source, agent_count)
    return str(evidence["run_id"])


def validate_bundle(
    bundle: Path,
    *,
    core_repo: Path,
    now: datetime | None = None,
    max_evidence_age_hours: float = DEFAULT_MAX_EVIDENCE_AGE_HOURS,
) -> dict[str, Any]:
    if (
        not math.isfinite(max_evidence_age_hours)
        or max_evidence_age_hours <= 0
        or max_evidence_age_hours > MAX_EVIDENCE_AGE_HOURS
    ):
        raise ScaleReadinessError("evidence_age_policy_invalid")
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ScaleReadinessError("manifest_missing")
    try:
        actual_files = {item.name for item in bundle.iterdir() if item.is_file()}
        actual_entries = {item.name for item in bundle.iterdir()}
    except OSError as exc:
        raise ScaleReadinessError("evidence_io_failed") from exc
    expected_files = {"manifest.json", *(f"rung-{count}.json" for count in RUNGS)}
    if expected_files - actual_entries:
        raise ScaleReadinessError("rung_file_missing")
    if actual_files != expected_files or actual_entries != expected_files:
        raise ScaleReadinessError("bundle_contents_invalid")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != SCHEMA:
        raise ScaleReadinessError("manifest_schema_invalid")

    evaluated_at = now or datetime.now(timezone.utc)
    if evaluated_at.tzinfo is None:
        raise ScaleReadinessError("evaluation_time_invalid")
    evaluated_at = evaluated_at.astimezone(timezone.utc)
    generated_at = parse_utc(manifest.get("generated_at"))
    if generated_at > evaluated_at + MAX_FUTURE_SKEW:
        raise ScaleReadinessError("evidence_from_future")
    if evaluated_at - generated_at > timedelta(hours=max_evidence_age_hours):
        raise ScaleReadinessError("evidence_stale")

    identity = current_core_identity(core_repo)
    if manifest.get("core") != identity:
        raise ScaleReadinessError("evidence_wrong_core_head")
    rungs = manifest.get("rungs")
    if not isinstance(rungs, list) or len(rungs) != len(RUNGS):
        raise ScaleReadinessError("rung_manifest_invalid")

    observed: set[int] = set()
    run_ids: set[str] = set()
    for row in rungs:
        if not isinstance(row, dict):
            raise ScaleReadinessError("rung_manifest_invalid")
        agent_count = exact_int(row.get("agent_count"))
        if agent_count not in RUNGS or agent_count in observed:
            raise ScaleReadinessError("rung_manifest_invalid")
        observed.add(agent_count)
        expected_name = f"rung-{agent_count}.json"
        if row.get("file") != expected_name:
            raise ScaleReadinessError("rung_file_invalid")
        path = bundle / expected_name
        if not path.is_file() or path.is_symlink():
            raise ScaleReadinessError("rung_file_missing")
        digest = sha256_file(path)
        size = path.stat().st_size
        if row.get("sha256") != digest or exact_int(row.get("size_bytes")) != size:
            raise ScaleReadinessError("rung_artifact_mismatch")
        if not exact_provider_counts(
            row.get("provider_counts"), RUNGS[agent_count]["provider_counts"]
        ):
            raise ScaleReadinessError("rung_manifest_invalid")
        run_id = validate_rung_evidence(load_json(path), agent_count)
        if run_id in run_ids:
            raise ScaleReadinessError("run_id_reused")
        run_ids.add(run_id)
    if observed != set(RUNGS):
        raise ScaleReadinessError("rung_manifest_invalid")

    return {
        "schema": SCHEMA,
        "ok": True,
        "status": "ready",
        "evaluated_at": evaluated_at.isoformat(),
        "generated_at": generated_at.isoformat(),
        "core": identity,
        "rungs": sorted(observed),
    }


def collect_bundle(
    core_repo: Path,
    output_dir: Path,
    *,
    max_evidence_age_hours: float = DEFAULT_MAX_EVIDENCE_AGE_HOURS,
) -> dict[str, Any]:
    identity = current_core_identity(core_repo)
    runner = core_repo / "experiments" / "fabric_v2" / "real_agent_baseline.py"
    if not runner.is_file():
        raise ScaleReadinessError("scale_runner_missing")
    if output_dir.exists():
        raise ScaleReadinessError("output_already_exists")
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="selfconnect-scale-", dir=output_dir.parent
    ) as temp_name:
        temp = Path(temp_name)
        staged = temp / "bundle"
        staged.mkdir()
        manifest_rungs: list[dict[str, Any]] = []
        for agent_count, spec in RUNGS.items():
            raw_dir = temp / f"raw-{agent_count}"
            raw_dir.mkdir()
            command = [
                sys.executable,
                str(runner),
                "--agents",
                str(agent_count),
                "--providers",
                spec["providers"],
                "--timeout",
                str(spec["timeout"]),
                "--close-windows",
                "--gemini-auth-type",
                "gemini-api-key",
                "--results-dir",
                str(raw_dir),
            ]
            result = run_command(
                command,
                cwd=core_repo,
                timeout=int(spec["timeout"]) + 180,
            )
            files = list(raw_dir.glob("real_agent_baseline_SC_REAL5_*.json"))
            if result.returncode != 0 or len(files) != 1:
                raise ScaleReadinessError(f"rung_{agent_count}_execution_failed")
            sanitized = validate_source_result(load_json(files[0]), agent_count)
            evidence_path = staged / f"rung-{agent_count}.json"
            write_json(evidence_path, sanitized)
            manifest_rungs.append(
                {
                    "agent_count": agent_count,
                    "provider_counts": spec["provider_counts"],
                    "file": evidence_path.name,
                    "sha256": sha256_file(evidence_path),
                    "size_bytes": evidence_path.stat().st_size,
                }
            )
        if current_core_identity(core_repo) != identity:
            raise ScaleReadinessError("core_repo_changed_during_collection")
        manifest = {
            "schema": SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "core": identity,
            "rungs": manifest_rungs,
        }
        write_json(staged / "manifest.json", manifest)
        staged.replace(output_dir)
    return validate_bundle(
        output_dir,
        core_repo=core_repo,
        max_evidence_age_hours=max_evidence_age_hours,
    )


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("collect", "verify"))
    parser.add_argument("--core-repo", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--report-file", type=Path)
    parser.add_argument(
        "--max-evidence-age-hours",
        type=float,
        default=DEFAULT_MAX_EVIDENCE_AGE_HOURS,
    )
    args = parser.parse_args()

    try:
        if args.mode == "collect":
            report = collect_bundle(
                args.core_repo.resolve(),
                args.bundle.resolve(),
                max_evidence_age_hours=args.max_evidence_age_hours,
            )
        else:
            report = validate_bundle(
                args.bundle.resolve(),
                core_repo=args.core_repo.resolve(),
                max_evidence_age_hours=args.max_evidence_age_hours,
            )
    except ScaleReadinessError as exc:
        report = {"schema": SCHEMA, "ok": False, "status": exc.status}
        write_report(args.report_file, report)
        print(json.dumps(report, indent=2))
        return 2
    except (OSError, UnicodeError):
        report = {"schema": SCHEMA, "ok": False, "status": "evidence_io_failed"}
        write_report(args.report_file, report)
        print(json.dumps(report, indent=2))
        return 2
    write_report(args.report_file, report)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
