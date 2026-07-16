# selfconnect — Python SDK

Python client and optional framework adapters for SelfConnect session,
budget-status, and event APIs.

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

`TskClient` presents a server-issued TSK credential to a configured SelfConnect
API. The server can accept or reject session and event requests, including
returning `401`, `403`, or `429`; direct client calls surface those responses as
typed exceptions. The SDK does not itself establish hardware binding,
cryptographic identity, storage immutability, event completeness, or a
deployment authorization.

| Concept | Description |
|---|---|
| **TSK Key** | Server-issued bearer credential (`sc-tsk-XXXX-YYYY`) |
| **Session** | A bounded unit of work — start → events → end |
| **Event** | A caller-reported event such as an LLM call, tool use, or policy decision |
| **Budget** | Server-reported token budget; direct calls raise on a `429` response |
| **Hash chain** | Server-reported retained event chain; useful for tamper detection within its stated boundary |

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

### Server-Reported Workflow Data

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

**What the callback adapter attempts to report:**
- LLM callbacks received while a SelfConnect session is active
- Tool callbacks received while a SelfConnect session is active
- Agent action/finish callbacks received by the handler
- Chain error callbacks and bounded error text

`raise_on_error=False` is the default. In that mode, SelfConnect API failures
are logged and LangChain execution continues, so the adapter is fail-open
telemetry rather than a non-bypassable enforcement boundary. Set
`raise_on_error=True` when the caller requires callback delivery errors to stop
execution.

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
| `get_session_workflow(session_id)` | Get server-reported workflow and event hash-chain data |
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
SELFCONNECT_TSK_KEY=sc-tsk-YOUR-KEY \
SELFCONNECT_BASE_URL=https://your-disposable-test-api.example \
pytest tests/ -m integration -v
```

---

## Evidence and Authorization Boundary

The SDK can retrieve server-reported events and hash-chain fields that an
operator may include in a broader evidence package. It does not by itself
establish EU AI Act, ISO 42001, NIST SP 800-53, FIPS 140, FedRAMP, ATO, or DoD
Impact Level compliance or authorization. Those conclusions depend on the
deployed server, complete system boundary, configuration, custody, assessment,
and approving authority.

Hash chaining can reveal modification of retained entries. It does not by
itself prove that all events were captured, prevent truncation/deletion, bind
events to a signer, or make storage immutable.

## Credential Storage

Prefer `SELFCONNECT_TSK_KEY` supplied by an operating-system or CI secret store.
`selfconnect login` writes the credential to `~/.selfconnect/config.json`.
Although the CLI requests owner-only file mode where supported, `chmod(0600)`
is not a Windows ACL guarantee. Do not treat the local JSON file as a hardware-
backed or independently attested credential store.

---

## Links

- **Dashboard**: [selfconnect.ai](https://selfconnect.ai)
- **API Docs**: [selfconnect.ai/docs](https://selfconnect.ai/docs)
- **Source**: [packages/selfconnect-py](https://github.com/rblake2320/selfconnect-ecosystem/tree/main/packages/selfconnect-py)
- **Issues**: [GitHub Issues](https://github.com/rblake2320/selfconnect-ecosystem/issues)

---

## License

MIT © SelfConnect.ai
