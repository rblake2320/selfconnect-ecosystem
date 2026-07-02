# SelfConnect Ecosystem — Implementation Notes

## VPS: api.selfconnect.ai

**Base URL:** `https://api.selfconnect.ai`
**SSL:** Let's Encrypt cert covering api.selfconnect.ai, selfconnect.ai, www.selfconnect.ai (expanded June 2026)
**Backend:** FastAPI + uvicorn on port 8090, proxied by nginx on port 443
**Database:** SQLite at /home/selfconnect/.selfconnect/store.db

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | None | Service health + TSK enforcement status |
| POST | /events | X-TSK-Key | Ingest agent event (budget enforced) |
| GET | /events/stream | None | SSE real-time event stream |
| POST | /sessions/start | X-TSK-Key | Register session start |
| POST | /sessions/end | X-TSK-Key | Register session end |
| GET | /sessions | None | List sessions |
| GET | /summary | None | Event summary stats |
| GET | /workflows/{session_id} | None | Session chain_of_custody |
| GET | /compliance/bundle | None | EU AI Act + NIST 800-53 + ISO 42001 bundle |
| GET | /budget/{tsk_key} | None | TSK budget status |
| POST | /tsk/register | None | Register a new TSK key |
| POST | /tsk/revoke | None | Revoke a TSK key |
| GET | /tsk/list | None | List all TSK keys |
| GET | /tsk/info/{tsk_key} | None | TSK key details |
| GET | /tsk/{tsk_key}/events | None | Events posted by a specific TSK key |
| POST | /webhooks/register | X-TSK-Key | Register a webhook URL |
| GET | /webhooks/list | X-TSK-Key | List registered webhooks |
| POST | /webhooks/{id}/test | X-TSK-Key | Test a webhook |
| DELETE | /webhooks/{id} | X-TSK-Key | Delete a webhook |

### Permanent Tester Key
- Key: sc-tsk-TESTER-0000
- Budget: 10,000,000,000 tokens (10B, effectively unlimited)
- Protected: Cannot be revoked (is_system = 1)
- Use for: CI/CD, integration tests, mesh harness, development

### Webhook Events
Webhooks fire on: budget_warning (80%), budget_exhausted (100%), policy_deny, session_end

---

## @selfconnect/tsk-client SDK

Location: packages/tsk-client/
Version: 1.0.0

### 3-Line Integration
```typescript
import { TskClient } from "@selfconnect/tsk-client";
const client = new TskClient({ tskKey: "sc-tsk-YOUR-KEY", baseUrl: "https://api.selfconnect.ai" });
await client.startSession("my-session-001", "my-agent");
await client.postEvent({ session_id: "my-session-001", agent_id: "my-agent", event_type: "TOOL_CALL", ts: Date.now()/1000 });
await client.endSession("my-session-001");
```

### API
- new TskClient({ tskKey, baseUrl? }) — create client
- client.startSession(sessionId, agentId, meta?) — register session start
- client.postEvent(event) — post a single event
- client.postEvents(events[]) — post multiple events
- client.endSession(sessionId, meta?) — register session end
- client.getBudget() — get current budget status { budget, used, remaining, pct_used }
- client.getSessionWorkflow(sessionId) — get chain_of_custody for a session

---

## selfconnect-store Changelog

### v2.1.0 (June 2026)
- Added tsk_keys table with budget enforcement
- Added TSK validation middleware on POST /events
- Added /tsk/register, /tsk/revoke, /tsk/list, /tsk/info/{key}, /tsk/{key}/events
- Added /sessions/start, /sessions/end
- Added GET /events/stream SSE endpoint
- Added webhooks table and /webhooks/* CRUD endpoints
- Added tsk_key column to events table for per-key event history
- Expanded Let's Encrypt cert to cover api.selfconnect.ai
- Fixed SQLite unixepoch() compatibility (replaced with strftime('%s','now'))

### v1.0.0 (Initial)
- Basic event ingestion via POST /events
- SQLite-backed storage
- /health, /summary, /sessions, /compliance/bundle, /workflows/{id}

---

## Mesh Test Harness

Location: selfconnect-store/tests/sc_mesh_test.py

Simulates 4 concurrent AI agents (Claude, GPT-4, Gemini, Codex) with independent TSK keys.
One agent is given a low budget to demonstrate hard-stop enforcement.

Run: python3 tests/sc_mesh_test.py
Expected: 16/16 checks pass

---

## Security Test Suite

Location: selfconnect-beta/server/security.e2e.test.ts

50 tests covering TSK enforcement, prompt injection defense, session lifecycle,
audit trail chain integrity, budget enforcement, compliance bundle, TSK admin ops,
input validation, replay protection, CORS validation.

Run: pnpm test server/security.e2e.test.ts
Expected: 50/50 pass

---

## Python SDK (selfconnect v1.0.0)

Location: packages/selfconnect-py/
Install: `pip install selfconnect` (or `pip install -e packages/selfconnect-py/`)

### Key Classes
- `TskClient`: core client — start_session, post_event, post_events, end_session, get_budget, get_session_workflow, get_tsk_info, get_tsk_events
- `SelfConnectCallbackHandler`: LangChain callback handler — auto-instruments all LLM calls, tool uses, chain events
- `GovernedCrew` (integrations/crewai_example.py): wraps CrewAI Crew with governance
- `GovernedConversation` (integrations/autogen_example.py): wraps AutoGen conversations with governance

### 3-Line Integration
```python
from selfconnect import TskClient
client = TskClient(tsk_key="sc-tsk-YOUR-KEY")
with client.session("my-agent") as session_id:
    client.post_event(session_id, "llm_call", tokens_input=512, tokens_output=128)
```

### Tests
34 passing (27 unit + 7 live integration against api.selfconnect.ai)
Run: `cd packages/selfconnect-py && pytest tests/ -v`

### VPS Bugfix Applied
/tsk/{key}/events endpoint fixed: `created_at` → `ingested_at`, `_store()` → `_db()`

GitHub: commit b5fe59b
