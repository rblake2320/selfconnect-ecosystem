"""The LangChain adapter's fail-open boundary must be explicit and tested."""

from __future__ import annotations

import pytest

from selfconnect import BudgetExhaustedError, SelfConnectCallbackHandler


def make_handler(monkeypatch, *, raise_on_error: bool):
    import selfconnect.langchain_handler as module

    monkeypatch.setattr(module, "_LANGCHAIN_AVAILABLE", True)
    handler = object.__new__(SelfConnectCallbackHandler)
    handler.client = None
    handler.agent_id = "boundary-agent"
    handler.auto_session = False
    handler.raise_on_error = raise_on_error
    handler._session_id = "session-1"
    handler._active_runs = {}
    handler._chain_depth = 0
    return handler


class FailingClient:
    def post_event(self, **_kwargs):
        raise BudgetExhaustedError("budget exhausted", status_code=429)


def test_default_style_fail_open_swallows_delivery_error(monkeypatch, capsys):
    handler = make_handler(monkeypatch, raise_on_error=False)
    handler.client = FailingClient()

    handler._post_event("llm_call", tokens_input=1)

    assert "could not post event" in capsys.readouterr().out


def test_fail_closed_option_propagates_delivery_error(monkeypatch):
    handler = make_handler(monkeypatch, raise_on_error=True)
    handler.client = FailingClient()

    with pytest.raises(BudgetExhaustedError):
        handler._post_event("llm_call", tokens_input=1)
