"""
SelfConnect.ai TskClient — the primary interface for AI agent governance.

Usage:
    from selfconnect import TskClient

    client = TskClient(tsk_key="sc-tsk-YOUR-KEY")

    # Context manager (auto start/end session)
    with client.session("my-agent") as session_id:
        client.post_event(session_id, "llm_call", tokens_input=512, tokens_output=128)

    # Decorator
    @client.governed_session("my-agent")
    def run_agent():
        ...
"""

from __future__ import annotations

import functools
import inspect
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

import httpx
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SelfConnectError(Exception):
    """Base exception for all SelfConnect SDK errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, detail: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class BudgetExhaustedError(SelfConnectError):
    """Raised when the TSK key's token budget is exhausted (HTTP 429)."""


class TskInvalidError(SelfConnectError):
    """Raised when the TSK key is missing, invalid, or revoked (HTTP 401)."""


class PolicyDeniedError(SelfConnectError):
    """Raised when an event is rejected by a governance policy (HTTP 403)."""


# ---------------------------------------------------------------------------
# TypedDicts for structured return values
# ---------------------------------------------------------------------------


class BudgetInfo(TypedDict):
    budget: int
    used: int
    remaining: int
    pct_used: float
    is_system: bool
    registered: bool


class SessionInfo(TypedDict):
    session_id: str
    agent_id: str
    started_at: float


# ---------------------------------------------------------------------------
# TskClient
# ---------------------------------------------------------------------------


class TskClient:
    """
    SelfConnect Trust Session Key (TSK) client.

    Provides a high-level interface for:
    - Session lifecycle management (start, end)
    - Real-time event posting with TSK enforcement
    - Budget monitoring and enforcement
    - Workflow / audit trail retrieval
    - Context manager and decorator patterns

    Parameters
    ----------
    tsk_key : str
        Your SelfConnect TSK key (e.g. ``sc-tsk-XXXX-YYYY``).
    base_url : str
        Base URL of the SelfConnect API. Defaults to ``https://api.selfconnect.ai``.
    timeout : float
        HTTP request timeout in seconds. Defaults to 30.
    max_retries : int
        Number of retries on transient 5xx errors. Defaults to 3.
    """

    DEFAULT_BASE_URL = "https://api.selfconnect.ai"

    def __init__(
        self,
        tsk_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        if not tsk_key or not tsk_key.startswith("sc-tsk-"):
            raise ValueError(
                "Invalid TSK key format. Keys must start with 'sc-tsk-'. "
                "Get your key at https://selfconnect.ai"
            )
        self.tsk_key = tsk_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self._http = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-TSK-Key": self.tsk_key,
                "Content-Type": "application/json",
                "User-Agent": f"selfconnect-py/1.0.0",
            },
            timeout=self.timeout,
        )

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self, agent_id: str, meta: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new governed session for the given agent.

        Parameters
        ----------
        agent_id : str
            Identifier for the agent (e.g. ``"research-agent-v2"``).
        meta : dict, optional
            Arbitrary metadata attached to the session.

        Returns
        -------
        str
            The session ID assigned by the SelfConnect backend.
        """
        # Generate a unique session ID (VPS requires it in the request body)
        session_id = str(uuid.uuid4())
        payload: Dict[str, Any] = {"session_id": session_id, "agent_id": agent_id}
        if meta:
            payload["meta"] = meta

        resp = self._request("POST", "/sessions/start", json=payload)
        # VPS echoes back the session_id; fall back to the one we generated
        return resp.get("session_id", session_id)

    def end_session(self, session_id: str, summary: Optional[str] = None) -> Dict[str, Any]:
        """
        End an active session.

        Parameters
        ----------
        session_id : str
            The session ID returned by :meth:`start_session`.
        summary : str, optional
            Human-readable summary of what the agent accomplished.

        Returns
        -------
        dict
            The final session record from the backend.
        """
        payload: Dict[str, Any] = {"session_id": session_id}
        if summary:
            payload["summary"] = summary
        return self._request("POST", "/sessions/end", json=payload)

    # ------------------------------------------------------------------
    # Event posting
    # ------------------------------------------------------------------

    def post_event(
        self,
        session_id: str,
        event_type: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        decision: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Post a single agent event to the SelfConnect audit trail.

        Parameters
        ----------
        session_id : str
            Active session ID.
        event_type : str
            Type of event (e.g. ``"llm_call"``, ``"tool_use"``, ``"policy_check"``).
        tokens_input : int
            Number of input tokens consumed.
        tokens_output : int
            Number of output tokens generated.
        decision : str, optional
            Decision made by the agent (e.g. ``"approved"``, ``"denied"``).
        meta : dict, optional
            Additional metadata.

        Returns
        -------
        dict
            The event record as stored by the backend.

        Raises
        ------
        BudgetExhaustedError
            If the TSK key's token budget is exhausted.
        TskInvalidError
            If the TSK key is invalid or revoked.
        """
        payload: Dict[str, Any] = {
            "session_id": session_id,
            "event_type": event_type,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
        }
        if decision is not None:
            payload["decision"] = decision
        if meta:
            payload["meta"] = meta

        return self._request("POST", "/events", json=payload)

    def post_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Post multiple events in a single batch request.

        Parameters
        ----------
        events : list of dict
            Each dict should match the :meth:`post_event` parameter shape
            (``session_id``, ``event_type``, ``tokens_input``, ``tokens_output``,
            optional ``decision``, optional ``meta``).

        Returns
        -------
        list of dict
            List of stored event records.
        """
        results = []
        for event in events:
            result = self.post_event(
                session_id=event["session_id"],
                event_type=event["event_type"],
                tokens_input=event.get("tokens_input", 0),
                tokens_output=event.get("tokens_output", 0),
                decision=event.get("decision"),
                meta=event.get("meta"),
            )
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Budget & workflow
    # ------------------------------------------------------------------

    def get_budget(self) -> BudgetInfo:
        """
        Retrieve the current budget status for this TSK key.

        Returns
        -------
        BudgetInfo
            TypedDict with ``budget``, ``used``, ``remaining``, ``pct_used``,
            ``is_system``, ``registered``.
        """
        data = self._request("GET", f"/budget/{self.tsk_key}")
        budget = int(data.get("budget", 0))
        used = int(data.get("used", 0))
        remaining = max(0, budget - used)
        pct_used = round((used / budget * 100) if budget > 0 else 0.0, 2)
        return BudgetInfo(
            budget=budget,
            used=used,
            remaining=remaining,
            pct_used=pct_used,
            is_system=bool(data.get("is_system", False)),
            registered=bool(data.get("registered", True)),
        )

    def get_session_workflow(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve the full workflow / chain-of-custody for a session.

        Parameters
        ----------
        session_id : str
            The session ID to retrieve.

        Returns
        -------
        dict
            Workflow data including ``chain_of_custody`` (list of events with
            cryptographic hash chain).
        """
        return self._request("GET", f"/workflows/{session_id}")

    def get_tsk_info(self) -> Dict[str, Any]:
        """
        Retrieve metadata about this TSK key from the backend.

        Returns
        -------
        dict
            Key info including ``key``, ``user_id``, ``budget``, ``used``,
            ``revoked``, ``created_at``.
        """
        return self._request("GET", f"/tsk/info/{self.tsk_key}")

    def get_tsk_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve recent events posted under this TSK key.

        Parameters
        ----------
        limit : int
            Maximum number of events to return. Defaults to 100.

        Returns
        -------
        list of dict
            List of event records.
        """
        data = self._request("GET", f"/tsk/{self.tsk_key}/events")
        events = data if isinstance(data, list) else data.get("events", [])
        return events[:limit]

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    @contextmanager
    def session(
        self,
        agent_id: str,
        meta: Optional[Dict[str, Any]] = None,
        summary_fn: Optional[Any] = None,
    ) -> Generator[str, None, None]:
        """
        Context manager that auto-starts and auto-ends a governed session.

        Usage::

            with client.session("research-agent") as session_id:
                client.post_event(session_id, "llm_call", tokens_input=512)

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        meta : dict, optional
            Session metadata.
        summary_fn : callable, optional
            Zero-argument callable that returns a summary string for the session end.

        Yields
        ------
        str
            The active session ID.
        """
        session_id = self.start_session(agent_id, meta=meta)
        try:
            yield session_id
        finally:
            summary = summary_fn() if callable(summary_fn) else None
            try:
                self.end_session(session_id, summary=summary)
            except Exception:
                pass  # Don't mask the original exception

    # ------------------------------------------------------------------
    # Decorator
    # ------------------------------------------------------------------

    def governed_session(
        self,
        agent_id: str,
        meta: Optional[Dict[str, Any]] = None,
    ):
        """
        Decorator that wraps a function in a governed session.

        The decorated function receives ``session_id`` as its first argument
        (after ``self`` if it's a method).

        Usage::

            @client.governed_session("research-agent")
            def run_research(session_id: str, query: str):
                client.post_event(session_id, "llm_call", tokens_input=512)
                return "result"

            # Async functions are also supported:
            @client.governed_session("async-agent")
            async def run_async(session_id: str):
                ...

        Parameters
        ----------
        agent_id : str
            Agent identifier for the session.
        meta : dict, optional
            Session metadata.
        """
        def decorator(fn):
            if inspect.iscoroutinefunction(fn):
                @functools.wraps(fn)
                async def async_wrapper(*args, **kwargs):
                    session_id = self.start_session(agent_id, meta=meta)
                    try:
                        result = await fn(session_id, *args, **kwargs)
                        self.end_session(session_id)
                        return result
                    except Exception as exc:
                        try:
                            self.end_session(session_id, summary=f"Error: {exc}")
                        except Exception:
                            pass
                        raise
                return async_wrapper
            else:
                @functools.wraps(fn)
                def sync_wrapper(*args, **kwargs):
                    session_id = self.start_session(agent_id, meta=meta)
                    try:
                        result = fn(session_id, *args, **kwargs)
                        self.end_session(session_id)
                        return result
                    except Exception as exc:
                        try:
                            self.end_session(session_id, summary=f"Error: {exc}")
                        except Exception:
                            pass
                        raise
                return sync_wrapper
        return decorator

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute an HTTP request with retry logic and error mapping.

        Raises
        ------
        TskInvalidError
            On HTTP 401.
        PolicyDeniedError
            On HTTP 403.
        BudgetExhaustedError
            On HTTP 429.
        SelfConnectError
            On all other non-2xx responses.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self._http.request(method, path, json=json, params=params)
                return self._handle_response(resp)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self.max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                continue
        raise SelfConnectError(
            f"Failed to connect to SelfConnect API after {self.max_retries} attempts: {last_exc}"
        )

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            detail = self._extract_detail(resp)
            raise TskInvalidError(
                f"TSK key invalid or revoked: {detail}",
                status_code=401,
                detail=detail,
            )
        if resp.status_code == 403:
            detail = self._extract_detail(resp)
            raise PolicyDeniedError(
                f"Policy denied: {detail}",
                status_code=403,
                detail=detail,
            )
        if resp.status_code == 429:
            detail = self._extract_detail(resp)
            raise BudgetExhaustedError(
                f"TSK budget exhausted: {detail}",
                status_code=429,
                detail=detail,
            )
        if resp.status_code >= 400:
            detail = self._extract_detail(resp)
            raise SelfConnectError(
                f"SelfConnect API error {resp.status_code}: {detail}",
                status_code=resp.status_code,
                detail=detail,
            )
        try:
            return resp.json()
        except Exception:
            return {"ok": True, "raw": resp.text}

    @staticmethod
    def _extract_detail(resp: httpx.Response) -> str:
        try:
            body = resp.json()
            if isinstance(body, dict):
                return str(body.get("detail", {}).get("error", body.get("detail", resp.text)))
        except Exception:
            pass
        return resp.text

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        masked = self.tsk_key[:12] + "****"
        return f"TskClient(tsk_key={masked!r}, base_url={self.base_url!r})"

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "TskClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
