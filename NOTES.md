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
