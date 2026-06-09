"""
SelfConnect LangChain Callback Handler

Automatically instruments LangChain chains and agents with SelfConnect
governance, cost tracking, and audit trail.

Usage::

    from langchain_openai import ChatOpenAI
    from selfconnect import SelfConnectCallbackHandler

    handler = SelfConnectCallbackHandler(tsk_key="sc-tsk-YOUR-KEY")

    llm = ChatOpenAI(
        model="gpt-4o",
        callbacks=[handler],
    )

    # Or attach to a chain:
    chain = prompt | llm | output_parser
    result = chain.invoke({"input": "..."}, config={"callbacks": [handler]})
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from .client import TskClient, SelfConnectError

try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.outputs import LLMResult

    _LANGCHAIN_AVAILABLE = True
except ImportError:
    # Graceful degradation — langchain-core is optional
    _LANGCHAIN_AVAILABLE = False
    BaseCallbackHandler = object  # type: ignore[assignment,misc]
    LLMResult = Any  # type: ignore[assignment,misc]


class SelfConnectCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that posts all LLM calls, tool uses, and
    chain events to the SelfConnect audit trail in real time.

    Parameters
    ----------
    tsk_key : str
        Your SelfConnect TSK key.
    agent_id : str
        Identifier for this agent/chain. Defaults to ``"langchain-agent"``.
    base_url : str
        SelfConnect API base URL.
    auto_session : bool
        If ``True`` (default), automatically starts a new session on the
        first LLM call and ends it when the chain completes.
    session_id : str, optional
        Provide an existing session ID to attach events to instead of
        creating a new one.
    raise_on_error : bool
        If ``True``, re-raise SelfConnect errors. If ``False`` (default),
        log and continue so LangChain execution is never blocked.
    """

    def __init__(
        self,
        tsk_key: str,
        agent_id: str = "langchain-agent",
        base_url: str = TskClient.DEFAULT_BASE_URL,
        auto_session: bool = True,
        session_id: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> None:
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain-core is required for SelfConnectCallbackHandler. "
                "Install it with: pip install selfconnect[langchain]"
            )
        super().__init__()
        self.client = TskClient(tsk_key=tsk_key, base_url=base_url)
        self.agent_id = agent_id
        self.auto_session = auto_session
        self.raise_on_error = raise_on_error
        self._session_id: Optional[str] = session_id
        self._active_runs: Dict[str, float] = {}  # run_id -> start_time
        self._chain_depth = 0

    @property
    def session_id(self) -> Optional[str]:
        """The current active session ID, or None if not started."""
        return self._session_id

    # ------------------------------------------------------------------
    # Chain callbacks
    # ------------------------------------------------------------------

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._chain_depth += 1
        if self.auto_session and self._session_id is None and self._chain_depth == 1:
            self._start_session()

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._chain_depth -= 1
        if self.auto_session and self._chain_depth == 0 and self._session_id is not None:
            self._end_session()

    def on_chain_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._chain_depth -= 1
        self._post_event(
            event_type="chain_error",
            meta={"error": str(error), "run_id": str(run_id)},
        )
        if self.auto_session and self._chain_depth == 0 and self._session_id is not None:
            self._end_session(summary=f"Chain error: {error}")

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        if self.auto_session and self._session_id is None:
            self._start_session()
        self._active_runs[str(run_id)] = time.time()

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        start = self._active_runs.pop(str(run_id), time.time())
        duration_ms = int((time.time() - start) * 1000)

        # Extract token usage from LangChain response
        tokens_input = 0
        tokens_output = 0
        model_name = "unknown"
        try:
            if response.llm_output:
                usage = response.llm_output.get("token_usage", {})
                tokens_input = usage.get("prompt_tokens", 0)
                tokens_output = usage.get("completion_tokens", 0)
                model_name = response.llm_output.get("model_name", "unknown")
        except Exception:
            pass

        self._post_event(
            event_type="llm_call",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            meta={
                "model": model_name,
                "duration_ms": duration_ms,
                "run_id": str(run_id),
                "generations": len(response.generations),
            },
        )

    def on_llm_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._active_runs.pop(str(run_id), None)
        self._post_event(
            event_type="llm_error",
            meta={"error": str(error), "run_id": str(run_id)},
        )

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._active_runs[f"tool_{run_id}"] = time.time()

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        start = self._active_runs.pop(f"tool_{run_id}", time.time())
        duration_ms = int((time.time() - start) * 1000)
        tool_name = kwargs.get("name", "unknown_tool")
        self._post_event(
            event_type="tool_use",
            meta={
                "tool": tool_name,
                "duration_ms": duration_ms,
                "run_id": str(run_id),
            },
        )

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        self._active_runs.pop(f"tool_{run_id}", None)
        self._post_event(
            event_type="tool_error",
            meta={"error": str(error), "run_id": str(run_id)},
        )

    # ------------------------------------------------------------------
    # Agent callbacks
    # ------------------------------------------------------------------

    def on_agent_action(self, action: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._post_event(
            event_type="agent_action",
            meta={
                "tool": getattr(action, "tool", "unknown"),
                "tool_input": str(getattr(action, "tool_input", ""))[:500],
                "run_id": str(run_id),
            },
        )

    def on_agent_finish(self, finish: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._post_event(
            event_type="agent_finish",
            decision="completed",
            meta={
                "return_values": str(getattr(finish, "return_values", ""))[:500],
                "run_id": str(run_id),
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_session(self) -> None:
        try:
            self._session_id = self.client.start_session(
                agent_id=self.agent_id,
                meta={"framework": "langchain", "handler_version": "1.0.0"},
            )
        except SelfConnectError as exc:
            if self.raise_on_error:
                raise
            print(f"[SelfConnect] Warning: could not start session: {exc}")

    def _end_session(self, summary: Optional[str] = None) -> None:
        if self._session_id is None:
            return
        try:
            self.client.end_session(self._session_id, summary=summary)
        except SelfConnectError as exc:
            if self.raise_on_error:
                raise
            print(f"[SelfConnect] Warning: could not end session: {exc}")
        finally:
            self._session_id = None

    def _post_event(
        self,
        event_type: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        decision: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._session_id is None:
            return
        try:
            self.client.post_event(
                session_id=self._session_id,
                event_type=event_type,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                decision=decision,
                meta=meta,
            )
        except SelfConnectError as exc:
            if self.raise_on_error:
                raise
            print(f"[SelfConnect] Warning: could not post event: {exc}")
