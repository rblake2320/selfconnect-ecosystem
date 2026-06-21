#!/usr/bin/env python3
"""SelfConnect ecosystem readiness checks.

This script is intentionally read-only. It turns the remaining external gates
into one repeatable command so the status is not reconstructed from transcripts.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPOS = {
    "selfconnect": "selfconnect",
    "selfconnect-enterprise": "selfconnect-enterprise",
    "selfconnect-ecosystem": "selfconnect-ecosystem",
    "bpc-protocol": "bpc-protocol",
    "tsk-protocol": "tsk-protocol",
    "selfconnect-alt": "selfconnect-alt",
}

GEMINI_ENV_VARS = (
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
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


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def run_cmd(args: list[str], cwd: Path | None = None, timeout: int = 30) -> CmdResult:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return CmdResult(completed.returncode, completed.stdout.strip(), completed.stderr.strip())
    except FileNotFoundError as exc:
        return CmdResult(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CmdResult(124, stdout.strip(), stderr.strip() or "command timed out")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def pka_root() -> Path:
    return Path(os.environ.get("PKA_ROOT", str(repo_root().parent))).resolve()


def git_repo_status(name: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"name": name, "path": str(path), "status": "missing", "ok": False}

    status = run_cmd(["git", "status", "--short", "--branch"], cwd=path)
    head = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=path)
    first_line = status.stdout.splitlines()[0] if status.stdout else ""
    dirty_lines = [line for line in status.stdout.splitlines()[1:] if line.strip()]
    upstream_drift = "[ahead" in first_line or "[behind" in first_line or "..." not in first_line
    ok = status.returncode == 0 and head.returncode == 0 and not dirty_lines and not upstream_drift
    return {
        "name": name,
        "path": str(path),
        "ok": ok,
        "branch_line": first_line,
        "head": head.stdout if head.returncode == 0 else None,
        "dirty_count": len(dirty_lines),
        "status": "clean" if ok else "attention",
        "error": status.stderr if status.returncode != 0 else "",
    }


def check_repos(root: Path) -> dict[str, Any]:
    repos = [git_repo_status(name, root / rel) for name, rel in REPOS.items()]
    return {
        "ok": all(item["ok"] for item in repos),
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


def check_gemini() -> dict[str, Any]:
    gemini = shutil.which("gemini")
    gcloud = shutil.which("gcloud")
    version = None
    if gemini:
        result = run_cmd([gemini, "--version"], timeout=20)
        version = result.stdout if result.returncode == 0 else None

    env = {name: {"present": bool(os.environ.get(name)), "length": len(os.environ.get(name, ""))} for name in GEMINI_ENV_VARS}
    adc = [{"path": str(path), "present": path.exists()} for path in default_adc_paths()]
    google_credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    google_credentials_file = bool(google_credentials_path and Path(google_credentials_path).exists())

    auth_configured = bool(
        os.environ.get("GEMINI_API_KEY")
        or google_credentials_file
        or any(item["present"] for item in adc)
    )
    return {
        "ok": bool(gemini and auth_configured),
        "status": "ready" if gemini and auth_configured else "provider_auth_required",
        "gemini_path": gemini,
        "gemini_version": version,
        "gcloud_path": gcloud,
        "env": env,
        "default_adc": adc,
    }


def check_tpm(root: Path) -> dict[str, Any]:
    enterprise = root / "selfconnect-enterprise"
    if not enterprise.exists():
        return {"ok": False, "status": "missing_repo", "path": str(enterprise)}

    probe = (
        "import json; "
        "from enterprise.tpm_attestation import tpm_probe; "
        "print(json.dumps(tpm_probe(), default=str))"
    )
    result = run_cmd([sys.executable, "-c", probe], cwd=enterprise, timeout=60)
    if result.returncode != 0:
        return {
            "ok": False,
            "status": "probe_error",
            "error": result.stderr or result.stdout,
        }
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "status": "bad_json", "error": str(exc), "stdout": result.stdout}
    return {
        "ok": bool(data.get("supported")),
        "status": "ready" if data.get("supported") else "na_on_this_host",
        "probe": data,
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
        "status": "ready" if all(present.values()) else "missing_signing_secrets",
        "gh_path": gh,
        "present": present,
    }


def check_msi_workflow() -> dict[str, Any]:
    gh = shutil.which("gh")
    if not gh:
        return {"ok": False, "status": "gh_missing", "gh_path": None}
    result = run_cmd(
        [
            gh,
            "run",
            "list",
            "--repo",
            "rblake2320/selfconnect-enterprise",
            "--workflow",
            "Build MSI Release Artifact",
            "--limit",
            "1",
            "--json",
            "databaseId,status,conclusion,headSha,createdAt",
        ],
        timeout=30,
    )
    if result.returncode != 0:
        return {"ok": False, "status": "workflow_query_failed", "error": result.stderr or result.stdout}
    try:
        runs = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "status": "bad_json", "error": str(exc), "stdout": result.stdout}
    latest = runs[0] if runs else None
    ok = bool(latest and latest.get("status") == "completed" and latest.get("conclusion") == "success")
    return {"ok": ok, "status": "ready" if ok else "no_successful_run", "latest": latest}


def collect() -> dict[str, Any]:
    root = pka_root()
    checks = {
        "repos": check_repos(root),
        "gemini": check_gemini(),
        "tpm": check_tpm(root),
        "msi_workflow": check_msi_workflow(),
        "signing_secrets": check_signing_secrets(),
    }
    return {
        "schema": "selfconnect.ecosystem_readiness.v1",
        "pka_root": str(root),
        "ok": all(item.get("ok", False) for item in checks.values()),
        "checks": checks,
        "issues": ISSUES,
    }


def emit_markdown(report: dict[str, Any]) -> str:
    checks = report["checks"]
    lines = [
        "# SelfConnect Ecosystem Readiness",
        "",
        f"- Overall: {'PASS' if report['ok'] else 'ATTENTION'}",
        f"- Root: `{report['pka_root']}`",
        "",
        "## Gates",
        "",
        "| Gate | Status | Detail | Tracker |",
        "|---|---|---|---|",
    ]
    lines.append(f"| Repos clean/synced | {'PASS' if checks['repos']['ok'] else 'ATTENTION'} | {sum(1 for r in checks['repos']['repos'] if r['ok'])}/{len(checks['repos']['repos'])} repos clean | n/a |")
    gemini = checks["gemini"]
    lines.append(f"| Gemini non-interactive auth | {'PASS' if gemini['ok'] else 'BLOCKED'} | {gemini['status']}; version `{gemini.get('gemini_version')}` | {ISSUES['gemini']} |")
    tpm = checks["tpm"]
    tpm_detail = tpm.get("probe", {}).get("error", tpm.get("status"))
    lines.append(f"| TPM platform attestation | {'PASS' if tpm['ok'] else 'NA'} | {tpm_detail} | {ISSUES['tpm']} |")
    msi = checks["msi_workflow"]
    latest = msi.get("latest") or {}
    lines.append(f"| MSI artifact workflow | {'PASS' if msi['ok'] else 'ATTENTION'} | run `{latest.get('databaseId', 'n/a')}` {latest.get('conclusion', msi.get('status'))} | n/a |")
    signing = checks["signing_secrets"]
    present = signing.get("present", {})
    lines.append(f"| MSI code-signing secrets | {'PASS' if signing['ok'] else 'BLOCKED'} | {present} | {ISSUES['signing_secrets']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON report")
    parser.add_argument("--markdown", action="store_true", help="print Markdown summary")
    parser.add_argument("--fail-on-blockers", action="store_true", help="exit nonzero when any gate is not ready")
    args = parser.parse_args()

    report = collect()
    if args.markdown:
        print(emit_markdown(report))
    else:
        print(json.dumps(report, indent=2))

    return 2 if args.fail_on_blockers and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
