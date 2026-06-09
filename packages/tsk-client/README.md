# @selfconnect/tsk-client

**Govern any AI agent in 3 lines of code.**

The SelfConnect TSK (Token Safety Key) client wraps the `api.selfconnect.ai` VPS with automatic budget enforcement, session lifecycle management, and EU AI Act compliance event logging.

---

## Installation

```bash
npm install @selfconnect/tsk-client
# or
pnpm add @selfconnect/tsk-client
```

---

## Quick Start

```ts
import { TskClient } from "@selfconnect/tsk-client";

const tsk = new TskClient({
  key: "sc-tsk-your-key-here",
  vps: "https://api.selfconnect.ai",
});

// Start a session
await tsk.sessionStart({
  sessionId: "session-abc123",
  agentId: "my-gpt4-agent",
  model: "gpt-4o",
  vendor: "openai",
});

// Log an event (tool call, policy check, etc.)
await tsk.event({
  sessionId: "session-abc123",
  eventType: "TOOL_CALL",
  toolName: "web_search",
  tokensInput: 250,
  tokensOutput: 180,
  decision: "ALLOW",
});

// End the session
await tsk.sessionEnd("session-abc123");
```

---

## From Environment Variables

```bash
export SELFCONNECT_TSK_KEY="sc-tsk-your-key-here"
```

```ts
import { fromEnv } from "@selfconnect/tsk-client";

const tsk = fromEnv();
```

---

## Budget Alerts

```ts
tsk.on("budget:warning", (info) => {
  console.warn(`⚠️  Budget at ${info.pctUsed.toFixed(1)}% — ${info.remaining} tokens left`);
});

tsk.on("budget:exhausted", (info) => {
  console.error("🚨 Budget exhausted — agent will be stopped");
  // Gracefully shut down your agent here
});
```

---

## Event Types

| Event Type | When to use |
|---|---|
| `SESSION_START` | Agent session begins |
| `TOOL_CALL` | Agent invokes a tool |
| `POLICY_ALLOW` | Policy check passed |
| `POLICY_DENY` | Policy check blocked action |
| `LLM_CALL` | LLM inference request |
| `SESSION_END` | Agent session ends |

---

## API Reference

### `new TskClient(opts)`

| Option | Type | Default | Description |
|---|---|---|---|
| `key` | `string` | **required** | TSK key (starts with `sc-tsk-`) |
| `vps` | `string` | `https://api.selfconnect.ai` | VPS base URL |
| `pollIntervalMs` | `number` | `30000` | Budget poll interval (0 = disabled) |
| `warningThreshold` | `number` | `0.8` | Budget warning threshold (0–1) |
| `autoEndOnExit` | `boolean` | `true` | Auto-end sessions on SIGTERM/SIGINT |
| `maxRetries` | `number` | `3` | Max retries for 5xx errors |
| `rejectUnauthorized` | `boolean` | `true` | TLS cert verification |

### `tsk.sessionStart(opts)`

Starts a session on the VPS and registers it for auto-cleanup.

### `tsk.sessionEnd(sessionId)`

Ends a session. Called automatically on process exit if `autoEndOnExit: true`.

### `tsk.event(opts)`

Posts a single event to the VPS. Throws `TskBudgetError` if budget is exhausted.

### `tsk.getBudget()`

Returns current budget info: `{ budgetTokens, tokensUsed, remaining, pctUsed, isExhausted }`.

### `fromEnv(overrides?)`

Creates a `TskClient` from `SELFCONNECT_TSK_KEY` and `SELFCONNECT_VPS_URL` env vars.

---

## Error Handling

```ts
import { TskBudgetError, TskAuthError, TskError } from "@selfconnect/tsk-client";

try {
  await tsk.event({ sessionId: "s1", eventType: "TOOL_CALL", tokensInput: 500 });
} catch (err) {
  if (err instanceof TskBudgetError) {
    console.error("Budget exhausted:", err.budget.tokensUsed, "/", err.budget.budgetTokens);
  } else if (err instanceof TskAuthError) {
    console.error("Invalid or revoked TSK key");
  } else if (err instanceof TskError) {
    console.error("VPS error:", err.status, err.body);
  }
}
```

---

## Compliance

Every event posted through this client is logged to the SelfConnect VPS with:
- Immutable hash chain (SHA-256 linked entries)
- Actor inventory (all agent DIDs)
- EU AI Act Article 12 / Annex IV compliance bundle export

Retrieve your compliance bundle at any time:
```
GET https://api.selfconnect.ai/compliance/bundle
X-TSK-Key: sc-tsk-your-key-here
```

---

## License

MIT © SelfConnect.ai
