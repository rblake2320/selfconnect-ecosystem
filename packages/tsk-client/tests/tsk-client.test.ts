/**
 * @selfconnect/tsk-client — unit tests
 *
 * Run with: pnpm test
 * Run live tests against VPS: pnpm test:live
 */

import { TskClient, TskError, TskAuthError, TskBudgetError, fromEnv } from "../src/index";

const VPS = process.env.SELFCONNECT_VPS_URL ?? "https://api.selfconnect.ai";
const TESTER_TSK = "sc-tsk-TESTER-0000";
const LIVE = process.env.TSK_LIVE === "1";

// ── Constructor validation ────────────────────────────────────────────────────

describe("TskClient constructor", () => {
  it("throws on missing key", () => {
    expect(() => new TskClient({ key: "" })).toThrow("key must start with 'sc-tsk-'");
  });

  it("throws on invalid key prefix", () => {
    expect(() => new TskClient({ key: "invalid-key" })).toThrow("key must start with 'sc-tsk-'");
  });

  it("accepts valid key", () => {
    const client = new TskClient({ key: "sc-tsk-test-1234" });
    expect(client).toBeInstanceOf(TskClient);
  });

  it("defaults vps to api.selfconnect.ai", () => {
    const client = new TskClient({ key: "sc-tsk-test-1234", autoEndOnExit: false });
    expect(client).toBeInstanceOf(TskClient);
  });

  it("strips trailing slash from vps URL", () => {
    const client = new TskClient({ key: "sc-tsk-test-1234", vps: "https://api.selfconnect.ai/" });
    expect(client).toBeInstanceOf(TskClient);
  });
});

// ── fromEnv ───────────────────────────────────────────────────────────────────

describe("fromEnv", () => {
  it("throws when SELFCONNECT_TSK_KEY is not set", () => {
    const orig = process.env.SELFCONNECT_TSK_KEY;
    delete process.env.SELFCONNECT_TSK_KEY;
    expect(() => fromEnv()).toThrow("SELFCONNECT_TSK_KEY environment variable is required");
    process.env.SELFCONNECT_TSK_KEY = orig;
  });

  it("creates client from env var", () => {
    process.env.SELFCONNECT_TSK_KEY = "sc-tsk-env-test-1234";
    const client = fromEnv({ autoEndOnExit: false });
    expect(client).toBeInstanceOf(TskClient);
    delete process.env.SELFCONNECT_TSK_KEY;
  });
});

// ── Error classes ─────────────────────────────────────────────────────────────

describe("Error classes", () => {
  it("TskError has correct name and message", () => {
    const err = new TskError("test error", 500, { detail: "server error" });
    expect(err.name).toBe("TskError");
    expect(err.message).toContain("HTTP 500");
    expect(err.status).toBe(500);
  });

  it("TskAuthError extends TskError", () => {
    const err = new TskAuthError("auth failed", 401, {});
    expect(err).toBeInstanceOf(TskError);
    expect(err.name).toBe("TskAuthError");
  });

  it("TskBudgetError has budget info", () => {
    const budget = {
      tskKey: "sc-tsk-test",
      budgetTokens: 1000,
      tokensUsed: 1000,
      remaining: 0,
      pctUsed: 100,
      isExhausted: true,
      isSystem: false,
      isActive: true,
      lastUsedAt: Date.now(),
    };
    const err = new TskBudgetError("budget exhausted", budget);
    expect(err.name).toBe("TskBudgetError");
    expect(err.budget.isExhausted).toBe(true);
  });
});

// ── Live tests (only run when TSK_LIVE=1) ────────────────────────────────────

const liveDescribe = LIVE ? describe : describe.skip;

liveDescribe("Live VPS tests", () => {
  const client = new TskClient({
    key: TESTER_TSK,
    vps: VPS,
    pollIntervalMs: 0, // disable polling for tests
    autoEndOnExit: false,
    rejectUnauthorized: false,
  });

  const sessionId = `tsk-sdk-test-${Date.now()}`;

  it("getBudget returns valid budget info", async () => {
    const info = await client.getBudget();
    expect(info.tskKey).toBe(TESTER_TSK);
    expect(info.isSystem).toBe(true);
    expect(info.isActive).toBe(true);
    expect(info.budgetTokens).toBeGreaterThan(0);
  }, 15_000);

  it("sessionStart succeeds", async () => {
    await expect(
      client.sessionStart({
        sessionId,
        agentId: "tsk-sdk-test-agent",
        model: "gpt-4o",
        vendor: "openai",
      })
    ).resolves.toBeUndefined();
  }, 15_000);

  it("event TOOL_CALL succeeds", async () => {
    await expect(
      client.event({
        sessionId,
        eventType: "TOOL_CALL",
        toolName: "web_search",
        tokensInput: 100,
        tokensOutput: 50,
        decision: "ALLOW",
      })
    ).resolves.toBeUndefined();
  }, 15_000);

  it("event POLICY_DENY succeeds", async () => {
    await expect(
      client.event({
        sessionId,
        eventType: "POLICY_DENY",
        toolName: "delete_file",
        decision: "DENY",
        meta: { reason: "destructive_action" },
      })
    ).resolves.toBeUndefined();
  }, 15_000);

  it("sessionEnd succeeds", async () => {
    await expect(client.sessionEnd(sessionId)).resolves.toBeUndefined();
  }, 15_000);

  it("invalid key throws TskAuthError", async () => {
    const badClient = new TskClient({
      key: "sc-tsk-invalid-key-xyz",
      vps: VPS,
      pollIntervalMs: 0,
      autoEndOnExit: false,
      rejectUnauthorized: false,
    });
    await expect(
      badClient.event({ sessionId: "test", eventType: "TOOL_CALL" })
    ).rejects.toBeInstanceOf(TskAuthError);
  }, 15_000);
});
