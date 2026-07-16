"""
SelfConnect + AutoGen Integration Example

Wraps an AutoGen conversation with session start, summary, completion, and
error events. It does not observe every internal message or tool call.

Requirements:
    pip install selfconnect pyautogen

Usage::

    from selfconnect.integrations.autogen_example import GovernedConversation

    conv = GovernedConversation(
        tsk_key="sc-tsk-YOUR-KEY",
        initiator=user_proxy,
        recipient=assistant,
        agent_id="my-autogen-conversation",
    )
    result = conv.initiate_chat(message="Analyze this dataset...")
    print(f"Session ID: {conv.session_id}")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class GovernedConversation:
    """
    Wraps an AutoGen conversation with bounded SelfConnect event reporting.

    Parameters
    ----------
    tsk_key : str
        SelfConnect TSK key.
    initiator : autogen.ConversableAgent
        The agent that initiates the conversation.
    recipient : autogen.ConversableAgent
        The agent that receives the initial message.
    agent_id : str
        Identifier used for this conversation's SelfConnect event records.
    base_url : str
        SelfConnect API base URL.
    """

    def __init__(
        self,
        tsk_key: str,
        initiator: Any,
        recipient: Any,
        agent_id: str = "autogen-conversation",
        base_url: str = "https://api.selfconnect.ai",
    ) -> None:
        from selfconnect import TskClient

        self.client = TskClient(tsk_key=tsk_key, base_url=base_url)
        self.initiator = initiator
        self.recipient = recipient
        self.agent_id = agent_id
        self._session_id: Optional[str] = None

    @property
    def session_id(self) -> Optional[str]:
        """The session ID for the most recent conversation."""
        return self._session_id

    def initiate_chat(
        self,
        message: str,
        max_turns: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Start a governed session, run the AutoGen conversation, and end the session.

        Parameters
        ----------
        message : str
            The initial message to send.
        max_turns : int, optional
            Maximum number of conversation turns.
        **kwargs
            Additional keyword arguments passed to ``initiator.initiate_chat()``.

        Returns
        -------
        Any
            The chat result from AutoGen.
        """
        self._session_id = self.client.start_session(
            agent_id=self.agent_id,
            meta={
                "framework": "autogen",
                "initiator": getattr(self.initiator, "name", "unknown"),
                "recipient": getattr(self.recipient, "name", "unknown"),
                "message_preview": message[:200],
            },
        )

        # Post the initial message as an event
        self.client.post_event(
            session_id=self._session_id,
            event_type="conversation_start",
            meta={"message_preview": message[:500]},
        )

        try:
            chat_kwargs: Dict[str, Any] = {"message": message, **kwargs}
            if max_turns is not None:
                chat_kwargs["max_turns"] = max_turns

            result = self.initiator.initiate_chat(self.recipient, **chat_kwargs)

            # Count messages and estimate tokens
            messages: List[Dict] = []
            try:
                messages = result.chat_history or []
            except AttributeError:
                pass

            total_tokens_est = sum(len(str(m.get("content", ""))) // 4 for m in messages)

            self.client.post_event(
                session_id=self._session_id,
                event_type="conversation_complete",
                tokens_input=total_tokens_est // 2,
                tokens_output=total_tokens_est // 2,
                decision="completed",
                meta={
                    "message_count": len(messages),
                    "total_tokens_estimate": total_tokens_est,
                },
            )
            self.client.end_session(
                self._session_id,
                summary=f"AutoGen conversation completed ({len(messages)} messages)",
            )
            return result

        except Exception as exc:
            self.client.post_event(
                session_id=self._session_id,
                event_type="conversation_error",
                decision="error",
                meta={"error": str(exc)},
            )
            self.client.end_session(self._session_id, summary=f"AutoGen conversation failed: {exc}")
            raise


# ---------------------------------------------------------------------------
# Standalone example (run directly to test)
# ---------------------------------------------------------------------------

def _demo():
    """
    Minimal demo showing how to use GovernedConversation.
    Requires pyautogen to be installed.
    """
    try:
        import autogen
    except ImportError:
        print("Install pyautogen to run this demo: pip install pyautogen")
        return

    import os

    TSK_KEY = os.environ.get("SELFCONNECT_TSK_KEY", "sc-tsk-TESTER-0000")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

    config_list = [{"model": "gpt-4o", "api_key": OPENAI_API_KEY}]

    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config={"config_list": config_list},
    )
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
        code_execution_config=False,
    )

    conv = GovernedConversation(
        tsk_key=TSK_KEY,
        initiator=user_proxy,
        recipient=assistant,
        agent_id="demo-autogen",
    )
    conv.initiate_chat(
        message="What are the top 3 benefits of AI governance?",
        max_turns=3,
    )
    print(f"\nSession ID: {conv.session_id}")


if __name__ == "__main__":
    _demo()
