"""
SelfConnect + CrewAI Integration Example

Wraps a CrewAI crew with SelfConnect governance so every agent action,
LLM call, and tool use is recorded in the SelfConnect audit trail.

Requirements:
    pip install selfconnect crewai

Usage::

    from selfconnect.integrations.crewai_example import GovernedCrew

    crew = GovernedCrew(
        tsk_key="sc-tsk-YOUR-KEY",
        crew=my_crewai_crew,
        agent_id="my-crewai-crew",
    )
    result = crew.kickoff(inputs={"topic": "AI governance"})
    print(result)
    print(f"Session ID: {crew.session_id}")
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class GovernedCrew:
    """
    Wraps a CrewAI ``Crew`` instance with SelfConnect governance.

    Parameters
    ----------
    tsk_key : str
        SelfConnect TSK key.
    crew : crewai.Crew
        The CrewAI crew to govern.
    agent_id : str
        Identifier for this crew in the SelfConnect audit trail.
    base_url : str
        SelfConnect API base URL.
    """

    def __init__(
        self,
        tsk_key: str,
        crew: Any,
        agent_id: str = "crewai-crew",
        base_url: str = "https://api.selfconnect.ai",
    ) -> None:
        from selfconnect import TskClient

        self.client = TskClient(tsk_key=tsk_key, base_url=base_url)
        self.crew = crew
        self.agent_id = agent_id
        self._session_id: Optional[str] = None

    @property
    def session_id(self) -> Optional[str]:
        """The session ID for the most recent kickoff."""
        return self._session_id

    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """
        Start a governed session, run the crew, and end the session.

        Parameters
        ----------
        inputs : dict, optional
            Inputs passed to ``crew.kickoff()``.

        Returns
        -------
        Any
            The result from ``crew.kickoff()``.
        """
        self._session_id = self.client.start_session(
            agent_id=self.agent_id,
            meta={"framework": "crewai", "inputs": str(inputs or {})[:500]},
        )
        try:
            result = self.crew.kickoff(inputs=inputs or {})
            # Post a summary event
            self.client.post_event(
                session_id=self._session_id,
                event_type="crew_completed",
                decision="completed",
                meta={"result_preview": str(result)[:500]},
            )
            self.client.end_session(self._session_id, summary="CrewAI crew completed successfully")
            return result
        except Exception as exc:
            self.client.post_event(
                session_id=self._session_id,
                event_type="crew_error",
                decision="error",
                meta={"error": str(exc)},
            )
            self.client.end_session(self._session_id, summary=f"CrewAI crew failed: {exc}")
            raise


# ---------------------------------------------------------------------------
# Standalone example (run directly to test)
# ---------------------------------------------------------------------------

def _demo():
    """
    Minimal demo showing how to use GovernedCrew.
    Requires crewai to be installed.
    """
    try:
        from crewai import Agent, Crew, Process, Task
        from langchain_openai import ChatOpenAI
    except ImportError:
        print("Install crewai and langchain-openai to run this demo.")
        return

    import os

    TSK_KEY = os.environ.get("SELFCONNECT_TSK_KEY", "sc-tsk-TESTER-0000")

    researcher = Agent(
        role="Researcher",
        goal="Research AI governance best practices",
        backstory="Expert in AI policy and compliance",
        verbose=True,
    )

    task = Task(
        description="Summarize the top 3 AI governance frameworks",
        expected_output="A concise 3-point summary",
        agent=researcher,
    )

    crew = Crew(agents=[researcher], tasks=[task], process=Process.sequential, verbose=True)

    governed = GovernedCrew(tsk_key=TSK_KEY, crew=crew, agent_id="demo-researcher")
    result = governed.kickoff()
    print(f"\nResult: {result}")
    print(f"Session ID: {governed.session_id}")


if __name__ == "__main__":
    _demo()
