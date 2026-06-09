# selfconnect — Python SDK

**AI agent governance, cost control, and compliance for every framework.**

```bash
pip install selfconnect
```

---

## Quick Start

### 3-Line Integration

```python
from selfconnect import TskClient

client = TskClient(tsk_key="sc-tsk-YOUR-KEY")
with client.session("my-agent") as session_id:
    client.post_event(session_id, "llm_call", tokens_input=512, tokens_output=128)
```

---

## Core Concepts

The `TskClient` wraps every AI agent interaction with a **Trust Session Key (TSK)** — a cryptographically-bound identity that enforces budget limits, records every action in an immutable audit trail, and generates compliance reports on demand.

| Concept | Description |
|---|---|
| **TSK Key** | Identity token for an agent or team (`sc-tsk-XXXX-YYYY`) |
| **Session** | A bounded unit of work — start → events → end |
| **Event** | A single agent action (LLM call, tool use, policy check) |
| **Budget** | Token limit enforced at the API level — 429 when exhausted |
| **Audit Trail** | Cryptographic hash chain of all events — tamper-evident |

---

## Installation

```bash
# Core SDK
pip install selfconnect

# With LangChain support
pip install selfconnect[langchain]

# Development
pip install selfconnect[dev]
```

**Requirements:** Python ≥ 3.9, `httpx >= 0.24`

---

## Usage

### Basic Session Lifecycle

```python
from selfconnect import TskClient

client = TskClient(tsk_key="sc-tsk-YOUR-KEY")

# Manual lifecycle
session_id = client.start_session("research-agent", meta={"env": "production"})
client.post_event(session_id, "llm_call", tokens_input=1024, tokens_output=256)
client.post_event(session_id, "tool_use", meta={"tool": "web_search"})
client.end_session(session_id, summary="Research task completed")
```

### Context Manager (Recommended)

```python
with client.session("research-agent") as session_id:
    result = llm.invoke("Summarize the latest AI governance news")
    client.post_event(session_id, "llm_call", tokens_input=512, tokens_output=200)
# Session auto-ends on exit, even if an exception is raised
```

### Decorator

```python
@client.governed_session("data-pipeline-agent")
def run_pipeline(session_id: str, dataset: str) -> dict:
    client.post_event(session_id, "tool_use", meta={"tool": "data_loader", "dataset": dataset})
    # ... your agent logic ...
    return {"status": "complete"}

result = run_pipeline("sales_q4_2025")
```

### Async Support

```python
@client.governed_session("async-agent")
async def run_async_agent(session_id: str, query: str) -> str:
    client.post_event(session_id, "llm_call", tokens_input=256, tokens_output=128)
    return "result"

result = await run_async_agent("What is AI governance?")
```

### Batch Events

```python
events = [
    {"session_id": session_id, "event_type": "llm_call", "tokens_input": 512, "tokens_output": 128},
    {"session_id": session_id, "event_type": "tool_use", "meta": {"tool": "calculator"}},
    {"session_id": session_id, "event_type": "policy_check", "decision": "approved"},
]
client.post_events(events)
```

### Budget Monitoring

```python
budget = client.get_budget()
print(f"Used: {budget['used']:,} / {budget['budget']:,} tokens ({budget['pct_used']:.1f}%)")
print(f"Remaining: {budget['remaining']:,} tokens")
```

### Audit Trail

```python
workflow = client.get_session_workflow(session_id)
for event in workflow["chain_of_custody"]:
    print(f"[{event['event_type']}] hash={event['entry_hash'][:16]}...")
```

---

## LangChain Integration

```python
from langchain_openai import ChatOpenAI
from selfconnect import SelfConnectCallbackHandler

handler = SelfConnectCallbackHandler(
    tsk_key="sc-tsk-YOUR-KEY",
    agent_id="langchain-research-agent",
)

llm = ChatOpenAI(model="gpt-4o", callbacks=[handler])
response = llm.invoke("Explain AI governance in 3 sentences")

print(f"Session ID: {handler.session_id}")
```

**What gets recorded automatically:**
- Every LLM call with token counts and latency
- Every tool invocation
- Every agent action and finish
- Chain errors with stack context

---

## CrewAI Integration

```python
from crewai import Agent, Crew, Task
from selfconnect.integrations.crewai_example import GovernedCrew

crew = Crew(agents=[researcher, writer], tasks=[research_task, write_task])

governed = GovernedCrew(
    tsk_key="sc-tsk-YOUR-KEY",
    crew=crew,
    agent_id="content-creation-crew",
)
result = governed.kickoff(inputs={"topic": "AI governance"})
print(f"Session ID: {governed.session_id}")
```

---

## AutoGen Integration

```python
import autogen
from selfconnect.integrations.autogen_example import GovernedConversation

conv = GovernedConversation(
    tsk_key="sc-tsk-YOUR-KEY",
    initiator=user_proxy,
    recipient=assistant,
    agent_id="autogen-research",
)
result = conv.initiate_chat(
    message="Analyze the competitive landscape for AI governance tools",
    max_turns=5,
)
print(f"Session ID: {conv.session_id}")
```

---

## Error Handling

```python
from selfconnect import TskClient, BudgetExhaustedError, TskInvalidError, SelfConnectError

try:
    client.post_event(session_id, "llm_call", tokens_input=1000)
except BudgetExhaustedError:
    # TSK budget exhausted — agent must stop
    print("Budget exhausted. Request a top-up from your SelfConnect admin.")
except TskInvalidError:
    # Key revoked or invalid
    print("TSK key is invalid or has been revoked.")
except SelfConnectError as e:
    # Other API errors
    print(f"API error {e.status_code}: {e}")
```

---

## API Reference

### `TskClient`

| Method | Description |
|---|---|
| `start_session(agent_id, meta=None)` | Start a session, returns `session_id` |
| `end_session(session_id, summary=None)` | End a session |
| `post_event(session_id, event_type, ...)` | Post a single event |
| `post_events(events)` | Post a batch of events |
| `get_budget()` | Get current budget status |
| `get_session_workflow(session_id)` | Get audit trail for a session |
| `get_tsk_info()` | Get metadata for this TSK key |
| `get_tsk_events(limit=100)` | Get recent events for this key |
| `session(agent_id)` | Context manager — auto start/end |
| `governed_session(agent_id)` | Decorator — auto start/end |
| `close()` | Close HTTP connection pool |

### `SelfConnectCallbackHandler`

| Parameter | Default | Description |
|---|---|---|
| `tsk_key` | required | Your TSK key |
| `agent_id` | `"langchain-agent"` | Agent identifier |
| `auto_session` | `True` | Auto-start/end sessions |
| `session_id` | `None` | Attach to existing session |
| `raise_on_error` | `False` | Re-raise SDK errors |

---

## Environment Variables

| Variable | Description |
|---|---|
| `SELFCONNECT_TSK_KEY` | Default TSK key (used by integration tests) |
| `SELFCONNECT_BASE_URL` | Override API base URL |

---

## Testing

```bash
# Unit tests only (no network required)
pytest tests/ -m "not integration"

# All tests including live API
SELFCONNECT_TSK_KEY=sc-tsk-YOUR-KEY pytest tests/ -v
```

---

## Compliance Standards

SelfConnect audit trails are designed to support:

- **EU AI Act** — Article 12 (record-keeping), Article 13 (transparency)
- **NIST 800-53** — AU-2 (audit events), AU-9 (protection of audit info)
- **ISO 42001** — AI management system evidence requirements
- **IL4/IL5/IL6/IL7** — Government and regulated industry requirements

---

## Links

- **Dashboard**: [selfconnect.ai](https://selfconnect.ai)
- **API Docs**: [selfconnect.ai/docs](https://selfconnect.ai/docs)
- **GitHub**: [rblake2320/selfconnect-ecosystem](https://github.com/rblake2320/selfconnect-ecosystem)
- **Issues**: [GitHub Issues](https://github.com/rblake2320/selfconnect-ecosystem/issues)

---

## License

MIT © SelfConnect.ai
