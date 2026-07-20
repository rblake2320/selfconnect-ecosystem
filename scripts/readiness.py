#!/usr/bin/env python3
"""SelfConnect ecosystem readiness checks.

This script is intentionally read-only. It turns the remaining external gates
into one repeatable command so the status is not reconstructed from transcripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import winreg
else:  # pragma: no cover - exercised on Windows in production
    winreg = None


@dataclass(frozen=True)
class RepoSpec:
    path: str
    remote_url: str
    default_branch: str


REPOS = {
    "selfconnect": RepoSpec(
        "selfconnect", "https://github.com/rblake2320/selfconnect", "master"
    ),
    "selfconnect-enterprise": RepoSpec(
        "selfconnect-enterprise",
        "https://github.com/rblake2320/selfconnect-enterprise",
        "master",
    ),
    "selfconnect-ecosystem": RepoSpec(
        "selfconnect-ecosystem",
        "https://github.com/rblake2320/selfconnect-ecosystem",
        "main",
    ),
    "selfconnect-terminal": RepoSpec(
        "selfconnect-terminal",
        "https://github.com/rblake2320/selfconnect-terminal",
        "main",
    ),
    "selfconnect-linux": RepoSpec(
        "selfconnect-linux",
        "https://github.com/rblake2320/selfconnect-linux",
        "main",
    ),
    "selfconnect-alt": RepoSpec(
        "selfconnect-alt",
        "https://github.com/rblake2320/selfconnect-alt",
        "master",
    ),
    "bpc-protocol": RepoSpec(
        "bpc-protocol", "https://github.com/rblake2320/bpc-protocol", "master"
    ),
    "tsk-protocol": RepoSpec(
        "tsk-protocol", "https://github.com/rblake2320/tsk-protocol", "master"
    ),
    "patent-portfolio": RepoSpec(
        "patent-portfolio",
        "https://github.com/rblake2320/patent-portfolio",
        "master",
    ),
}

GEMINI_ENV_VARS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
    "GOOGLE_GENAI_USE_ENTERPRISE",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "CLOUDSDK_CONFIG",
)

SIGNING_SECRETS = (
    "WINDOWS_SIGNING_CERT_BASE64",
    "WINDOWS_SIGNING_CERT_PASSWORD",
)

ISSUES = {
    "gemini": "https://github.com/rblake2320/selfconnect-ecosystem/issues/2",
    "tpm": "https://github.com/rblake2320/selfconnect-ecosystem/issues/3",
    "signing_secrets": "https://github.com/rblake2320/selfconnect-ecosystem/issues/4",
}

DEFAULT_MAX_EVIDENCE_AGE_HOURS = 168.0
MAX_EVIDENCE_AGE_HOURS = 168.0
MAX_FUTURE_SKEW = timedelta(minutes=5)
MSI_REPO = "rblake2320/selfconnect-enterprise"
MSI_WORKFLOW = "Build MSI Release Artifact"
MSI_ARTIFACT_NAME = "selfconnect-enterprise-msi"
EXPECTED_SUCCESS_STATUS = {
    "repos": "ready",
    "gemini": "ready",
    "tpm": "ready",
    "msi_workflow": "ready",
    "signing_secrets": "configured",
}


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def run_cmd(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> CmdResult:
    process_env = None
    if env is not None:
        process_env = os.environ.copy()
        process_env.update(env)
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            timeout=timeout,
            check=False,
            env=process_env,
        )
        return CmdResult(completed.returncode, completed.stdout.strip(), completed.stderr.strip())
    except FileNotFoundError as exc:
        return CmdResult(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CmdResult(124, stdout.strip(), stderr.strip() or "command timed out")
    except UnicodeError as exc:
        return CmdResult(126, "", f"command output was not valid UTF-8: {type(exc).__name__}")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def pka_root() -> Path:
    return Path(os.environ.get("PKA_ROOT", str(repo_root().parent))).resolve()


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


def git_repo_status(name: str, spec: RepoSpec, path: Path) -> dict[str, Any]:
    if not path.is_dir():
        return {"name": name, "path": str(path), "status": "missing", "ok": False}

    status = run_cmd(["git", "status", "--porcelain=v1", "--untracked-files=normal"], cwd=path)
    head = run_cmd(["git", "rev-parse", "HEAD"], cwd=path)
    branch = run_cmd(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=path)
    if status.returncode != 0 or head.returncode != 0 or branch.returncode != 0:
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "status": "git_query_failed",
            "error": "local git status, HEAD, or branch query failed",
        }

    if branch.stdout != spec.default_branch:
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "branch": branch.stdout,
            "expected_branch": spec.default_branch,
            "head": head.stdout,
            "dirty_count": len(status.stdout.splitlines()),
            "status": "wrong_branch",
        }

    remote = run_cmd(["git", "config", "--get", f"branch.{branch.stdout}.remote"], cwd=path)
    merge_ref = run_cmd(["git", "config", "--get", f"branch.{branch.stdout}.merge"], cwd=path)
    if remote.returncode != 0 or merge_ref.returncode != 0 or not remote.stdout or not merge_ref.stdout:
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "branch": branch.stdout,
            "head": head.stdout,
            "dirty_count": len(status.stdout.splitlines()),
            "status": "upstream_unavailable",
        }

    expected_ref = f"refs/heads/{spec.default_branch}"
    if merge_ref.stdout != expected_ref:
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "branch": branch.stdout,
            "head": head.stdout,
            "dirty_count": len(status.stdout.splitlines()),
            "remote": remote.stdout,
            "remote_ref": merge_ref.stdout,
            "expected_ref": expected_ref,
            "status": "wrong_upstream_branch",
        }

    remote_url = run_cmd(["git", "remote", "get-url", remote.stdout], cwd=path)
    if remote_url.returncode != 0 or not remote_url.stdout:
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "branch": branch.stdout,
            "head": head.stdout,
            "dirty_count": len(status.stdout.splitlines()),
            "status": "remote_identity_unavailable",
        }
    if normalize_remote_url(remote_url.stdout) != normalize_remote_url(spec.remote_url):
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "branch": branch.stdout,
            "head": head.stdout,
            "dirty_count": len(status.stdout.splitlines()),
            "remote": remote.stdout,
            "remote_url": remote_url.stdout,
            "expected_remote_url": spec.remote_url,
            "status": "wrong_remote_identity",
        }

    remote_head = run_cmd(
        ["git", "ls-remote", "--exit-code", spec.remote_url, expected_ref],
        cwd=path,
        timeout=30,
    )
    remote_lines = [line for line in remote_head.stdout.splitlines() if line.strip()]
    if remote_head.returncode != 0 or len(remote_lines) != 1:
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "branch": branch.stdout,
            "head": head.stdout,
            "dirty_count": len(status.stdout.splitlines()),
            "status": "remote_head_unavailable",
        }

    fields = remote_lines[0].split()
    if len(fields) != 2 or fields[1] != expected_ref:
        return {
            "name": name,
            "path": str(path),
            "ok": False,
            "branch": branch.stdout,
            "head": head.stdout,
            "dirty_count": len(status.stdout.splitlines()),
            "status": "remote_head_invalid",
        }

    dirty_lines = [line for line in status.stdout.splitlines() if line.strip()]
    remote_sha = fields[0]
    ok = not dirty_lines and head.stdout == remote_sha
    state = "clean" if ok else ("dirty" if dirty_lines else "remote_drift")
    return {
        "name": name,
        "path": str(path),
        "ok": ok,
        "branch": branch.stdout,
        "head": head.stdout,
        "remote": remote.stdout,
        "remote_url": spec.remote_url,
        "remote_ref": expected_ref,
        "remote_head": remote_sha,
        "dirty_count": len(dirty_lines),
        "status": state,
    }


def check_repos(root: Path) -> dict[str, Any]:
    repos = [
        git_repo_status(name, spec, root / spec.path)
        for name, spec in REPOS.items()
    ]
    ok = all(item["ok"] is True for item in repos)
    return {
        "ok": ok,
        "status": "ready" if ok else "repo_set_not_current",
        "repos": repos,
    }


def default_adc_paths() -> list[Path]:
    paths: list[Path] = []
    appdata = os.environ.get("APPDATA")
    home = Path.home()
    if appdata:
        paths.append(Path(appdata) / "gcloud" / "application_default_credentials.json")
    paths.append(home / ".config" / "gcloud" / "application_default_credentials.json")
    return paths


def windows_registry_env(name: str, scope: str) -> str:
    if winreg is None:
        return ""
    if scope == "User":
        hive = winreg.HKEY_CURRENT_USER
        subkey = "Environment"
    elif scope == "Machine":
        hive = winreg.HKEY_LOCAL_MACHINE
        subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    else:
        raise ValueError(f"unknown environment scope: {scope}")
    try:
        with winreg.OpenKey(hive, subkey) as key:
            value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return ""
    return str(value)


def env_presence(name: str) -> dict[str, dict[str, int | bool]]:
    values = {
        "process": os.environ.get(name, ""),
        "user": windows_registry_env(name, "User"),
        "machine": windows_registry_env(name, "Machine"),
    }
    return {
        scope: {"present": bool(value), "length": len(value)}
        for scope, value in values.items()
    }


def first_env_value(name: str) -> str:
    return (
        os.environ.get(name, "")
        or windows_registry_env(name, "User")
        or windows_registry_env(name, "Machine")
    )


def check_gemini() -> dict[str, Any]:
    gemini = shutil.which("gemini")
    gcloud = shutil.which("gcloud")
    version = None
    if gemini:
        result = run_cmd([gemini, "--version"], timeout=20)
        if result.returncode != 0 or not result.stdout:
            return {
                "ok": False,
                "status": "version_probe_failed",
                "gemini_path": gemini,
                "gcloud_path": gcloud,
            }
        version = result.stdout

    env = {name: env_presence(name) for name in GEMINI_ENV_VARS}
    adc = [{"path": str(path), "present": path.exists()} for path in default_adc_paths()]
    google_credentials_path = first_env_value("GOOGLE_APPLICATION_CREDENTIALS")
    google_credentials_file = bool(google_credentials_path and Path(google_credentials_path).exists())

    auth_sources = {
        "gemini_api_key": bool(first_env_value("GEMINI_API_KEY")),
        "google_api_key": bool(first_env_value("GOOGLE_API_KEY")),
        "credentials_file": google_credentials_file,
        "default_adc": any(item["present"] for item in adc),
    }
    auth_configured = any(auth_sources.values())
    if not gemini:
        return {
            "ok": False,
            "status": "cli_missing",
            "gemini_path": None,
            "gemini_version": None,
            "gcloud_path": gcloud,
            "env": env,
            "default_adc": adc,
            "auth_sources": auth_sources,
        }
    if not auth_configured:
        return {
            "ok": False,
            "status": "provider_auth_required",
            "gemini_path": gemini,
            "gemini_version": version,
            "gcloud_path": gcloud,
            "env": env,
            "default_adc": adc,
            "auth_sources": auth_sources,
        }

    nonce = f"SC_READINESS_{secrets.token_hex(16)}"
    prompt = f"Return exactly this token and no other text: {nonce}"
    probe = run_cmd(
        [
            gemini,
            "-p",
            prompt,
            "--output-format",
            "text",
            "--approval-mode",
            "plan",
        ],
        timeout=90,
    )
    if probe.returncode != 0:
        return {
            "ok": False,
            "status": "provider_probe_failed",
            "gemini_path": gemini,
            "gemini_version": version,
            "gcloud_path": gcloud,
            "env": env,
            "default_adc": adc,
            "auth_sources": auth_sources,
            "probe_returncode": probe.returncode,
        }
    if probe.stdout.strip() != nonce:
        return {
            "ok": False,
            "status": "provider_probe_mismatch",
            "gemini_path": gemini,
            "gemini_version": version,
            "gcloud_path": gcloud,
            "env": env,
            "default_adc": adc,
            "auth_sources": auth_sources,
        }
    return {
        "ok": True,
        "status": "ready",
        "gemini_path": gemini,
        "gemini_version": version,
        "gcloud_path": gcloud,
        "env": env,
        "default_adc": adc,
        "auth_sources": auth_sources,
        "probe": "exact_nonce_returned",
    }


def check_tpm(root: Path) -> dict[str, Any]:
    enterprise = root / "selfconnect-enterprise"
    if not enterprise.exists():
        return {"ok": False, "status": "missing_repo", "path": str(enterprise)}

    expected_public_key = os.environ.get(
        "READINESS_TPM_PUBLIC_KEY_SHA256", ""
    ).strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected_public_key) is None:
        return {
            "ok": False,
            "status": "missing_or_invalid_public_key_pin",
        }

    probe = (
        "import json; "
        "from enterprise.tpm_attestation import tpm_probe; "
        "print(json.dumps(tpm_probe(), default=str))"
    )
    result = run_cmd(
        [sys.executable, "-c", probe],
        cwd=enterprise,
        timeout=60,
        env={"SELFCONNECT_TPM_PUBLIC_KEY_SHA256": expected_public_key},
    )
    if result.returncode != 0:
        return {
            "ok": False,
            "status": "probe_error",
            "error": result.stderr or result.stdout,
        }
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "status": "bad_json", "error": type(exc).__name__}
    if not isinstance(data, dict):
        return {"ok": False, "status": "bad_json_shape"}
    digest_fields = (
        "claim_sha256",
        "nonce_sha256",
        "pcr_values_sha256",
        "public_key_sha256",
    )
    digests_valid = all(
        isinstance(data.get(key), str)
        and re.fullmatch(r"[0-9a-f]{64}", data[key].lower()) is not None
        for key in digest_fields
    )
    verified = (
        data.get("supported") is True
        and data.get("verified") is True
        and data.get("platform_key_bound") is True
        and data.get("replay_checked") is True
        and digests_valid
        and data.get("public_key_sha256", "").lower() == expected_public_key
        and isinstance(data.get("claim_size"), int)
        and data["claim_size"] > 0
        and isinstance(data.get("pcr_mask"), int)
        and data["pcr_mask"] > 0
        and isinstance(data.get("pcr_algorithm"), int)
        and data["pcr_algorithm"] > 0
    )
    safe_probe = {
        key: data.get(key)
        for key in (
            "supported",
            "verified",
            "platform_key_bound",
            "identity_key_bound",
            "manufacturer_chain_verified",
            "replay_checked",
            "claim_size",
            "claim_sha256",
            "public_key_sha256",
            "pcr_mask",
            "pcr_algorithm",
            "pcr_values_sha256",
            "error",
        )
        if key in data
    }
    return {
        "ok": verified,
        "status": "ready" if verified else "attestation_verification_failed",
        "probe": safe_probe,
    }


def parse_secret_names(output: str) -> set[str]:
    names: set[str] = set()
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        names.add(stripped.split()[0])
    return names


def check_signing_secrets() -> dict[str, Any]:
    gh = shutil.which("gh")
    if not gh:
        return {"ok": False, "status": "gh_missing", "gh_path": None}
    result = run_cmd([gh, "secret", "list", "--repo", "rblake2320/selfconnect-enterprise"], timeout=30)
    if result.returncode != 0:
        return {
            "ok": False,
            "status": "secret_list_failed",
            "gh_path": gh,
            "error": result.stderr or result.stdout,
        }
    names = parse_secret_names(result.stdout)
    present = {name: name in names for name in SIGNING_SECRETS}
    return {
        "ok": all(present.values()),
        "status": "configured" if all(present.values()) else "missing_signing_secrets",
        "gh_path": gh,
        "present": present,
        "boundary": "name_presence_only; signed artifact evidence is checked separately",
    }


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def normalize_sha256_thumbprint(value: str) -> str | None:
    normalized = re.sub(r"[\s:-]", "", value).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", normalized):
        return None
    return normalized


def verify_authenticode(
    msi_path: Path,
    *,
    expected_signer_sha256: str,
) -> dict[str, Any]:
    expected = normalize_sha256_thumbprint(expected_signer_sha256)
    if expected is None:
        return {"ok": False, "status": "signer_policy_invalid"}
    if sys.platform != "win32":
        return {"ok": False, "status": "authenticode_platform_unsupported"}

    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        return {"ok": False, "status": "powershell_missing"}

    script = r"""
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1') -Force
function Get-CertSha256($Cert) {
    if ($null -eq $Cert) { return $null }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($sha.ComputeHash($Cert.RawData))).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
}
$signature = Get-AuthenticodeSignature -LiteralPath $env:SC_READINESS_ARTIFACT
[ordered]@{
    status = $signature.Status.ToString()
    signer_sha256 = (Get-CertSha256 $signature.SignerCertificate)
    signer_subject = $(if ($null -eq $signature.SignerCertificate) {
        $null
    } else {
        $signature.SignerCertificate.Subject
    })
    timestamped = $null -ne $signature.TimeStamperCertificate
    timestamp_signer_sha256 = (Get-CertSha256 $signature.TimeStamperCertificate)
} | ConvertTo-Json -Compress
"""
    result = run_cmd(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=60,
        env={"SC_READINESS_ARTIFACT": str(msi_path)},
    )
    if result.returncode != 0:
        return {"ok": False, "status": "authenticode_probe_failed"}
    try:
        evidence = json.loads(
            result.stdout,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {value}")
            ),
        )
    except (json.JSONDecodeError, ValueError):
        return {"ok": False, "status": "authenticode_evidence_invalid"}
    if not isinstance(evidence, dict):
        return {"ok": False, "status": "authenticode_evidence_invalid"}

    actual = normalize_sha256_thumbprint(str(evidence.get("signer_sha256") or ""))
    if evidence.get("status") != "Valid":
        return {"ok": False, "status": "authenticode_invalid"}
    if actual != expected:
        return {
            "ok": False,
            "status": "authenticode_signer_mismatch",
            "signer_sha256": actual,
        }
    if evidence.get("timestamped") is not True:
        return {"ok": False, "status": "authenticode_timestamp_missing"}
    return {
        "ok": True,
        "status": "valid",
        "signer_sha256": actual,
        "timestamped": True,
        "timestamp_signer_sha256": normalize_sha256_thumbprint(
            str(evidence.get("timestamp_signer_sha256") or "")
        ),
    }


def validate_msi_artifact(
    artifact_dir: Path,
    *,
    run_id: int,
    head_sha: str,
    branch: str,
    now: datetime,
    max_age: timedelta,
    expected_signer_sha256: str,
) -> dict[str, Any]:
    evidence_files = list(artifact_dir.rglob("msi-evidence.json"))
    checksum_files = list(artifact_dir.rglob("msi-sha256.txt"))
    msi_files = list(artifact_dir.rglob("*.msi"))
    if len(evidence_files) != 1 or len(checksum_files) != 1 or len(msi_files) != 1:
        return {"ok": False, "status": "artifact_evidence_missing"}

    evidence_path = evidence_files[0]
    if evidence_path.stat().st_size > 64 * 1024:
        return {"ok": False, "status": "artifact_evidence_oversized"}
    try:
        evidence = json.loads(
            evidence_path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"invalid JSON constant: {value}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return {"ok": False, "status": "artifact_evidence_invalid"}
    if not isinstance(evidence, dict):
        return {"ok": False, "status": "artifact_evidence_invalid"}

    generated = parse_utc_timestamp(evidence.get("generated_utc"))
    if generated is None:
        return {"ok": False, "status": "artifact_timestamp_missing"}
    if generated > now + MAX_FUTURE_SKEW:
        return {"ok": False, "status": "artifact_timestamp_in_future"}
    age = now - generated
    if age > max_age:
        return {
            "ok": False,
            "status": "artifact_evidence_stale",
            "age_hours": round(age.total_seconds() / 3600, 2),
        }

    msi_path = msi_files[0]
    actual_sha = sha256_file(msi_path)
    expected_sha = evidence.get("sha256")
    expected_size = evidence.get("size_bytes")
    if (
        evidence.get("workflow") != MSI_WORKFLOW
        or str(evidence.get("run_id")) != str(run_id)
        or evidence.get("git_sha") != head_sha
        or evidence.get("ref") != f"refs/heads/{branch}"
        or evidence.get("artifact") != msi_path.name
        or evidence.get("signed") is not True
        or not isinstance(expected_size, int)
        or isinstance(expected_size, bool)
        or expected_size != msi_path.stat().st_size
        or not isinstance(expected_sha, str)
        or expected_sha.lower() != actual_sha
    ):
        return {"ok": False, "status": "artifact_evidence_mismatch"}

    try:
        checksum_text = checksum_files[0].read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return {"ok": False, "status": "artifact_checksum_invalid"}
    checksum_parts = checksum_text.split()
    if len(checksum_parts) != 2 or checksum_parts[0].lower() != actual_sha:
        return {"ok": False, "status": "artifact_checksum_mismatch"}
    if checksum_parts[1].lstrip("*") != msi_path.name:
        return {"ok": False, "status": "artifact_checksum_mismatch"}

    signature = verify_authenticode(
        msi_path,
        expected_signer_sha256=expected_signer_sha256,
    )
    if signature.get("ok") is not True or signature.get("status") != "valid":
        return {
            "ok": False,
            "status": signature.get("status", "authenticode_invalid"),
        }

    return {
        "ok": True,
        "status": "ready",
        "artifact": msi_path.name,
        "sha256": actual_sha,
        "signature": signature,
        "generated_utc": generated.isoformat(),
    }


def check_msi_workflow(
    *,
    now: datetime | None = None,
    max_age_hours: float = DEFAULT_MAX_EVIDENCE_AGE_HOURS,
) -> dict[str, Any]:
    if (
        not math.isfinite(max_age_hours)
        or max_age_hours <= 0
        or max_age_hours > MAX_EVIDENCE_AGE_HOURS
    ):
        return {"ok": False, "status": "invalid_evidence_policy"}
    expected_signer_sha256 = first_env_value("READINESS_WINDOWS_SIGNER_SHA256")
    if normalize_sha256_thumbprint(expected_signer_sha256) is None:
        return {"ok": False, "status": "signer_policy_missing"}
    evaluated_at = now or datetime.now(timezone.utc)
    if evaluated_at.tzinfo is None:
        return {"ok": False, "status": "invalid_evaluation_time"}
    evaluated_at = evaluated_at.astimezone(timezone.utc)
    max_age = timedelta(hours=max_age_hours)

    gh = shutil.which("gh")
    if not gh:
        return {"ok": False, "status": "gh_missing", "gh_path": None}
    branch_result = run_cmd(
        [gh, "api", f"repos/{MSI_REPO}", "--jq", ".default_branch"],
        timeout=30,
    )
    if branch_result.returncode != 0 or not branch_result.stdout:
        return {"ok": False, "status": "repository_query_unavailable"}
    branch = branch_result.stdout.strip()
    head_result = run_cmd(
        [gh, "api", f"repos/{MSI_REPO}/commits/{branch}", "--jq", ".sha"],
        timeout=30,
    )
    if head_result.returncode != 0 or not head_result.stdout:
        return {"ok": False, "status": "repository_head_unavailable"}
    expected_head = head_result.stdout.strip()

    result = run_cmd(
        [
            gh,
            "run",
            "list",
            "--repo",
            MSI_REPO,
            "--workflow",
            MSI_WORKFLOW,
            "--branch",
            branch,
            "--limit",
            "1",
            "--json",
            "databaseId,status,conclusion,headSha,headBranch,createdAt,event,url",
        ],
        timeout=30,
    )
    if result.returncode != 0:
        return {"ok": False, "status": "workflow_query_failed", "error": result.stderr or result.stdout}
    try:
        runs = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "status": "bad_json", "error": type(exc).__name__}
    if not isinstance(runs, list):
        return {"ok": False, "status": "workflow_evidence_invalid"}
    latest = runs[0] if runs else None
    if not isinstance(latest, dict):
        return {"ok": False, "status": "workflow_evidence_missing", "latest": None}
    created = parse_utc_timestamp(latest.get("createdAt"))
    if created is None:
        return {"ok": False, "status": "workflow_timestamp_missing", "latest": latest}
    if created > evaluated_at + MAX_FUTURE_SKEW:
        return {"ok": False, "status": "workflow_timestamp_in_future", "latest": latest}
    run_age = evaluated_at - created
    if run_age > max_age:
        return {
            "ok": False,
            "status": "workflow_evidence_stale",
            "latest": latest,
            "age_hours": round(run_age.total_seconds() / 3600, 2),
        }
    if (
        latest.get("status") != "completed"
        or latest.get("conclusion") != "success"
        or latest.get("headBranch") != branch
        or latest.get("headSha") != expected_head
    ):
        return {
            "ok": False,
            "status": "workflow_not_current_success",
            "latest": latest,
            "expected_head": expected_head,
        }
    run_id = latest.get("databaseId")
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        return {"ok": False, "status": "workflow_run_id_invalid", "latest": latest}

    with tempfile.TemporaryDirectory(prefix="selfconnect-readiness-msi-") as temp_dir:
        download = run_cmd(
            [
                gh,
                "run",
                "download",
                str(run_id),
                "--repo",
                MSI_REPO,
                "--name",
                MSI_ARTIFACT_NAME,
                "--dir",
                temp_dir,
            ],
            timeout=120,
        )
        if download.returncode != 0:
            return {
                "ok": False,
                "status": "workflow_artifact_unavailable",
                "latest": latest,
            }
        artifact = validate_msi_artifact(
            Path(temp_dir),
            run_id=run_id,
            head_sha=expected_head,
            branch=branch,
            now=evaluated_at,
            max_age=max_age,
            expected_signer_sha256=expected_signer_sha256,
        )
    return {
        **artifact,
        "latest": latest,
        "expected_head": expected_head,
        "max_age_hours": max_age_hours,
    }


def run_required_check(
    name: str,
    check: Any,
    *,
    expected_status: str,
) -> dict[str, Any]:
    try:
        result = check()
    except Exception as exc:
        return {
            "ok": False,
            "status": "check_exception",
            "check": name,
            "error_type": type(exc).__name__,
        }
    if not isinstance(result, dict):
        return {"ok": False, "status": "invalid_check_result", "check": name}
    normalized = dict(result)
    if normalized.get("ok") is not True:
        normalized["ok"] = False
    if not isinstance(normalized.get("status"), str) or not normalized["status"]:
        normalized["ok"] = False
        normalized["status"] = "missing_check_status"
    elif normalized.get("ok") is True and normalized["status"] != expected_status:
        normalized["ok"] = False
        normalized["observed_status"] = normalized["status"]
        normalized["status"] = "unexpected_success_status"
    normalized["required"] = True
    return normalized


def collect(
    *,
    now: datetime | None = None,
    max_evidence_age_hours: float = DEFAULT_MAX_EVIDENCE_AGE_HOURS,
) -> dict[str, Any]:
    root = pka_root()
    evaluated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    repos = run_required_check(
        "repos",
        lambda: check_repos(root),
        expected_status=EXPECTED_SUCCESS_STATUS["repos"],
    )
    if repos["ok"] is True:
        tpm = run_required_check(
            "tpm",
            lambda: check_tpm(root),
            expected_status=EXPECTED_SUCCESS_STATUS["tpm"],
        )
    else:
        tpm = run_required_check(
            "tpm",
            lambda: {"ok": False, "status": "repo_precondition_failed"},
            expected_status=EXPECTED_SUCCESS_STATUS["tpm"],
        )
    checks = {
        "repos": repos,
        "gemini": run_required_check(
            "gemini",
            check_gemini,
            expected_status=EXPECTED_SUCCESS_STATUS["gemini"],
        ),
        "tpm": tpm,
        "msi_workflow": run_required_check(
            "msi_workflow",
            lambda: check_msi_workflow(
                now=evaluated_at,
                max_age_hours=max_evidence_age_hours,
            ),
            expected_status=EXPECTED_SUCCESS_STATUS["msi_workflow"],
        ),
        "signing_secrets": run_required_check(
            "signing_secrets",
            check_signing_secrets,
            expected_status=EXPECTED_SUCCESS_STATUS["signing_secrets"],
        ),
    }
    return {
        "schema": "selfconnect.ecosystem_readiness.v2",
        "evaluated_at": evaluated_at.isoformat(),
        "max_evidence_age_hours": max_evidence_age_hours,
        "pka_root": str(root),
        "ok": all(item.get("ok") is True for item in checks.values()),
        "checks": checks,
        "issues": ISSUES,
    }


def markdown_cell(value: Any) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", r"\|")[:240]


def emit_markdown(report: dict[str, Any], *, report_only: bool = False) -> str:
    checks = report["checks"]
    lines = [
        "# SelfConnect Ecosystem Readiness",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'FAIL'}",
        f"- Evaluation mode: {'REPORT ONLY - not readiness evidence' if report_only else 'FAIL-CLOSED'}",
        f"- Evaluated at: `{report['evaluated_at']}`",
        f"- Maximum evidence age: `{report['max_evidence_age_hours']}` hours",
        f"- Root: `{report['pka_root']}`",
        "",
        "## Gates",
        "",
        "| Gate | Status | Detail | Tracker |",
        "|---|---|---|---|",
    ]
    repos = checks["repos"]
    repo_items = repos.get("repos", [])
    repo_detail = markdown_cell(
        f"{sum(1 for r in repo_items if r.get('ok') is True)}/{len(repo_items)} "
        f"repos current; {repos.get('status', 'evaluated')}"
    )
    lines.append(f"| Repos clean/current remote | {'PASS' if repos['ok'] else 'FAIL'} | {repo_detail} | n/a |")
    gemini = checks["gemini"]
    gemini_detail = markdown_cell(
        f"{gemini['status']}; version {gemini.get('gemini_version')}"
    )
    lines.append(f"| Gemini non-interactive exact-response probe | {'PASS' if gemini['ok'] else 'FAIL'} | {gemini_detail} | {ISSUES['gemini']} |")
    tpm = checks["tpm"]
    tpm_detail = markdown_cell(tpm.get("probe", {}).get("error", tpm.get("status")))
    lines.append(f"| TPM platform attestation | {'PASS' if tpm['ok'] else 'FAIL'} | {tpm_detail} | {ISSUES['tpm']} |")
    msi = checks["msi_workflow"]
    latest = msi.get("latest") or {}
    msi_detail = markdown_cell(
        f"{msi.get('status')}; run {latest.get('databaseId', 'n/a')}"
    )
    lines.append(f"| Current signed MSI evidence | {'PASS' if msi['ok'] else 'FAIL'} | {msi_detail} | n/a |")
    signing = checks["signing_secrets"]
    present = signing.get("present", {})
    signing_detail = markdown_cell(f"{signing.get('status')}; {present}")
    lines.append(f"| MSI code-signing secret names | {'PASS' if signing['ok'] else 'FAIL'} | {signing_detail} | {ISSUES['signing_secrets']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown", action="store_true", help="print Markdown summary")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="print diagnostics but exit zero; output is explicitly marked non-evidence",
    )
    parser.add_argument(
        "--fail-on-blockers",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max-evidence-age-hours",
        type=float,
        default=DEFAULT_MAX_EVIDENCE_AGE_HOURS,
        help=(
            "maximum age for remote workflow and artifact evidence; "
            f"may not exceed {MAX_EVIDENCE_AGE_HOURS:g} hours"
        ),
    )
    args = parser.parse_args()

    if args.report_only and args.fail_on_blockers:
        parser.error("--report-only cannot be combined with --fail-on-blockers")
    if (
        not math.isfinite(args.max_evidence_age_hours)
        or args.max_evidence_age_hours <= 0
        or args.max_evidence_age_hours > MAX_EVIDENCE_AGE_HOURS
    ):
        parser.error(
            "--max-evidence-age-hours must be positive and no greater than "
            f"{MAX_EVIDENCE_AGE_HOURS:g}"
        )

    report = collect(max_evidence_age_hours=args.max_evidence_age_hours)
    if args.markdown:
        print(emit_markdown(report, report_only=args.report_only))
    else:
        report["evaluation_mode"] = "report_only" if args.report_only else "fail_closed"
        print(json.dumps(report, indent=2))

    return 0 if report["ok"] or args.report_only else 2


if __name__ == "__main__":
    raise SystemExit(main())
