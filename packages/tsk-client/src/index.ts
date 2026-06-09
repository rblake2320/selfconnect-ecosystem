/**
 * @selfconnect/tsk-client
 *
 * SelfConnect TSK (Token Safety Key) client.
 * Govern any AI agent in 3 lines of code:
 *
 *   const tsk = new TskClient({ key: "sc-tsk-...", vps: "https://api.selfconnect.ai" });
 *   await tsk.sessionStart({ sessionId: "my-session", agentId: "my-agent" });
 *   await tsk.event({ sessionId: "my-session", eventType: "TOOL_CALL", tokensInput: 120 });
 *
 * The client automatically:
 *   - Injects X-TSK-Key on every request
 *   - Polls budget and emits "budget:warning" at 80% and "budget:exhausted" at 100%
 *   - Ends the session on process exit (SIGTERM / SIGINT)
 *   - Retries transient 5xx errors with exponential backoff
 */

import { EventEmitter } from "events";
import * as https from "https";
import * as http from "http";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TskClientOptions {
  /** TSK key — starts with "sc-tsk-" */
  key: string;
  /** VPS base URL, e.g. "https://api.selfconnect.ai" */
  vps?: string;
  /**
   * Budget polling interval in milliseconds.
   * Set to 0 to disable polling. Default: 30_000 (30s).
   */
  pollIntervalMs?: number;
  /**
   * Budget warning threshold (0–1). Default: 0.8 (80%).
   * Emits "budget:warning" when pct_used crosses this threshold.
   */
  warningThreshold?: number;
  /**
   * Whether to automatically end the active session on SIGTERM/SIGINT.
   * Default: true.
   */
  autoEndOnExit?: boolean;
  /**
   * Maximum number of retries for transient 5xx errors. Default: 3.
   */
  maxRetries?: number;
  /**
   * Whether to skip TLS certificate verification. Only use for development.
   * Default: false.
   */
  rejectUnauthorized?: boolean;
}

export interface SessionStartOptions {
  sessionId: string;
  agentId: string;
  agentType?: string;
  model?: string;
  vendor?: string;
  meta?: Record<string, unknown>;
}

export interface EventOptions {
  sessionId: string;
  eventType: string;
  agentId?: string;
  toolName?: string;
  decision?: string;
  tokensInput?: number;
  tokensOutput?: number;
  tokensCache?: number;
  usdCost?: number;
  actorDid?: string;
  targetDid?: string;
  entryHash?: string;
  priorHash?: string;
  payloadHash?: string;
  meta?: Record<string, unknown>;
}

export interface BudgetInfo {
  tskKey: string;
  budgetTokens: number;
  tokensUsed: number;
  remaining: number;
  pctUsed: number;
  isExhausted: boolean;
  isSystem: boolean;
  isActive: boolean;
  lastUsedAt: number | null;
}

export interface TskClientEvents {
  "budget:warning": (info: BudgetInfo) => void;
  "budget:exhausted": (info: BudgetInfo) => void;
  "session:started": (sessionId: string) => void;
  "session:ended": (sessionId: string) => void;
  "event:accepted": (sessionId: string, eventType: string) => void;
  "event:rejected": (sessionId: string, status: number, error: string) => void;
  error: (err: Error) => void;
}

// ── Client ────────────────────────────────────────────────────────────────────

export class TskClient extends EventEmitter {
  private readonly key: string;
  private readonly vps: string;
  private readonly pollIntervalMs: number;
  private readonly warningThreshold: number;
  private readonly autoEndOnExit: boolean;
  private readonly maxRetries: number;
  private readonly rejectUnauthorized: boolean;

  private activeSessions: Set<string> = new Set();
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private warnedAt80 = false;
  private exhaustedEmitted = false;

  constructor(opts: TskClientOptions) {
    super();
    if (!opts.key || !opts.key.startsWith("sc-tsk-")) {
      throw new Error("TskClient: key must start with 'sc-tsk-'");
    }
    this.key = opts.key;
    this.vps = (opts.vps ?? "https://api.selfconnect.ai").replace(/\/$/, "");
    this.pollIntervalMs = opts.pollIntervalMs ?? 30_000;
    this.warningThreshold = opts.warningThreshold ?? 0.8;
    this.autoEndOnExit = opts.autoEndOnExit ?? true;
    this.maxRetries = opts.maxRetries ?? 3;
    this.rejectUnauthorized = opts.rejectUnauthorized ?? true;

    if (this.autoEndOnExit) {
      const cleanup = async () => {
        for (const sid of this.activeSessions) {
          try { await this.sessionEnd(sid); } catch { /* best-effort */ }
        }
        this.stopPolling();
      };
      process.once("SIGTERM", cleanup);
      process.once("SIGINT", cleanup);
    }
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  /** Start a session and register it for auto-cleanup on exit. */
  async sessionStart(opts: SessionStartOptions): Promise<void> {
    const body = {
      session_id: opts.sessionId,
      agent_id: opts.agentId,
      agent_type: opts.agentType,
      model: opts.model,
      vendor: opts.vendor,
      meta: opts.meta,
    };
    const res = await this._post("/sessions/start", body);
    if (res.status === 200) {
      this.activeSessions.add(opts.sessionId);
      this.emit("session:started", opts.sessionId);
      if (this.pollIntervalMs > 0 && !this.pollTimer) {
        this._startPolling();
      }
    } else {
      throw new TskError("sessionStart failed", res.status, res.body);
    }
  }

  /** End a session. */
  async sessionEnd(sessionId: string): Promise<void> {
    const body = { session_id: sessionId };
    const res = await this._post("/sessions/end", body);
    this.activeSessions.delete(sessionId);
    this.emit("session:ended", sessionId);
    if (this.activeSessions.size === 0) {
      this.stopPolling();
    }
    if (res.status !== 200) {
      throw new TskError("sessionEnd failed", res.status, res.body);
    }
  }

  /** Post a single event to the VPS. */
  async event(opts: EventOptions): Promise<void> {
    const body: Record<string, unknown> = {
      session_id: opts.sessionId,
      event_type: opts.eventType,
      ts: Date.now() / 1000,
    };
    if (opts.agentId !== undefined) body.agent_id = opts.agentId;
    if (opts.toolName !== undefined) body.tool_name = opts.toolName;
    if (opts.decision !== undefined) body.decision = opts.decision;
    if (opts.tokensInput !== undefined) body.tokens_input = opts.tokensInput;
    if (opts.tokensOutput !== undefined) body.tokens_output = opts.tokensOutput;
    if (opts.tokensCache !== undefined) body.tokens_cache = opts.tokensCache;
    if (opts.usdCost !== undefined) body.usd_cost = opts.usdCost;
    if (opts.actorDid !== undefined) body.actor_did = opts.actorDid;
    if (opts.targetDid !== undefined) body.target_did = opts.targetDid;
    if (opts.entryHash !== undefined) body.entry_hash = opts.entryHash;
    if (opts.priorHash !== undefined) body.prior_hash = opts.priorHash;
    if (opts.payloadHash !== undefined) body.payload_hash = opts.payloadHash;
    if (opts.meta !== undefined) body.meta = opts.meta;

    const res = await this._post("/events", body);
    if (res.status === 200) {
      this.emit("event:accepted", opts.sessionId, opts.eventType);
    } else if (res.status === 429) {
      const info = await this.getBudget();
      this.emit("budget:exhausted", info);
      this.emit("event:rejected", opts.sessionId, res.status, "budget_exhausted");
      throw new TskBudgetError("Token budget exhausted", info);
    } else if (res.status === 401) {
      const detail = (res.body as Record<string, unknown>)?.detail;
      const errMsg = (detail as Record<string, unknown>)?.error ?? "invalid_tsk";
      this.emit("event:rejected", opts.sessionId, res.status, String(errMsg));
      throw new TskAuthError("TSK authentication failed", res.status, res.body);
    } else {
      this.emit("event:rejected", opts.sessionId, res.status, "unknown");
      throw new TskError("event failed", res.status, res.body);
    }
  }

  /** Get current budget info for this TSK key. */
  async getBudget(): Promise<BudgetInfo> {
    const res = await this._get(`/budget/${encodeURIComponent(this.key)}`);
    if (res.status !== 200) {
      throw new TskError("getBudget failed", res.status, res.body);
    }
    const d = res.body as Record<string, unknown>;
    // VPS returns: budget (not budget_tokens), used (not tokens_used), exhausted (not is_exhausted)
    const budgetTokens = Number(d.budget ?? d.budget_tokens ?? 0);
    const tokensUsed = Number(d.used ?? d.tokens_used ?? 0);
    return {
      tskKey: String(d.tsk_key ?? this.key),
      budgetTokens,
      tokensUsed,
      remaining: Number(d.remaining ?? Math.max(0, budgetTokens - tokensUsed)),
      pctUsed: Number(d.pct_used ?? 0),
      isExhausted: Boolean(d.exhausted ?? d.is_exhausted ?? false),
      isSystem: Boolean(d.is_system ?? false),
      isActive: Boolean(d.is_active ?? true),
      lastUsedAt: d.last_used_at != null ? Number(d.last_used_at) : null,
    };
  }

  /** Stop budget polling. Called automatically when all sessions end. */
  stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  // ── Private helpers ─────────────────────────────────────────────────────────

  private _startPolling(): void {
    this.pollTimer = setInterval(async () => {
      try {
        const info = await this.getBudget();
        const pct = info.pctUsed / 100;
        if (info.isExhausted && !this.exhaustedEmitted) {
          this.exhaustedEmitted = true;
          this.emit("budget:exhausted", info);
        } else if (pct >= this.warningThreshold && !this.warnedAt80) {
          this.warnedAt80 = true;
          this.emit("budget:warning", info);
        }
      } catch (err) {
        this.emit("error", err instanceof Error ? err : new Error(String(err)));
      }
    }, this.pollIntervalMs);
  }

  private async _post(
    path: string,
    body: Record<string, unknown>,
    attempt = 0
  ): Promise<{ status: number; body: unknown }> {
    const json = JSON.stringify(body);
    return this._request("POST", path, json, attempt);
  }

  private async _get(
    path: string,
    attempt = 0
  ): Promise<{ status: number; body: unknown }> {
    return this._request("GET", path, null, attempt);
  }

  private _request(
    method: string,
    path: string,
    body: string | null,
    attempt: number
  ): Promise<{ status: number; body: unknown }> {
    return new Promise((resolve, reject) => {
      const url = new URL(this.vps + path);
      const isHttps = url.protocol === "https:";
      const lib = isHttps ? https : http;

      const options: https.RequestOptions = {
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + url.search,
        method,
        headers: {
          "Content-Type": "application/json",
          "X-TSK-Key": this.key,
          ...(body !== null ? { "Content-Length": Buffer.byteLength(body) } : {}),
        },
        rejectUnauthorized: this.rejectUnauthorized,
      };

      const req = lib.request(options, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          let parsed: unknown;
          try { parsed = JSON.parse(data); } catch { parsed = data; }
          const status = res.statusCode ?? 0;
          // Retry on 5xx
          if (status >= 500 && attempt < this.maxRetries) {
            const delay = Math.min(1000 * 2 ** attempt, 8000);
            setTimeout(() => {
              this._request(method, path, body, attempt + 1).then(resolve).catch(reject);
            }, delay);
          } else {
            resolve({ status, body: parsed });
          }
        });
      });

      req.on("error", (err) => {
        if (attempt < this.maxRetries) {
          const delay = Math.min(1000 * 2 ** attempt, 8000);
          setTimeout(() => {
            this._request(method, path, body, attempt + 1).then(resolve).catch(reject);
          }, delay);
        } else {
          reject(err);
        }
      });

      if (body !== null) req.write(body);
      req.end();
    });
  }
}

// ── Errors ────────────────────────────────────────────────────────────────────

export class TskError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown
  ) {
    super(`${message} (HTTP ${status})`);
    this.name = "TskError";
  }
}

export class TskAuthError extends TskError {
  constructor(message: string, status: number, body: unknown) {
    super(message, status, body);
    this.name = "TskAuthError";
  }
}

export class TskBudgetError extends Error {
  constructor(message: string, public readonly budget: BudgetInfo) {
    super(message);
    this.name = "TskBudgetError";
  }
}

// ── Convenience factory ───────────────────────────────────────────────────────

/**
 * Create a TskClient from environment variables.
 * Reads SELFCONNECT_TSK_KEY and optionally SELFCONNECT_VPS_URL.
 */
export function fromEnv(overrides?: Partial<TskClientOptions>): TskClient {
  const key = process.env.SELFCONNECT_TSK_KEY;
  if (!key) {
    throw new Error(
      "SELFCONNECT_TSK_KEY environment variable is required. " +
      "Get your key from https://selfconnect.ai/dashboard"
    );
  }
  return new TskClient({
    key,
    vps: process.env.SELFCONNECT_VPS_URL ?? "https://api.selfconnect.ai",
    ...overrides,
  });
}

export default TskClient;
