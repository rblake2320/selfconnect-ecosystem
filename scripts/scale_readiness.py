#!/usr/bin/env python3
"""Verify attested restricted-producer 10/15/20 scale evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA = "selfconnect.scale_readiness_evidence.v2"
RUNG_SCHEMA = "selfconnect.restricted_scale_result.v2"
LEGACY_SCHEMA = "selfconnect.real_agent_baseline.v3"
CORE_REMOTE = "https://github.com/rblake2320/selfconnect"
CORE_BRANCH = "master"
ECOSYSTEM_REPOSITORY = "rblake2320/selfconnect-ecosystem"
PRODUCER_WORKFLOW = "Restricted Real-Agent Scale Producer"
PRODUCER_ENVIRONMENT = "scale-readiness-producer"
PRODUCER_RUNNER_GROUP = "selfconnect-scale-ephemeral"
PRODUCER_JOB_NAME = "restricted-scale-producer"
PRODUCER_SIGNER_WORKFLOW = (
    "github.com/rblake2320/selfconnect/.github/workflows/restricted-scale-producer.yml"
)
PRODUCER_SOURCE_REF = "refs/heads/master"
PRODUCER_REPOSITORY = "rblake2320/selfconnect"
PRODUCER_REPOSITORY_URI = f"https://github.com/{PRODUCER_REPOSITORY}"
PRODUCER_SIGNER_URI = (
    f"{PRODUCER_REPOSITORY_URI}/.github/workflows/"
    "restricted-scale-producer.yml@refs/heads/master"
)
GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
SLSA_PROVENANCE_V1 = "https://slsa.dev/provenance/v1"
CONSUMER_REPOSITORY = "rblake2320/selfconnect-ecosystem"
CONSUMER_WORKFLOW = "Verify Restricted Scale Evidence"
DEFAULT_MAX_EVIDENCE_AGE_HOURS = 168.0
MAX_EVIDENCE_AGE_HOURS = 168.0
MAX_FUTURE_SKEW = timedelta(minutes=5)
MAX_RUNG_DURATION = timedelta(minutes=30)
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
NONCE_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^SC_SCALE_[0-9a-f]{32}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")

RUNGS: dict[int, dict[str, int]] = {
    10: {"gemini": 10},
    15: {"claude": 5, "codex": 5, "gemini": 5},
    20: {"claude": 7, "codex": 7, "gemini": 6},
}

REQUIRED_RESTRICTED_MODES = {
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
}
GEMINI_DENY_ALL_POLICY_SHA256 = (
    "ff0198012262e2a478eb9d26ebe175924079cc7d16379ef809d18c012649029a"
)
PROVIDER_VERSIONS = {
    "codex": "codex-cli 0.144.4",
    "claude": "2.1.183 (Claude Code)",
    "gemini": "0.46.0",
}
PROVIDER_ENTRYPOINT_SHA256 = {
    "codex": "51398051c2332b6afe08dc3b9dbb4056085c197f35ca57a307ee303d450cada5",
    "claude": "ba6e71d0e39b33c42a519bd10fc6d79b04d62cedcc918b3991ff863462261eb0",
    "gemini": "6970329338ab5726d015b4ed847b1d2fd960244baefc86cbeacd3786b677dddc",
}
PROVIDER_EXE_NAMES = {
    "codex": "codex.exe",
    "claude": "claude.exe",
    "gemini": "node.exe",
}
COMMON_PROVIDER_ENV_NAMES = {
    "ALLUSERSPROFILE",
    "APPDATA",
    "CI",
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "NO_COLOR",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERDOMAIN",
    "USERNAME",
    "USERPROFILE",
    "WINDIR",
}
PROVIDER_ENV_NAMES = {
    "codex": sorted(COMMON_PROVIDER_ENV_NAMES | {"OPENAI_API_KEY"}),
    "claude": sorted(COMMON_PROVIDER_ENV_NAMES | {"ANTHROPIC_API_KEY"}),
    "gemini": sorted(
        COMMON_PROVIDER_ENV_NAMES | {"GEMINI_API_KEY", "GEMINI_CLI_NO_RELAUNCH"}
    ),
}
# These are populated from the exact pinned CLI help observations. They are
# intentionally distinct from the required policy projection below.
PROVIDER_HELP_SHA256 = {
    "codex": "9f86f0115238ddde2514587e5f95b0ab0aa6b89495e5912878d49ad26038aa19",
    "claude": "6c5e44dd5a1c5b04f7deb4d734ac6d2585561509c6a2d5deaed6914665e03b29",
    "gemini": "b5c6e1af180f48adb3700982e7b06e905f29d2965f047eaeebd0b5c4f676b632",
}
PROVIDER_HELP_COMMANDS = {
    "codex": ["codex", "exec", "--help"],
    "claude": ["claude", "--help"],
    "gemini": ["gemini", "--help"],
}
FORBIDDEN_MODE_TOKENS = {
    "--dangerously-bypass-approvals-and-sandbox",
    "--dangerously-skip-permissions",
    "bypassPermissions",
    "--yolo",
    "yolo",
    "--skip-trust",
}


def provider_policy_projection(provider: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "cli_version": PROVIDER_VERSIONS[provider],
        "help_command": PROVIDER_HELP_COMMANDS[provider],
        "required_runtime_policy": REQUIRED_RESTRICTED_MODES[provider],
        "forbidden_runtime_tokens": sorted(FORBIDDEN_MODE_TOKENS),
    }


def policy_projection_sha256(provider: str) -> str:
    payload = json.dumps(
        provider_policy_projection(provider),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


PROVIDER_PINS = {
    provider: {
        "required_policy_projection_sha256": policy_projection_sha256(provider),
        "required_tool_policy_sha256": (
            GEMINI_DENY_ALL_POLICY_SHA256 if provider == "gemini" else None
        ),
        "expected_cli_version": PROVIDER_VERSIONS[provider],
        "expected_help_sha256": PROVIDER_HELP_SHA256[provider],
        "expected_entrypoint_sha256": PROVIDER_ENTRYPOINT_SHA256[provider],
        "expected_provider_exe_name": PROVIDER_EXE_NAMES[provider],
    }
    for provider in ("codex", "claude", "gemini")
}


class ScaleReadinessError(RuntimeError):
    """A bounded readiness failure safe to expose in CI."""

    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.status = status


def exact_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def exact_provider_counts(value: Any, expected: dict[str, int]) -> bool:
    if not isinstance(value, dict) or set(value) != set(expected):
        return False
    return all(exact_int(value.get(name)) == count for name, count in expected.items())


def require_exact_keys(value: dict[str, Any], expected: set[str], status: str) -> None:
    if set(value) != expected:
        raise ScaleReadinessError(status)


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


def parse_attestation_result(
    path: Path,
    *,
    archive_sha256: str,
    source_digest: str,
    producer_run_id: int,
    producer_run_attempt: int,
) -> dict[str, Any]:
    if (
        not SHA256_RE.fullmatch(archive_sha256)
        or not SHA1_RE.fullmatch(source_digest)
        or producer_run_id <= 0
        or producer_run_attempt <= 0
    ):
        raise ScaleReadinessError("attestation_expected_identity_invalid")
    try:
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size > MAX_JSON_BYTES
        ):
            raise ScaleReadinessError("attestation_result_invalid")
        value = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda item: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {item}")
            ),
        )
    except ScaleReadinessError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScaleReadinessError("attestation_result_invalid") from exc
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise ScaleReadinessError("attestation_result_invalid")
    result = value[0].get("verificationResult")
    if not isinstance(result, dict):
        raise ScaleReadinessError("attestation_result_invalid")
    signature = result.get("signature")
    certificate = signature.get("certificate") if isinstance(signature, dict) else None
    statement = result.get("statement")
    timestamps = result.get("verifiedTimestamps")
    if (
        not isinstance(certificate, dict)
        or not isinstance(statement, dict)
        or not isinstance(timestamps, list)
        or not timestamps
    ):
        raise ScaleReadinessError("attestation_result_invalid")
    for timestamp in timestamps:
        if (
            not isinstance(timestamp, dict)
            or not isinstance(timestamp.get("type"), str)
            or not timestamp["type"]
            or not isinstance(timestamp.get("uri"), str)
            or not timestamp["uri"]
        ):
            raise ScaleReadinessError("attestation_result_invalid")
        parse_utc(timestamp.get("timestamp"))

    expected_run_uri = (
        f"{PRODUCER_REPOSITORY_URI}/actions/runs/{producer_run_id}/attempts/"
        f"{producer_run_attempt}"
    )
    expected_certificate = {
        "issuer": GITHUB_OIDC_ISSUER,
        "subjectAlternativeName": PRODUCER_SIGNER_URI,
        "buildSignerURI": PRODUCER_SIGNER_URI,
        "runnerEnvironment": "self-hosted",
        "sourceRepositoryURI": PRODUCER_REPOSITORY_URI,
        "sourceRepositoryDigest": source_digest,
        "sourceRepositoryRef": PRODUCER_SOURCE_REF,
        "buildTrigger": "workflow_dispatch",
        "runInvocationURI": expected_run_uri,
    }

    verified_certificate = {
        name: certificate.get(name) for name in expected_certificate
    }
    if verified_certificate != expected_certificate:
        raise ScaleReadinessError("attestation_identity_invalid")

    if statement.get("predicateType") != SLSA_PROVENANCE_V1:
        raise ScaleReadinessError("attestation_predicate_invalid")
    subjects = statement.get("subject")
    if (
        not isinstance(subjects, list)
        or len(subjects) != 1
        or not isinstance(subjects[0], dict)
        or subjects[0].get("name") != "scale-evidence.zip"
        or subjects[0].get("digest") != {"sha256": archive_sha256}
    ):
        raise ScaleReadinessError("attestation_subject_invalid")
    return {
        "result_sha256": sha256_file(path),
        "certificate": verified_certificate,
        "predicate_type": statement["predicateType"],
        "subject": {
            "name": subjects[0]["name"],
            "sha256": subjects[0]["digest"]["sha256"],
        },
        "verified_timestamp_count": len(timestamps),
    }


def parse_producer_jobs_result(
    path: Path,
    *,
    producer_run_id: int,
    source_digest: str,
) -> dict[str, Any]:
    try:
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size > MAX_JSON_BYTES
        ):
            raise ScaleReadinessError("producer_jobs_result_invalid")
        value = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda item: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {item}")
            ),
        )
    except ScaleReadinessError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScaleReadinessError("producer_jobs_result_invalid") from exc
    if not isinstance(value, list) or not value:
        raise ScaleReadinessError("producer_jobs_result_invalid")
    jobs: list[Any] = []
    seen_job_ids: set[int] = set()
    expected_total_count: int | None = None
    for page in value:
        page_total = (
            exact_int(page.get("total_count")) if isinstance(page, dict) else None
        )
        if (
            not isinstance(page, dict)
            or page_total is None
            or page_total < 0
            or not isinstance(page.get("jobs"), list)
        ):
            raise ScaleReadinessError("producer_jobs_result_invalid")
        if expected_total_count is None:
            expected_total_count = page_total
        elif page_total != expected_total_count:
            raise ScaleReadinessError("producer_jobs_result_invalid")
        for candidate in page["jobs"]:
            if not isinstance(candidate, dict):
                raise ScaleReadinessError("producer_jobs_result_invalid")
            candidate_id = exact_int(candidate.get("id"))
            if (
                candidate_id is None
                or candidate_id <= 0
                or candidate_id in seen_job_ids
            ):
                raise ScaleReadinessError("producer_jobs_result_invalid")
            seen_job_ids.add(candidate_id)
            jobs.append(candidate)
    if expected_total_count != len(jobs):
        raise ScaleReadinessError("producer_jobs_result_invalid")
    matches = [
        job
        for job in jobs
        if isinstance(job, dict) and job.get("name") == PRODUCER_JOB_NAME
    ]
    if len(matches) != 1:
        raise ScaleReadinessError("producer_job_identity_invalid")
    job = matches[0]
    job_id = exact_int(job.get("id"))
    runner_id = exact_int(job.get("runner_id"))
    runner_group_id = exact_int(job.get("runner_group_id"))
    labels = job.get("labels")
    if (
        exact_int(job.get("run_id")) != producer_run_id
        or job.get("head_sha") != source_digest
        or job.get("conclusion") != "success"
        or job_id is None
        or job_id <= 0
        or runner_id is None
        or runner_id <= 0
        or runner_group_id is None
        or runner_group_id <= 0
        or not isinstance(job.get("runner_name"), str)
        or not SAFE_ID_RE.fullmatch(job["runner_name"])
        or job.get("runner_group_name") != PRODUCER_RUNNER_GROUP
        or not isinstance(labels, list)
        or any(not isinstance(label, str) for label in labels)
        or len(labels) != len(set(labels))
        or any(not SAFE_ID_RE.fullmatch(label) for label in labels)
        or not {"self-hosted", "Windows", "X64"}.issubset(set(labels))
    ):
        raise ScaleReadinessError("producer_job_identity_invalid")
    return {
        "job_id": job_id,
        "job_name": job["name"],
        "runner_id": runner_id,
        "runner_name": job["runner_name"],
        "runner_group_id": runner_group_id,
        "runner_group_name": job["runner_group_name"],
        "labels": sorted(set(labels)),
        "source_sha": job["head_sha"],
    }


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_consumer_actions_environment(
    *,
    run_id: int,
    run_attempt: int,
    actor: str,
    source_sha: str,
) -> None:
    expected = {
        "GITHUB_REPOSITORY": CONSUMER_REPOSITORY,
        "GITHUB_WORKFLOW": CONSUMER_WORKFLOW,
        "GITHUB_RUN_ID": str(run_id),
        "GITHUB_RUN_ATTEMPT": str(run_attempt),
        "GITHUB_ACTOR": actor,
        "GITHUB_SHA": source_sha,
        "GITHUB_REF": "refs/heads/main",
    }
    if any(os.environ.get(name) != value for name, value in expected.items()):
        raise ScaleReadinessError("consumer_actions_context_invalid")


def extract_archive(archive: Path, destination: Path) -> None:
    """Extract the exact bounded evidence bundle without ZIP path traversal."""
    expected = {"manifest.json", *(f"rung-{count}.json" for count in RUNGS)}
    try:
        if (
            not archive.is_file()
            or archive.is_symlink()
            or archive.stat().st_size > MAX_ARCHIVE_BYTES
        ):
            raise ScaleReadinessError("evidence_archive_invalid")
        if destination.exists():
            raise ScaleReadinessError("evidence_destination_not_empty")
        with zipfile.ZipFile(archive) as bundle:
            infos = bundle.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)) or set(names) != expected:
                raise ScaleReadinessError("evidence_archive_contents_invalid")
            for info in infos:
                unix_mode = info.external_attr >> 16
                if (
                    info.is_dir()
                    or info.flag_bits & 0x1
                    or info.file_size > MAX_JSON_BYTES
                    or info.compress_size > MAX_ARCHIVE_BYTES
                    or (unix_mode & 0o170000) == 0o120000
                ):
                    raise ScaleReadinessError("evidence_archive_entry_invalid")
            destination.mkdir(parents=True, exist_ok=True)
            for info in infos:
                payload = bundle.read(info)
                if len(payload) != info.file_size:
                    raise ScaleReadinessError("evidence_archive_entry_invalid")
                (destination / info.filename).write_bytes(payload)
    except ScaleReadinessError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, ValueError) as exc:
        raise ScaleReadinessError("evidence_archive_invalid") from exc


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


def remote_core_head() -> str:
    git = shutil.which("git")
    if not git:
        raise ScaleReadinessError("core_remote_head_unavailable")
    safe_path = str(Path(git).parent)
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    try:
        result = subprocess.run(
            [git, "ls-remote", "--exit-code", CORE_REMOTE, f"refs/heads/{CORE_BRANCH}"],
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
            timeout=30,
            env={
                "PATH": safe_path,
                "SystemRoot": system_root,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "NUL" if sys.platform == "win32" else "/dev/null",
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise ScaleReadinessError("core_remote_head_unavailable") from exc
    fields = result.stdout.split()
    if (
        result.returncode != 0
        or len(fields) != 2
        or not SHA1_RE.fullmatch(fields[0].lower())
    ):
        raise ScaleReadinessError("core_remote_head_unavailable")
    return fields[0].lower()


def expected_roles(provider_counts: dict[str, int]) -> set[str]:
    return {
        f"real{provider}-{ordinal}"
        for provider, count in provider_counts.items()
        for ordinal in range(1, count + 1)
    }


def expected_ack(provider: str, role: str, nonce: str) -> str:
    return f"ACK_REAL_VENDOR provider={provider} role={role} nonce={nonce}"


def validate_workflow_context(
    value: Any,
    *,
    expected_ecosystem_sha: str,
    expected_producer_run_id: int,
    expected_producer_run_attempt: int,
    expected_producer_actor: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScaleReadinessError("producer_context_invalid")
    require_exact_keys(
        value,
        {
            "repository",
            "workflow",
            "ref",
            "producer_run_id",
            "producer_run_attempt",
            "actor",
            "ecosystem_contract_sha",
            "core_head_sha",
        },
        "producer_context_invalid",
    )
    expected = {
        "repository": "rblake2320/selfconnect",
        "workflow": PRODUCER_WORKFLOW,
        "ref": "refs/heads/master",
        "producer_run_id": expected_producer_run_id,
        "producer_run_attempt": expected_producer_run_attempt,
        "actor": expected_producer_actor,
        "ecosystem_contract_sha": expected_ecosystem_sha,
    }
    for name, wanted in expected.items():
        actual = value.get(name)
        if name in {"producer_run_id", "producer_run_attempt"}:
            actual = exact_int(actual)
        if actual != wanted:
            raise ScaleReadinessError("producer_context_invalid")
    if (
        exact_int(value.get("producer_run_attempt")) is None
        or value["producer_run_attempt"] <= 0
    ):
        raise ScaleReadinessError("producer_context_invalid")
    if not isinstance(value.get("actor"), str) or not SAFE_ID_RE.fullmatch(
        value["actor"]
    ):
        raise ScaleReadinessError("producer_context_invalid")
    return value


def validate_requested_runner_config(value: Any) -> dict[str, str]:
    expected = {
        "environment": PRODUCER_ENVIRONMENT,
        "runner_group": PRODUCER_RUNNER_GROUP,
    }
    if value != expected:
        raise ScaleReadinessError("requested_runner_config_invalid")
    return expected


def validate_code_identity(value: Any, core_head: str) -> None:
    if not isinstance(value, dict):
        raise ScaleReadinessError("producer_code_identity_invalid")
    require_exact_keys(
        value,
        {
            "core_remote",
            "core_branch",
            "core_head_sha",
            "fresh_detached_checkout",
            "git_config_cleared",
            "python_env_cleared",
            "core_tree_sha256",
            "producer_sha256",
            "guard_module_sha256",
        },
        "producer_code_identity_invalid",
    )
    exact = {
        "core_remote": CORE_REMOTE,
        "core_branch": CORE_BRANCH,
        "core_head_sha": core_head,
        "fresh_detached_checkout": True,
        "git_config_cleared": True,
        "python_env_cleared": True,
    }
    for name, wanted in exact.items():
        if value.get(name) != wanted:
            raise ScaleReadinessError("producer_code_identity_invalid")
    for name in ("core_tree_sha256", "producer_sha256", "guard_module_sha256"):
        digest = value.get(name)
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ScaleReadinessError("producer_code_identity_invalid")


def validate_provider_pins(value: Any) -> None:
    if value != PROVIDER_PINS:
        raise ScaleReadinessError("provider_cli_policy_not_pinned")


def expected_argv_projection(provider: str, prompt: str) -> list[str]:
    if provider == "codex":
        return [
            "codex.exe",
            "exec",
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--ignore-user-config",
            prompt,
        ]
    if provider == "claude":
        return [
            "claude.exe",
            "--print",
            "--bare",
            "--safe-mode",
            "--permission-mode",
            "plan",
            "--tools",
            "",
            prompt,
        ]
    if provider == "gemini":
        return [
            "node.exe",
            "gemini.js",
            "--prompt",
            prompt,
            "--approval-mode",
            "plan",
            "--sandbox",
            "--admin-policy",
            "gemini-deny-all.toml",
        ]
    raise ScaleReadinessError("cli_invocation_invalid")


def validate_invocation(value: Any, provider: str, prompt: str) -> None:
    if not isinstance(value, dict):
        raise ScaleReadinessError("cli_invocation_invalid")
    require_exact_keys(
        value,
        {
            "provider",
            "exit_code",
            "actual_argv_projection",
            "actual_environment_names",
            "observed_cli_version",
            "observed_help_sha256",
            "observed_entrypoint_sha256",
            "observed_provider_exe_name",
        },
        "cli_invocation_invalid",
    )
    if value.get("provider") != provider or value.get("exit_code") != 0:
        raise ScaleReadinessError("cli_invocation_invalid")
    pin = PROVIDER_PINS[provider]
    for name in (
        "observed_cli_version",
        "observed_help_sha256",
        "observed_entrypoint_sha256",
        "observed_provider_exe_name",
    ):
        pin_name = name.replace("observed_", "expected_")
        if value.get(name) != pin[pin_name]:
            raise ScaleReadinessError("provider_invocation_not_pinned")
    if value.get("actual_environment_names") != PROVIDER_ENV_NAMES[provider]:
        raise ScaleReadinessError("provider_env_not_isolated")
    argv = value.get("actual_argv_projection")
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        raise ScaleReadinessError("cli_invocation_invalid")
    if FORBIDDEN_MODE_TOKENS.intersection(argv):
        raise ScaleReadinessError("provider_mode_not_restricted")
    if argv != expected_argv_projection(provider, prompt):
        raise ScaleReadinessError("provider_actual_argv_invalid")


def validate_guard_assertion(
    value: Any, *, provider: str, role: str, nonce: str
) -> None:
    if not isinstance(value, dict):
        raise ScaleReadinessError("guard_assertion_invalid")
    require_exact_keys(value, {"claim", "digest"}, "guard_assertion_invalid")
    claim = value.get("claim")
    digest = value.get("digest")
    if not isinstance(claim, dict) or not isinstance(digest, str):
        raise ScaleReadinessError("guard_assertion_invalid")
    require_exact_keys(
        claim,
        {
            "pre_guard_ok",
            "post_guard_ok",
            "spawn_alive_during_guard",
            "provider_in_spawn_tree",
            "same_session",
            "tree_root_pid",
            "provider_pid",
            "window_pid",
            "session_id",
            "class_name",
            "exe_name",
            "title_sha256",
            "process_tree_projection",
            "process_tree_sha256",
            "provider_entrypoint_sha256",
        },
        "guard_assertion_invalid",
    )
    if not SHA256_RE.fullmatch(digest) or sha256_bytes(canonical_json(claim)) != digest:
        raise ScaleReadinessError("guard_digest_invalid")
    required_true = (
        "pre_guard_ok",
        "post_guard_ok",
        "spawn_alive_during_guard",
        "provider_in_spawn_tree",
        "same_session",
    )
    if any(claim.get(name) is not True for name in required_true):
        raise ScaleReadinessError("guard_assertion_invalid")
    for name in ("tree_root_pid", "provider_pid", "window_pid", "session_id"):
        if exact_int(claim.get(name)) is None or claim[name] <= 0:
            raise ScaleReadinessError("guard_assertion_invalid")
    if (
        claim["tree_root_pid"] != claim["window_pid"]
        or claim["provider_pid"] == claim["window_pid"]
    ):
        raise ScaleReadinessError("guard_assertion_invalid")
    if claim.get("class_name") != "CASCADIA_HOSTING_WINDOW_CLASS":
        raise ScaleReadinessError("guard_assertion_invalid")
    if claim.get("exe_name") != "WindowsTerminal.exe":
        raise ScaleReadinessError("guard_assertion_invalid")
    title_hash = sha256_bytes(f"SC_SCALE {provider} {role} {nonce}".encode())
    if claim.get("title_sha256") != title_hash:
        raise ScaleReadinessError("guard_assertion_invalid")
    projection = claim.get("process_tree_projection")
    if not isinstance(projection, list) or not (3 <= len(projection) <= 64):
        raise ScaleReadinessError("guard_assertion_invalid")
    seen_pids: set[int] = set()
    parent_by_pid: dict[int, int | None] = {}
    exe_by_pid: dict[int, str] = {}
    for node in projection:
        if not isinstance(node, dict) or set(node) != {"pid", "parent_pid", "exe_name"}:
            raise ScaleReadinessError("guard_assertion_invalid")
        pid = exact_int(node.get("pid"))
        parent_pid = node.get("parent_pid")
        if (
            pid is None
            or pid <= 0
            or pid in seen_pids
            or (
                parent_pid is not None
                and (exact_int(parent_pid) is None or parent_pid <= 0)
            )
            or not isinstance(node.get("exe_name"), str)
            or not SAFE_ID_RE.fullmatch(node["exe_name"])
        ):
            raise ScaleReadinessError("guard_assertion_invalid")
        seen_pids.add(pid)
        parent_by_pid[pid] = parent_pid
        exe_by_pid[pid] = node["exe_name"]
    if [node["pid"] for node in projection] != sorted(seen_pids):
        raise ScaleReadinessError("guard_assertion_invalid")
    root = claim["tree_root_pid"]
    if (
        parent_by_pid.get(root) is not None
        or exe_by_pid.get(root) != "WindowsTerminal.exe"
    ):
        raise ScaleReadinessError("guard_assertion_invalid")
    if any(
        pid != root and parent not in seen_pids for pid, parent in parent_by_pid.items()
    ):
        raise ScaleReadinessError("guard_assertion_invalid")
    provider_pid = claim["provider_pid"]
    if exe_by_pid.get(provider_pid) != PROVIDER_EXE_NAMES[provider]:
        raise ScaleReadinessError("guard_assertion_invalid")
    for start_pid in seen_pids:
        cursor = start_pid
        visited: set[int] = set()
        while cursor != root:
            if cursor in visited or parent_by_pid.get(cursor) not in seen_pids:
                raise ScaleReadinessError("guard_assertion_invalid")
            visited.add(cursor)
            cursor = parent_by_pid[cursor]  # type: ignore[assignment]
    tree = claim.get("process_tree_sha256")
    if (
        not isinstance(tree, str)
        or not SHA256_RE.fullmatch(tree)
        or tree != sha256_bytes(canonical_json(projection))
    ):
        raise ScaleReadinessError("guard_assertion_invalid")
    if (
        claim.get("provider_entrypoint_sha256")
        != PROVIDER_PINS[provider]["expected_entrypoint_sha256"]
    ):
        raise ScaleReadinessError("guard_assertion_invalid")


def validate_rung(
    value: dict[str, Any], agent_count: int
) -> tuple[datetime, datetime, set[str], str]:
    if value.get("schema") == LEGACY_SCHEMA:
        raise ScaleReadinessError("legacy_unsafe_producer_rejected")
    if value.get("schema") != RUNG_SCHEMA:
        raise ScaleReadinessError("rung_schema_invalid")
    if "real_model_calls_total" in value or "model_call_accounting" in value:
        raise ScaleReadinessError("unsupported_model_call_claim")
    require_exact_keys(
        value,
        {
            "schema",
            "run_id",
            "verdict",
            "agent_count",
            "provider_counts",
            "logical_simulation",
            "visible_windows",
            "started_at_utc",
            "completed_at_utc",
            "cli_invocation_accounting",
            "agents",
        },
        "rung_schema_invalid",
    )
    if (
        value.get("verdict") != "PASS"
        or exact_int(value.get("agent_count")) != agent_count
    ):
        raise ScaleReadinessError("rung_not_passed")
    providers = RUNGS[agent_count]
    if not exact_provider_counts(value.get("provider_counts"), providers):
        raise ScaleReadinessError("provider_counts_mismatch")
    if (
        value.get("logical_simulation") is not False
        or value.get("visible_windows") is not True
    ):
        raise ScaleReadinessError("real_visible_agents_required")
    accounting = value.get("cli_invocation_accounting")
    if (
        not isinstance(accounting, dict)
        or set(accounting) != {"cli_invocations_total"}
        or exact_int(accounting.get("cli_invocations_total")) != agent_count
    ):
        raise ScaleReadinessError("cli_invocation_accounting_invalid")
    started = parse_utc(value.get("started_at_utc"))
    completed = parse_utc(value.get("completed_at_utc"))
    if completed <= started or completed - started > MAX_RUNG_DURATION:
        raise ScaleReadinessError("rung_time_invalid")

    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ScaleReadinessError("run_id_invalid")
    agents = value.get("agents")
    if not isinstance(agents, list) or len(agents) != agent_count:
        raise ScaleReadinessError("agent_evidence_count_mismatch")
    roles = expected_roles(providers)
    seen_roles: set[str] = set()
    nonces: set[str] = set()
    agent_intervals: list[tuple[datetime, datetime]] = []
    for agent in agents:
        if not isinstance(agent, dict):
            raise ScaleReadinessError("agent_evidence_invalid")
        require_exact_keys(
            agent,
            {
                "provider",
                "role",
                "nonce",
                "nonce_sha256",
                "expected_sha256",
                "observed_acks",
                "status",
                "provider_outcome",
                "invocation",
                "producer_guard_assertion",
                "started_at_utc",
                "completed_at_utc",
            },
            "agent_evidence_invalid",
        )
        provider, role, nonce = (
            agent.get("provider"),
            agent.get("role"),
            agent.get("nonce"),
        )
        provider_roles = (
            {
                f"real{provider}-{ordinal}"
                for ordinal in range(1, providers.get(provider, 0) + 1)
            }
            if isinstance(provider, str)
            else set()
        )
        if (
            not isinstance(provider, str)
            or not isinstance(role, str)
            or provider not in providers
            or role not in provider_roles
            or role in seen_roles
        ):
            raise ScaleReadinessError("agent_role_invalid")
        if (
            not isinstance(nonce, str)
            or not NONCE_RE.fullmatch(nonce)
            or nonce in nonces
        ):
            raise ScaleReadinessError("agent_nonce_invalid")
        seen_roles.add(role)
        nonces.add(nonce)
        expected = expected_ack(provider, role, nonce)
        agent_started = parse_utc(agent.get("started_at_utc"))
        agent_completed = parse_utc(agent.get("completed_at_utc"))
        if not (started <= agent_started < agent_completed <= completed):
            raise ScaleReadinessError("agent_time_invalid")
        agent_intervals.append((agent_started, agent_completed))
        if agent.get("nonce_sha256") != sha256_bytes(nonce.encode()):
            raise ScaleReadinessError("agent_hash_invalid")
        if agent.get("expected_sha256") != sha256_bytes(expected.encode()):
            raise ScaleReadinessError("agent_hash_invalid")
        if agent.get("status") != "pass":
            raise ScaleReadinessError("agent_status_invalid")
        observations = agent.get("observed_acks")
        if not isinstance(observations, dict) or set(observations) != {
            "process_stdout",
            "rendered_terminal_copy",
        }:
            raise ScaleReadinessError("observed_ack_invalid")
        observation_policy = {
            "process_stdout": "provider_stdout_pipe",
            "rendered_terminal_copy": "terminal_render_of_captured_stdout",
        }
        observation_times: dict[str, datetime] = {}
        observation_ids: set[str] = set()
        for source, observation in observations.items():
            required_observation_keys = {
                "event_id",
                "source",
                "provenance",
                "sha256",
                "captured_at_utc",
            }
            if source == "rendered_terminal_copy":
                required_observation_keys.add("derivative_of_event_id")
            if (
                not isinstance(observation, dict)
                or set(observation) != required_observation_keys
            ):
                raise ScaleReadinessError("observed_ack_invalid")
            captured = parse_utc(observation.get("captured_at_utc"))
            event_id = observation.get("event_id")
            if (
                not isinstance(event_id, str)
                or not NONCE_RE.fullmatch(event_id)
                or event_id in observation_ids
                or observation.get("source") != source
                or observation.get("provenance") != observation_policy[source]
                or observation.get("sha256") != sha256_bytes(expected.encode())
                or not (agent_started <= captured <= agent_completed)
            ):
                raise ScaleReadinessError("observed_ack_invalid")
            observation_ids.add(event_id)
            observation_times[source] = captured
        if (
            observations["rendered_terminal_copy"].get("derivative_of_event_id")
            != observations["process_stdout"].get("event_id")
            or observation_times["process_stdout"]
            >= observation_times["rendered_terminal_copy"]
        ):
            raise ScaleReadinessError("observed_ack_derivation_invalid")
        outcome = agent.get("provider_outcome")
        if not isinstance(outcome, dict) or outcome != {
            "auth_failed": False,
            "quota_exceeded": False,
        }:
            raise ScaleReadinessError("provider_outcome_invalid")
        prompt = f"Reply with exactly this one line and nothing else: {expected}"
        validate_invocation(agent.get("invocation"), provider, prompt)
        validate_guard_assertion(
            agent.get("producer_guard_assertion"),
            provider=provider,
            role=role,
            nonce=nonce,
        )
    if seen_roles != roles:
        raise ScaleReadinessError("agent_role_invalid")
    if max(start for start, _ in agent_intervals) > min(
        end for _, end in agent_intervals
    ):
        raise ScaleReadinessError("agent_concurrency_not_established")
    return started, completed, nonces, run_id


def validate_bundle(
    bundle: Path,
    *,
    expected_ecosystem_sha: str,
    expected_producer_run_id: int,
    expected_producer_run_attempt: int = 1,
    expected_producer_actor: str = "restricted-producer",
    producer_archive_sha256: str,
    verified_attestation: dict[str, Any],
    externally_observed_runner: dict[str, Any],
    consumer_run_id: int,
    consumer_run_attempt: int,
    consumer_actor: str,
    now: datetime | None = None,
    max_evidence_age_hours: float = DEFAULT_MAX_EVIDENCE_AGE_HOURS,
) -> dict[str, Any]:
    if not SHA1_RE.fullmatch(expected_ecosystem_sha):
        raise ScaleReadinessError("ecosystem_sha_invalid")
    if expected_producer_run_id <= 0:
        raise ScaleReadinessError("producer_run_id_invalid")
    if expected_producer_run_attempt <= 0:
        raise ScaleReadinessError("producer_run_attempt_invalid")
    if not SAFE_ID_RE.fullmatch(expected_producer_actor):
        raise ScaleReadinessError("producer_actor_invalid")
    if not SHA256_RE.fullmatch(producer_archive_sha256):
        raise ScaleReadinessError("producer_archive_digest_invalid")
    if not isinstance(verified_attestation, dict) or not SHA256_RE.fullmatch(
        str(verified_attestation.get("result_sha256", ""))
    ):
        raise ScaleReadinessError("attestation_result_digest_invalid")
    if not isinstance(externally_observed_runner, dict):
        raise ScaleReadinessError("producer_job_identity_invalid")
    if (
        consumer_run_id <= 0
        or consumer_run_attempt <= 0
        or not SAFE_ID_RE.fullmatch(consumer_actor)
    ):
        raise ScaleReadinessError("consumer_context_invalid")
    if (
        not math.isfinite(max_evidence_age_hours)
        or max_evidence_age_hours <= 0
        or max_evidence_age_hours > MAX_EVIDENCE_AGE_HOURS
    ):
        raise ScaleReadinessError("evidence_age_policy_invalid")
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ScaleReadinessError("manifest_missing")
    expected_files = {"manifest.json", *(f"rung-{count}.json" for count in RUNGS)}
    try:
        entries = {item.name for item in bundle.iterdir()}
    except OSError as exc:
        raise ScaleReadinessError("evidence_io_failed") from exc
    if entries != expected_files:
        raise ScaleReadinessError("bundle_contents_invalid")

    manifest = load_json(manifest_path)
    if manifest.get("schema") != SCHEMA:
        raise ScaleReadinessError("manifest_schema_invalid")
    require_exact_keys(
        manifest,
        {
            "schema",
            "generated_at",
            "producer_context",
            "requested_runner_config",
            "code_identity",
            "provider_pins",
            "rungs",
        },
        "manifest_schema_invalid",
    )
    evaluated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    generated_at = parse_utc(manifest.get("generated_at"))
    if generated_at > evaluated_at + MAX_FUTURE_SKEW:
        raise ScaleReadinessError("evidence_from_future")
    if evaluated_at - generated_at > timedelta(hours=max_evidence_age_hours):
        raise ScaleReadinessError("evidence_stale")

    workflow_context = validate_workflow_context(
        manifest.get("producer_context"),
        expected_ecosystem_sha=expected_ecosystem_sha.lower(),
        expected_producer_run_id=expected_producer_run_id,
        expected_producer_run_attempt=expected_producer_run_attempt,
        expected_producer_actor=expected_producer_actor,
    )
    requested_runner_config = validate_requested_runner_config(
        manifest.get("requested_runner_config")
    )
    core_head = remote_core_head()
    if workflow_context.get("core_head_sha") != core_head:
        raise ScaleReadinessError("evidence_wrong_core_head")
    validate_code_identity(manifest.get("code_identity"), core_head)
    validate_provider_pins(manifest.get("provider_pins"))

    rows = manifest.get("rungs")
    if not isinstance(rows, list) or len(rows) != len(RUNGS):
        raise ScaleReadinessError("rung_manifest_invalid")
    intervals: list[tuple[int, datetime, datetime]] = []
    all_nonces: set[str] = set()
    run_ids: set[str] = set()
    observed: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ScaleReadinessError("rung_manifest_invalid")
        require_exact_keys(
            row,
            {"agent_count", "file", "sha256", "size_bytes"},
            "rung_manifest_invalid",
        )
        count = exact_int(row.get("agent_count"))
        if count not in RUNGS or count in observed:
            raise ScaleReadinessError("rung_manifest_invalid")
        observed.add(count)
        path = bundle / f"rung-{count}.json"
        if row.get("file") != path.name or not path.is_file() or path.is_symlink():
            raise ScaleReadinessError("rung_file_invalid")
        if (
            row.get("sha256") != sha256_file(path)
            or exact_int(row.get("size_bytes")) != path.stat().st_size
        ):
            raise ScaleReadinessError("rung_artifact_mismatch")
        started, completed, nonces, run_id = validate_rung(load_json(path), count)
        if nonces & all_nonces:
            raise ScaleReadinessError("cross_rung_nonce_reuse")
        if run_id in run_ids:
            raise ScaleReadinessError("cross_rung_run_id_reuse")
        all_nonces.update(nonces)
        run_ids.add(run_id)
        intervals.append((count, started, completed))
    if observed != set(RUNGS):
        raise ScaleReadinessError("rung_manifest_invalid")
    intervals.sort()
    for index, (count, started, completed) in enumerate(intervals):
        if completed > generated_at or evaluated_at - completed > timedelta(
            hours=max_evidence_age_hours
        ):
            raise ScaleReadinessError("rung_time_invalid")
        if index and started < intervals[index - 1][2]:
            raise ScaleReadinessError("rung_order_invalid")
        if count not in RUNGS:
            raise ScaleReadinessError("rung_manifest_invalid")
    return {
        "schema": SCHEMA,
        "ok": True,
        "status": "ready",
        "evaluated_at": evaluated_at.isoformat(),
        "generated_at": generated_at.isoformat(),
        "core_head_sha": core_head,
        "ecosystem_contract_sha": expected_ecosystem_sha.lower(),
        "producer_run_id": expected_producer_run_id,
        "producer_run_attempt": expected_producer_run_attempt,
        "producer_actor": expected_producer_actor,
        "rungs": sorted(observed),
        "producer_archive_sha256": producer_archive_sha256,
        "verified_attestation": verified_attestation,
        "producer_runner_context": {
            "requested": requested_runner_config,
            "externally_observed": externally_observed_runner,
            "attested_runner_environment": verified_attestation["certificate"][
                "runnerEnvironment"
            ],
        },
        "consumer_context": {
            "repository": CONSUMER_REPOSITORY,
            "workflow": CONSUMER_WORKFLOW,
            "run_id": consumer_run_id,
            "run_attempt": consumer_run_attempt,
            "actor": consumer_actor,
            "source_sha": expected_ecosystem_sha.lower(),
        },
    }


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--expected-ecosystem-sha", required=True)
    verify.add_argument("--expected-producer-run-id", type=int, required=True)
    verify.add_argument("--expected-producer-run-attempt", type=int, required=True)
    verify.add_argument("--expected-producer-actor", required=True)
    verify.add_argument("--expected-producer-source-sha", required=True)
    verify.add_argument("--producer-archive", type=Path, required=True)
    verify.add_argument("--verified-attestation-result", type=Path, required=True)
    verify.add_argument("--producer-jobs-result", type=Path, required=True)
    verify.add_argument("--consumer-run-id", type=int, required=True)
    verify.add_argument("--consumer-run-attempt", type=int, required=True)
    verify.add_argument("--consumer-actor", required=True)
    verify.add_argument("--report-file", type=Path)
    verify.add_argument(
        "--max-evidence-age-hours", type=float, default=DEFAULT_MAX_EVIDENCE_AGE_HOURS
    )
    extract = commands.add_parser("extract")
    extract.add_argument("--archive", type=Path, required=True)
    extract.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "extract":
        try:
            extract_archive(args.archive.resolve(), args.destination.resolve())
        except ScaleReadinessError as exc:
            print(
                json.dumps(
                    {"schema": SCHEMA, "ok": False, "status": exc.status}, indent=2
                )
            )
            return 2
        print(
            json.dumps({"schema": SCHEMA, "ok": True, "status": "extracted"}, indent=2)
        )
        return 0
    try:
        validate_consumer_actions_environment(
            run_id=args.consumer_run_id,
            run_attempt=args.consumer_run_attempt,
            actor=args.consumer_actor,
            source_sha=args.expected_ecosystem_sha,
        )
        archive_sha256 = sha256_file(args.producer_archive.resolve())
        attestation = parse_attestation_result(
            args.verified_attestation_result.resolve(),
            archive_sha256=archive_sha256,
            source_digest=args.expected_producer_source_sha,
            producer_run_id=args.expected_producer_run_id,
            producer_run_attempt=args.expected_producer_run_attempt,
        )
        externally_observed_runner = parse_producer_jobs_result(
            args.producer_jobs_result.resolve(),
            producer_run_id=args.expected_producer_run_id,
            source_digest=args.expected_producer_source_sha,
        )
        report = validate_bundle(
            args.bundle.resolve(),
            expected_ecosystem_sha=args.expected_ecosystem_sha,
            expected_producer_run_id=args.expected_producer_run_id,
            expected_producer_run_attempt=args.expected_producer_run_attempt,
            expected_producer_actor=args.expected_producer_actor,
            producer_archive_sha256=archive_sha256,
            verified_attestation=attestation,
            externally_observed_runner=externally_observed_runner,
            consumer_run_id=args.consumer_run_id,
            consumer_run_attempt=args.consumer_run_attempt,
            consumer_actor=args.consumer_actor,
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
