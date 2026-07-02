"""
Tests for the SelfConnect MCP server tool handlers.

All tests are unit tests — no real network calls, no MCP SDK required.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.tsk_key = "sc-tsk-TEST-0000-0000"
    client.get_budget.return_value = {
        "budget": 500_000,
        "used": 12_345,
        "remaining": 487_655,
        "pct_used": 2.47,
        "is_system": False,
        "registered": True,
    }
    client.start_session.return_value = "sess-mcp-001"
    client.end_session.return_value = {"session_id": "sess-mcp-001", "status": "ended"}
    client.post_event.return_value = {"event_id": "ev-001", "hash": "abc123"}
    client.get_session_workflow.return_value = {
        "session_id": "sess-mcp-001",
        "chain_of_custody": [{"event_type": "llm_call", "hash": "abc123"}],
    }
    client.get_tsk_events.return_value = [
        {"session_id": "sess-mcp-001", "event_type": "llm_call", "tokens_input": 100}
    ]
    client.get_tsk_info.return_value = {
        "key": "sc-tsk-TEST-0000-0000",
        "budget": 500_000,
        "revoked": False,
    }
    return client


@pytest.fixture(autouse=True)
def patch_get_client(mock_client):
    with patch("selfconnect.mcp.server._get_client", return_value=mock_client):
        yield


class TestMcpTools:
    @pytest.mark.asyncio
    async def test_status(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("selfconnect_status", {})
        data = json.loads(result)
        assert data["remaining"] == 487_655

    @pytest.mark.asyncio
    async def test_start_session(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("selfconnect_start_session", {"agent_id": "test-agent"})
        data = json.loads(result)
        assert data["session_id"] == "sess-mcp-001"
        assert data["agent_id"] == "test-agent"

    @pytest.mark.asyncio
    async def test_end_session(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("selfconnect_end_session", {"session_id": "sess-mcp-001"})
        data = json.loads(result)
        assert data["status"] == "ended"

    @pytest.mark.asyncio
    async def test_post_event(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("selfconnect_post_event", {
            "session_id": "sess-mcp-001",
            "event_type": "llm_call",
            "tokens_input": 512,
            "tokens_output": 128,
        })
        data = json.loads(result)
        assert data["event_id"] == "ev-001"
        mock_client.post_event.assert_called_once_with(
            session_id="sess-mcp-001",
            event_type="llm_call",
            tokens_input=512,
            tokens_output=128,
            decision=None,
            meta=None,
        )

    @pytest.mark.asyncio
    async def test_get_audit(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("selfconnect_get_audit", {"session_id": "sess-mcp-001"})
        data = json.loads(result)
        assert "chain_of_custody" in data
        assert len(data["chain_of_custody"]) == 1

    @pytest.mark.asyncio
    async def test_recent_events(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("selfconnect_recent_events", {"limit": 10})
        data = json.loads(result)
        assert isinstance(data, list)
        assert data[0]["event_type"] == "llm_call"

    @pytest.mark.asyncio
    async def test_key_info(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("selfconnect_key_info", {})
        data = json.loads(result)
        assert data["revoked"] is False

    @pytest.mark.asyncio
    async def test_unknown_tool(self, mock_client):
        from selfconnect.mcp.server import handle_tool
        result = await handle_tool("nonexistent_tool", {})
        data = json.loads(result)
        assert "error" in data
        assert "Unknown tool" in data["error"]

    @pytest.mark.asyncio
    async def test_tool_error_returns_json(self):
        from selfconnect.mcp.server import handle_tool
        with patch("selfconnect.mcp.server._get_client", side_effect=ValueError("No key")):
            result = await handle_tool("selfconnect_status", {})
        data = json.loads(result)
        assert "error" in data
        assert "No key" in data["error"]

    def test_tools_list_complete(self):
        from selfconnect.mcp.server import TOOLS
        names = {t["name"] for t in TOOLS}
        expected = {
            "selfconnect_status",
            "selfconnect_start_session",
            "selfconnect_end_session",
            "selfconnect_post_event",
            "selfconnect_get_audit",
            "selfconnect_recent_events",
            "selfconnect_key_info",
        }
        assert expected == names

    def test_all_tools_have_required_fields(self):
        from selfconnect.mcp.server import TOOLS
        for tool in TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert len(tool["description"]) > 20, f"{tool['name']} description too short"
