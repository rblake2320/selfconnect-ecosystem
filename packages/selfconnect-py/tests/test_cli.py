"""
Tests for the selfconnect CLI.

All tests are unit tests — no real network calls.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from selfconnect.cli.main import cli
from selfconnect.cli.config import CONFIG_FILE, save_credentials, clear_credentials, get_tsk_key


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_config(tmp_path, monkeypatch):
    """Redirect config to a temp dir so tests don't touch ~/.selfconnect."""
    import selfconnect.cli.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "CONFIG_DIR", tmp_path / ".selfconnect")
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", tmp_path / ".selfconnect" / "config.json")
    yield


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_client():
    """Return a mock TskClient with sensible defaults."""
    client = MagicMock()
    client.tsk_key = "sc-tsk-TEST-0000-0000"
    client.get_tsk_info.return_value = {
        "key": "sc-tsk-TEST-0000-0000",
        "user_id": "u_001",
        "budget": 500_000,
        "used": 12_345,
        "revoked": False,
        "created_at": "2026-01-01T00:00:00Z",
    }
    client.get_budget.return_value = {
        "budget": 500_000,
        "used": 12_345,
        "remaining": 487_655,
        "pct_used": 2.47,
        "is_system": False,
        "registered": True,
    }
    client.get_tsk_events.return_value = [
        {
            "session_id": "sess-abc-123",
            "event_type": "llm_call",
            "tokens_input": 512,
            "tokens_output": 128,
            "ingested_at": "2026-06-09T10:00:00Z",
        }
    ]
    client.start_session.return_value = "sess-new-456"
    client.end_session.return_value = {"session_id": "sess-new-456", "status": "ended"}
    client.get_session_workflow.return_value = {
        "session_id": "sess-abc-123",
        "chain_of_custody": [{"event_type": "llm_call", "hash": "abc123"}],
    }
    return client


# ─── login ────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, runner, mock_client):
        with patch("selfconnect.client.TskClient", return_value=mock_client):
            result = runner.invoke(cli, ["login", "--key", "sc-tsk-TEST-0000-0000"])
        assert result.exit_code == 0
        assert "Logged in" in result.output

    def test_login_invalid_key_format(self, runner):
        result = runner.invoke(cli, ["login", "--key", "bad-key"])
        assert result.exit_code == 1
        assert "Invalid key format" in result.output

    def test_login_api_failure(self, runner):
        with patch("selfconnect.client.TskClient") as MockClient:
            MockClient.return_value.get_tsk_info.side_effect = Exception("401 Unauthorized")
            result = runner.invoke(cli, ["login", "--key", "sc-tsk-BAD-KEY-0000"])
        assert result.exit_code == 1
        assert "Login failed" in result.output


# ─── logout ───────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_when_logged_in(self, runner, mock_client):
        with patch("selfconnect.client.TskClient", return_value=mock_client):
            runner.invoke(cli, ["login", "--key", "sc-tsk-TEST-0000-0000"])
        result = runner.invoke(cli, ["logout"])
        assert result.exit_code == 0
        assert "Logged out" in result.output

    def test_logout_when_not_logged_in(self, runner):
        result = runner.invoke(cli, ["logout"])
        assert result.exit_code == 0
        assert "Not logged in" in result.output


# ─── status ───────────────────────────────────────────────────────────────────

class TestStatus:
    def test_status_text_output(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "Budget" in result.output
        assert "487,655" in result.output

    def test_status_json_output(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "budget" in data
        assert data["budget"]["remaining"] == 487_655

    def test_status_not_logged_in(self, runner):
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output


# ─── usage ────────────────────────────────────────────────────────────────────

class TestUsage:
    def test_usage_text_output(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["usage"])
        assert result.exit_code == 0
        assert "llm_call" in result.output
        assert "512" in result.output

    def test_usage_json_output(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["usage", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["event_type"] == "llm_call"

    def test_usage_empty(self, runner, mock_client):
        mock_client.get_tsk_events.return_value = []
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["usage"])
        assert result.exit_code == 0
        assert "No events" in result.output


# ─── audit ────────────────────────────────────────────────────────────────────

class TestAudit:
    def test_audit_stdout(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["audit", "sess-abc-123"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "chain_of_custody" in data

    def test_audit_to_file(self, runner, mock_client, tmp_path):
        out = str(tmp_path / "audit.json")
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["audit", "sess-abc-123", "--output", out])
        assert result.exit_code == 0
        assert "saved" in result.output
        saved = json.loads(open(out).read())
        assert "chain_of_custody" in saved


# ─── session ──────────────────────────────────────────────────────────────────

class TestSession:
    def test_session_start(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["session", "start", "my-agent"])
        assert result.exit_code == 0
        assert "sess-new-456" in result.output

    def test_session_start_json(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["session", "start", "my-agent", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["session_id"] == "sess-new-456"

    def test_session_end(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["session", "end", "sess-new-456"])
        assert result.exit_code == 0
        assert "ended" in result.output.lower()


# ─── keys ─────────────────────────────────────────────────────────────────────

class TestKeys:
    def test_keys_info(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["keys", "info"])
        assert result.exit_code == 0
        assert "Budget" in result.output

    def test_keys_info_json(self, runner, mock_client):
        with patch("selfconnect.cli.main._client", return_value=mock_client):
            result = runner.invoke(cli, ["keys", "info", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "budget" in data


# ─── version ──────────────────────────────────────────────────────────────────

class TestVersion:
    def test_version(self, runner):
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "selfconnect" in result.output
