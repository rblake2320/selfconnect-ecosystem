"""
pytest test suite for the selfconnect Python SDK.

Unit tests use respx to mock httpx requests — no network required.
Integration tests require an explicitly configured disposable test identity
and base URL. No live credential is embedded in this repository.

Run unit tests only:
    pytest tests/test_client.py -v -m "not integration"

Run explicitly configured live integration:
    SELFCONNECT_TSK_KEY=... SELFCONNECT_BASE_URL=... \
        pytest tests/test_client.py -v -m integration
"""

from __future__ import annotations

import json
import os
import pytest
import respx
import httpx

from selfconnect import TskClient, SelfConnectError, BudgetExhaustedError, TskInvalidError
from selfconnect.client import PolicyDeniedError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://api.selfconnect.ai"
TESTER_KEY = "sc-tsk-TESTER-0000"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Return a TskClient pointed at the mock base URL."""
    return TskClient(tsk_key=TESTER_KEY, base_url=BASE_URL, max_retries=1)


@pytest.fixture
def mock_api():
    """Activate respx mock router for all tests in a block."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Unit Tests: Constructor validation
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_valid_key_accepted(self):
        c = TskClient(tsk_key="sc-tsk-VALID-KEY1")
        assert c.tsk_key == "sc-tsk-VALID-KEY1"

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="sc-tsk-"):
            TskClient(tsk_key="invalid-key")

    def test_empty_key_raises(self):
        with pytest.raises(ValueError):
            TskClient(tsk_key="")

    def test_base_url_trailing_slash_stripped(self):
        c = TskClient(tsk_key="sc-tsk-X-0000", base_url="https://api.selfconnect.ai/")
        assert c.base_url == "https://api.selfconnect.ai"

    def test_repr_masks_key(self):
        c = TskClient(tsk_key="sc-tsk-SECRET-9999")
        r = repr(c)
        assert "sc-tsk-SECR" in r
        assert "SECRET-9999" not in r

    def test_context_manager_closes(self):
        with TskClient(tsk_key="sc-tsk-CTX-0001") as c:
            assert c.tsk_key == "sc-tsk-CTX-0001"
        # After __exit__, the client is closed — no exception expected


# ---------------------------------------------------------------------------
# Unit Tests: start_session
# ---------------------------------------------------------------------------

class TestStartSession:
    def test_returns_session_id(self, client, mock_api):
        mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(200, json={"session_id": "sess-abc123", "ok": True})
        )
        sid = client.start_session("test-agent")
        assert sid == "sess-abc123"

    def test_sends_tsk_header(self, client, mock_api):
        route = mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(200, json={"session_id": "sess-xyz"})
        )
        client.start_session("agent-1")
        assert route.called
        req = route.calls.last.request
        assert req.headers.get("x-tsk-key") == TESTER_KEY

    def test_sends_agent_id_in_body(self, client, mock_api):
        route = mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(200, json={"session_id": "sess-001"})
        )
        client.start_session("my-agent", meta={"env": "test"})
        body = json.loads(route.calls.last.request.content)
        assert body["agent_id"] == "my-agent"
        assert body["meta"]["env"] == "test"

    def test_401_raises_tsk_invalid(self, client, mock_api):
        mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(401, json={"detail": {"error": "TSK key not found"}})
        )
        with pytest.raises(TskInvalidError):
            client.start_session("agent")

    def test_500_raises_selfconnect_error(self, client, mock_api):
        mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(500, json={"detail": "internal error"})
        )
        with pytest.raises(SelfConnectError):
            client.start_session("agent")


# ---------------------------------------------------------------------------
# Unit Tests: post_event
# ---------------------------------------------------------------------------

class TestPostEvent:
    def test_posts_event_successfully(self, client, mock_api):
        mock_api.post("/events").mock(
            return_value=httpx.Response(200, json={"id": "evt-001", "ok": True})
        )
        result = client.post_event("sess-001", "llm_call", tokens_input=512, tokens_output=128)
        assert result["ok"] is True

    def test_sends_correct_payload(self, client, mock_api):
        route = mock_api.post("/events").mock(
            return_value=httpx.Response(200, json={"id": "evt-002"})
        )
        client.post_event(
            "sess-001",
            "tool_use",
            tokens_input=100,
            tokens_output=50,
            decision="approved",
            meta={"tool": "web_search"},
        )
        body = json.loads(route.calls.last.request.content)
        assert body["session_id"] == "sess-001"
        assert body["event_type"] == "tool_use"
        assert body["tokens_input"] == 100
        assert body["tokens_output"] == 50
        assert body["decision"] == "approved"
        assert body["meta"]["tool"] == "web_search"

    def test_429_raises_budget_exhausted(self, client, mock_api):
        mock_api.post("/events").mock(
            return_value=httpx.Response(429, json={"detail": {"error": "Budget exhausted"}})
        )
        with pytest.raises(BudgetExhaustedError):
            client.post_event("sess-001", "llm_call")

    def test_401_raises_tsk_invalid(self, client, mock_api):
        mock_api.post("/events").mock(
            return_value=httpx.Response(401, json={"detail": {"error": "TSK revoked"}})
        )
        with pytest.raises(TskInvalidError):
            client.post_event("sess-001", "llm_call")

    def test_403_raises_policy_denied(self, client, mock_api):
        mock_api.post("/events").mock(
            return_value=httpx.Response(403, json={"detail": {"error": "Policy violation"}})
        )
        with pytest.raises(PolicyDeniedError):
            client.post_event("sess-001", "llm_call")


# ---------------------------------------------------------------------------
# Unit Tests: post_events (batch)
# ---------------------------------------------------------------------------

class TestPostEvents:
    def test_posts_multiple_events(self, client, mock_api):
        mock_api.post("/events").mock(
            return_value=httpx.Response(200, json={"id": "evt-batch", "ok": True})
        )
        events = [
            {"session_id": "sess-001", "event_type": "llm_call", "tokens_input": 100, "tokens_output": 50},
            {"session_id": "sess-001", "event_type": "tool_use", "tokens_input": 0, "tokens_output": 0},
        ]
        results = client.post_events(events)
        assert len(results) == 2

    def test_empty_batch_returns_empty_list(self, client, mock_api):
        results = client.post_events([])
        assert results == []


# ---------------------------------------------------------------------------
# Unit Tests: end_session
# ---------------------------------------------------------------------------

class TestEndSession:
    def test_ends_session_successfully(self, client, mock_api):
        mock_api.post("/sessions/end").mock(
            return_value=httpx.Response(200, json={"ok": True, "session_id": "sess-001"})
        )
        result = client.end_session("sess-001", summary="Completed research task")
        assert result["ok"] is True

    def test_sends_summary_in_body(self, client, mock_api):
        route = mock_api.post("/sessions/end").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        client.end_session("sess-001", summary="Test summary")
        body = json.loads(route.calls.last.request.content)
        assert body["summary"] == "Test summary"
        assert body["session_id"] == "sess-001"


# ---------------------------------------------------------------------------
# Unit Tests: get_budget
# ---------------------------------------------------------------------------

class TestGetBudget:
    def test_returns_budget_info(self, client, mock_api):
        mock_api.get(f"/budget/{TESTER_KEY}").mock(
            return_value=httpx.Response(200, json={
                "budget": 10_000_000_000,
                "used": 5_000_000,
                "is_system": True,
                "registered": True,
            })
        )
        budget = client.get_budget()
        assert budget["budget"] == 10_000_000_000
        assert budget["used"] == 5_000_000
        assert budget["remaining"] == 9_995_000_000
        assert budget["pct_used"] == pytest.approx(0.05, abs=0.01)
        assert budget["is_system"] is True

    def test_zero_budget_pct_is_zero(self, client, mock_api):
        mock_api.get(f"/budget/{TESTER_KEY}").mock(
            return_value=httpx.Response(200, json={"budget": 0, "used": 0})
        )
        budget = client.get_budget()
        assert budget["pct_used"] == 0.0


# ---------------------------------------------------------------------------
# Unit Tests: get_session_workflow
# ---------------------------------------------------------------------------

class TestGetSessionWorkflow:
    def test_returns_workflow_data(self, client, mock_api):
        mock_api.get("/workflows/sess-001").mock(
            return_value=httpx.Response(200, json={
                "session_id": "sess-001",
                "chain_of_custody": [{"id": "evt-1", "entry_hash": "abc"}],
            })
        )
        workflow = client.get_session_workflow("sess-001")
        assert workflow["session_id"] == "sess-001"
        assert len(workflow["chain_of_custody"]) == 1


# ---------------------------------------------------------------------------
# Unit Tests: context manager (session())
# ---------------------------------------------------------------------------

class TestSessionContextManager:
    def test_auto_starts_and_ends_session(self, client, mock_api):
        start_route = mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(200, json={"session_id": "sess-ctx-001"})
        )
        mock_api.post("/events").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        end_route = mock_api.post("/sessions/end").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        with client.session("test-agent") as session_id:
            assert session_id == "sess-ctx-001"
            client.post_event(session_id, "llm_call", tokens_input=100)

        # Both start and end should have been called
        assert start_route.called
        assert end_route.called

    def test_session_ends_even_on_exception(self, client, mock_api):
        mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(200, json={"session_id": "sess-exc"})
        )
        end_route = mock_api.post("/sessions/end").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        with pytest.raises(ValueError):
            with client.session("test-agent"):
                raise ValueError("intentional error")

        assert end_route.called


# ---------------------------------------------------------------------------
# Unit Tests: governed_session decorator
# ---------------------------------------------------------------------------

class TestGovernedSessionDecorator:
    def test_sync_function_receives_session_id(self, client, mock_api):
        mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(200, json={"session_id": "sess-dec-001"})
        )
        mock_api.post("/sessions/end").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        received_session_ids = []

        @client.governed_session("decorated-agent")
        def my_func(session_id: str, value: int) -> int:
            received_session_ids.append(session_id)
            return value * 2

        result = my_func(21)
        assert result == 42
        assert received_session_ids == ["sess-dec-001"]

    @pytest.mark.asyncio
    async def test_async_function_receives_session_id(self, client, mock_api):
        mock_api.post("/sessions/start").mock(
            return_value=httpx.Response(200, json={"session_id": "sess-async-001"})
        )
        mock_api.post("/sessions/end").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )

        received = []

        @client.governed_session("async-agent")
        async def async_func(session_id: str) -> str:
            received.append(session_id)
            return "async-result"

        result = await async_func()
        assert result == "async-result"
        assert received == ["sess-async-001"]


# ---------------------------------------------------------------------------
# Integration Tests (require an explicitly configured disposable identity)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestLiveIntegration:
    """
    Live integration tests against an operator-selected SelfConnect endpoint.

    The credential must be restricted, disposable, and supplied by a protected
    environment. These tests do not run with the unit-test placeholder key.
    """

    @pytest.fixture(autouse=True)
    def live_client(self):
        key = os.environ.get("SELFCONNECT_TSK_KEY")
        base_url = os.environ.get("SELFCONNECT_BASE_URL")
        if not key or not base_url:
            pytest.skip(
                "live integration requires SELFCONNECT_TSK_KEY and "
                "SELFCONNECT_BASE_URL from a protected environment"
            )
        if key == TESTER_KEY:
            pytest.fail("unit-test placeholder key cannot be used for live integration")
        self.client = TskClient(tsk_key=key, base_url=base_url)
        self.live_base_url = base_url

    def test_get_budget_returns_real_data(self):
        budget = self.client.get_budget()
        assert budget["budget"] > 0
        assert budget["used"] >= 0
        assert budget["remaining"] >= 0
        assert 0.0 <= budget["pct_used"] <= 100.0

    def test_full_session_lifecycle(self):
        # Start session
        session_id = self.client.start_session(
            "pytest-integration-agent",
            meta={"test": True, "framework": "pytest"},
        )
        assert session_id and len(session_id) > 0

        # Post events
        result = self.client.post_event(
            session_id=session_id,
            event_type="llm_call",
            tokens_input=100,
            tokens_output=50,
            meta={"model": "test-model"},
        )
        assert result is not None

        # Post batch events
        batch_results = self.client.post_events([
            {"session_id": session_id, "event_type": "tool_use", "tokens_input": 10, "tokens_output": 5},
            {"session_id": session_id, "event_type": "policy_check", "tokens_input": 0, "tokens_output": 0, "decision": "approved"},
        ])
        assert len(batch_results) == 2

        # End session
        end_result = self.client.end_session(session_id, summary="pytest integration test completed")
        assert end_result is not None

    def test_workflow_retrieval(self):
        # Start a session, post an event, end it, then retrieve workflow
        session_id = self.client.start_session("pytest-workflow-agent")
        self.client.post_event(session_id, "llm_call", tokens_input=50, tokens_output=25)
        self.client.end_session(session_id)

        workflow = self.client.get_session_workflow(session_id)
        assert "chain_of_custody" in workflow or "session_id" in workflow

    def test_context_manager_lifecycle(self):
        with self.client.session("pytest-ctx-agent") as session_id:
            assert session_id
            self.client.post_event(session_id, "llm_call", tokens_input=20, tokens_output=10)
        # Session should be ended automatically

    def test_invalid_key_raises_tsk_invalid(self):
        bad_client = TskClient(
            tsk_key="sc-tsk-INVALID-0000",
            base_url=self.live_base_url,
            max_retries=1,
        )
        with pytest.raises((TskInvalidError, SelfConnectError)):
            bad_client.post_event("fake-session", "llm_call")

    def test_tsk_info_returns_key_metadata(self):
        info = self.client.get_tsk_info()
        assert info is not None

    def test_tsk_events_returns_list(self):
        events = self.client.get_tsk_events(limit=10)
        assert isinstance(events, list)
