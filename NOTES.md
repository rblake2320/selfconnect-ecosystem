# SelfConnect Ecosystem — Integration Notes (2026-06-09)

## TSK Protocol — Live on VPS

The `selfconnect-store` submodule has been upgraded to v2.0.0 with full TSK (Token Signing Key) enforcement. All `POST /events` calls to `api.selfconnect.ai` now require an `X-TSK-Key` header.

### What Changed

**selfconnect-store** (commit 5fbb5ff on master):
- New `tsk_keys` SQLite table with budget enforcement
- All 9 new TSK/session/SSE endpoints live on the VPS
- Permanent tester key `sc-tsk-TESTER-0000` (10B token budget, cannot be revoked)
- 50/50 security tests passing

**selfconnect-beta** (web app at selfconnect.ai):
- TSK keys are generated on user signup and synced to the VPS
- TSK regeneration revokes the old key on VPS and registers the new one
- Admin panel has TSK management: list all keys, revoke, restore, budget top-up
- User dashboard shows live VPS TSK status (is_active, budget used, last_used_at)
- Enterprise dashboard has real-time SSE live event feed from VPS
- Audit trail page shows chain-of-custody with hash verification
- Compliance bundle export (EU AI Act / NIST 800-53 / ISO 42001)
- Mesh test harness for 4-agent cross-vendor simulation

### VPS Endpoints (api.selfconnect.ai)

| Endpoint | Auth Required | Description |
|----------|--------------|-------------|
| GET /health | None | Liveness check |
| GET /summary | None | Aggregate stats |
| GET /sessions | None | Session list |
| GET /sessions/{id} | None | Session detail |
| GET /workflows/{id} | None | Chain-of-custody for session |
| GET /compliance/bundle | None | EU AI Act evidence export |
| POST /events | X-TSK-Key | Ingest a governance event |
| POST /tsk/register | None | Register a new TSK key |
| POST /tsk/revoke | None | Revoke a TSK key |
| GET /tsk/info/{key} | None | Key metadata |
| GET /tsk/list | None | List all keys |
| GET /tsk/{key}/events | None | Events by key |
| GET /budget/{key} | None | Budget usage |
| POST /sessions/start | X-TSK-Key | Start a session |
| POST /sessions/end | X-TSK-Key | End a session |
| GET /events/stream | None | SSE live stream |

### Security Test Results (50/50 passing)

Tests run against `api.selfconnect.ai` on 2026-06-09. All 50 tests green:
- TSK enforcement (7 tests): missing key, fake key, SQL injection, XSS, valid key, system key protection
- Prompt injection defense (10 tests): 8 attack vectors, JSON bomb, array bomb
- Session lifecycle (7 tests): full start→event→end→list→workflow flow
- Audit trail chain integrity (3 tests): compliance bundle fields, workflow chain_of_custody
- Budget enforcement (3 tests): tester key budget, fields, never exhausted
- TSK admin operations (7 tests): register, post, revoke, verify rejected, list, info, system protection
- Input validation (7 tests): missing fields, negative tokens, year 2099, 1000-char IDs, Unicode
- Replay protection (1 test): duplicate event is idempotent
- CORS (1 test): headers present
- Summary endpoints (3 tests): /summary, /sessions, /health fields
