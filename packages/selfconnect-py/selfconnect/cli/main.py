"""
selfconnect CLI — manage your AI governance platform from the terminal.

Commands:
  login     Save a TSK key to ~/.selfconnect/config.json
  logout    Remove saved credentials
  status    Show TSK key info and budget
  usage     Show recent events and token usage
  audit     Export a session audit trail (chain-of-custody)
  keys      Manage TSK keys (info, revoke)
  session   Start / end sessions manually
  version   Print SDK version
"""
from __future__ import annotations

import json
import sys
from typing import Optional

import click
from pathlib import Path

from selfconnect.cli.config import (
    clear_credentials,
    get_base_url,
    get_tsk_key,
    is_logged_in,
    save_credentials,
)

# Lazy import so CLI works without a valid key for login/version
def _client(tsk_key: Optional[str] = None, base_url: Optional[str] = None):
    from selfconnect import TskClient

    key = tsk_key or get_tsk_key()
    url = base_url or get_base_url()
    if not key:
        click.echo(
            click.style("✗ Not logged in. Run: selfconnect login --key sc-tsk-YOUR-KEY", fg="red"),
            err=True,
        )
        sys.exit(1)
    return TskClient(tsk_key=key, base_url=url)


# ─── Formatting helpers ───────────────────────────────────────────────────────

def _ok(msg: str) -> None:
    click.echo(click.style("✓ ", fg="green") + msg)


def _err(msg: str) -> None:
    click.echo(click.style("✗ ", fg="red") + msg, err=True)


def _header(title: str) -> None:
    click.echo(click.style(f"\n  {title}", bold=True))
    click.echo(click.style("  " + "─" * len(title), fg="bright_black"))


def _row(label: str, value: str, color: Optional[str] = None) -> None:
    val = click.style(str(value), fg=color) if color else str(value)
    click.echo(f"  {click.style(label + ':', bold=True):<28} {val}")


def _budget_bar(pct: float, width: int = 30) -> str:
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    color = "green" if pct < 70 else ("yellow" if pct < 90 else "red")
    return click.style(bar, fg=color) + f"  {pct:.1f}%"


# ─── CLI group ────────────────────────────────────────────────────────────────

@click.group()
@click.version_option(package_name="selfconnect", prog_name="selfconnect")
def cli():
    """SelfConnect.ai — AI governance platform CLI.

    Manage TSK keys, monitor budgets, and export audit trails from the terminal.

    Docs: https://selfconnect.ai/docs/cli
    """


# ─── login ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--key", "-k", prompt="TSK Key", help="Your SelfConnect TSK key (sc-tsk-...)")
@click.option("--url", default="https://api.selfconnect.ai", show_default=True, help="API base URL")
def login(key: str, url: str):
    """Save your TSK key to ~/.selfconnect/config.json."""
    if not key.startswith("sc-tsk-"):
        _err("Invalid key format. TSK keys must start with 'sc-tsk-'")
        sys.exit(1)

    # Verify the key works before saving
    click.echo("  Verifying key with SelfConnect API...")
    try:
        from selfconnect.client import TskClient
        client = TskClient(tsk_key=key, base_url=url)
        info = client.get_tsk_info()
        save_credentials(key, url)
        _ok(f"Logged in — key: {key[:18]}...  |  budget: {info.get('budget', '?')} tokens")
    except Exception as exc:
        _err(f"Login failed: {exc}")
        sys.exit(1)


# ─── logout ───────────────────────────────────────────────────────────────────

@cli.command()
def logout():
    """Remove saved TSK key from ~/.selfconnect/config.json."""
    if not is_logged_in():
        click.echo("  Not logged in.")
        return
    clear_credentials()
    _ok("Logged out. Credentials removed from ~/.selfconnect/config.json")


# ─── status ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--key", "-k", default=None, help="Override TSK key")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def status(key: Optional[str], as_json: bool):
    """Show TSK key info and current budget status."""
    client = _client(tsk_key=key)

    try:
        info = client.get_tsk_info()
        budget = client.get_budget()
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)

    if as_json:
        click.echo(json.dumps({"info": info, "budget": budget}, indent=2))
        return

    _header("TSK Key Status")
    _row("Key", client.tsk_key[:22] + "...", "cyan")
    _row("Registered", "Yes" if budget["registered"] else "No",
         "green" if budget["registered"] else "red")
    _row("Revoked", "Yes" if info.get("revoked") else "No",
         "red" if info.get("revoked") else "green")
    _row("Created", str(info.get("created_at", "—")))

    _header("Budget")
    _row("Total budget", f"{budget['budget']:,} tokens")
    _row("Used", f"{budget['used']:,} tokens")
    _row("Remaining", f"{budget['remaining']:,} tokens",
         "green" if budget["pct_used"] < 70 else ("yellow" if budget["pct_used"] < 90 else "red"))
    click.echo(f"\n  {_budget_bar(budget['pct_used'])}\n")


# ─── usage ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--key", "-k", default=None, help="Override TSK key")
@click.option("--limit", "-n", default=20, show_default=True, help="Number of events to show")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def usage(key: Optional[str], limit: int, as_json: bool):
    """Show recent events and token usage for this TSK key."""
    client = _client(tsk_key=key)

    try:
        events = client.get_tsk_events(limit=limit)
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(events, indent=2, default=str))
        return

    if not events:
        click.echo("  No events found for this TSK key.")
        return

    _header(f"Recent Events  ({len(events)} shown)")
    click.echo(
        f"  {'Time':<22} {'Session':<38} {'Type':<18} {'In':>8} {'Out':>8}"
    )
    click.echo("  " + "─" * 96)

    total_in = total_out = 0
    for ev in events:
        ts = str(ev.get("ingested_at", ev.get("created_at", "—")))[:19]
        sid = str(ev.get("session_id", "—"))[:36]
        etype = str(ev.get("event_type", "—"))[:16]
        tin = int(ev.get("tokens_input", 0))
        tout = int(ev.get("tokens_output", 0))
        total_in += tin
        total_out += tout
        click.echo(f"  {ts:<22} {sid:<38} {etype:<18} {tin:>8,} {tout:>8,}")

    click.echo("  " + "─" * 96)
    click.echo(
        f"  {'TOTAL':<22} {'':<38} {'':<18} "
        + click.style(f"{total_in:>8,}", bold=True)
        + click.style(f" {total_out:>8,}", bold=True)
    )
    click.echo()


# ─── audit ────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("session_id")
@click.option("--key", "-k", default=None, help="Override TSK key")
@click.option("--output", "-o", default=None, help="Save to file (default: stdout)")
@click.option("--json", "as_json", is_flag=True, default=True, help="Output JSON (default)")
def audit(session_id: str, key: Optional[str], output: Optional[str], as_json: bool):
    """Export the cryptographic audit trail for a session.

    SESSION_ID is the UUID of the session to retrieve.

    Example:
        selfconnect audit 3f2a1b4c-... --output audit.json
    """
    client = _client(tsk_key=key)

    try:
        workflow = client.get_session_workflow(session_id)
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)

    payload = json.dumps(workflow, indent=2, default=str)

    if output:
        Path(output).write_text(payload)
        _ok(f"Audit trail saved to {output}")
        events = workflow.get("chain_of_custody", workflow.get("events", []))
        click.echo(f"  Events: {len(events)}  |  Session: {session_id}")
    else:
        click.echo(payload)


# ─── keys group ───────────────────────────────────────────────────────────────

@cli.group()
def keys():
    """Manage TSK keys — inspect, list, and revoke."""


@keys.command(name="info")
@click.option("--key", "-k", default=None, help="TSK key to inspect (default: current)")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def keys_info(key: Optional[str], as_json: bool):
    """Show detailed info for a TSK key."""
    client = _client(tsk_key=key)

    try:
        info = client.get_tsk_info()
        budget = client.get_budget()
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)

    if as_json:
        click.echo(json.dumps({**info, "budget": budget}, indent=2, default=str))
        return

    _header("Key Info")
    for k, v in info.items():
        _row(k, str(v))
    _header("Budget")
    _row("budget", f"{budget['budget']:,}")
    _row("used", f"{budget['used']:,}")
    _row("remaining", f"{budget['remaining']:,}")
    _row("pct_used", f"{budget['pct_used']}%")
    click.echo()


@keys.command(name="revoke")
@click.argument("tsk_key_to_revoke")
@click.option("--key", "-k", default=None, help="Admin TSK key (default: current)")
@click.confirmation_option(prompt="Are you sure you want to revoke this key?")
def keys_revoke(tsk_key_to_revoke: str, key: Optional[str]):
    """Revoke a TSK key permanently.

    TSK_KEY_TO_REVOKE is the key to revoke (e.g. sc-tsk-XXXX-YYYY).
    """
    client = _client(tsk_key=key)

    try:
        result = client._request("POST", "/tsk/revoke", json={"tsk_key": tsk_key_to_revoke})
        _ok(f"Key revoked: {tsk_key_to_revoke}")
        if result:
            click.echo(f"  {json.dumps(result, indent=2)}")
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)


# ─── session group ────────────────────────────────────────────────────────────

@cli.group()
def session():
    """Manually start and end governed sessions."""


@session.command(name="start")
@click.argument("agent_id")
@click.option("--key", "-k", default=None, help="Override TSK key")
@click.option("--json", "as_json", is_flag=True, help="Output session ID as JSON")
def session_start(agent_id: str, key: Optional[str], as_json: bool):
    """Start a new governed session for AGENT_ID.

    Prints the session ID to stdout so it can be captured in scripts:

        SESSION=$(selfconnect session start my-agent)
    """
    client = _client(tsk_key=key)

    try:
        session_id = client.start_session(agent_id)
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)

    if as_json:
        click.echo(json.dumps({"session_id": session_id, "agent_id": agent_id}))
    else:
        click.echo(session_id)


@session.command(name="end")
@click.argument("session_id")
@click.option("--summary", "-s", default=None, help="Session summary")
@click.option("--key", "-k", default=None, help="Override TSK key")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON")
def session_end(session_id: str, summary: Optional[str], key: Optional[str], as_json: bool):
    """End an active session SESSION_ID."""
    client = _client(tsk_key=key)

    try:
        result = client.end_session(session_id, summary=summary)
    except Exception as exc:
        _err(str(exc))
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        _ok(f"Session ended: {session_id}")


# ─── version ──────────────────────────────────────────────────────────────────

@cli.command()
def version():
    """Print the selfconnect SDK version."""
    try:
        from importlib.metadata import version as pkg_version
        v = pkg_version("selfconnect")
    except Exception:
        v = "unknown"
    click.echo(f"selfconnect {v}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
