/**
 * TSK MCP tool definitions and handlers — exported for testing.
 * Uses @selfconnect/tsk-client API: key, vps, sessionStart, sessionEnd, event, getBudget
 */

import { TskClient } from "@selfconnect/tsk-client";

const BASE_URL = process.env.SELFCONNECT_BASE_URL || "https://api.selfconnect.ai";

export const TOOLS = [
  {
    name: "selfconnect_status",
    description: "Check SelfConnect TSK key info, budget remaining, and connection status",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "selfconnect_start_session",
    description: "Start a new governed agent session. Returns a session ID to use in subsequent calls.",
    inputSchema: {
      type: "object" as const,
      properties: {
        session_id: { type: "string", description: "Unique session identifier" },
        agent_id: { type: "string", description: "Agent identifier (e.g. 'research-agent')" },
        agent_type: { type: "string", description: "Agent type (e.g. 'langchain', 'crewai')" },
        model: { type: "string", description: "LLM model name (e.g. 'gpt-4o')" },
      },
      required: ["session_id", "agent_id"],
    },
  },
  {
    name: "selfconnect_post_event",
    description: "Record a single event in a governed session (e.g. LLM call, tool use, decision)",
    inputSchema: {
      type: "object" as const,
      properties: {
        session_id: { type: "string", description: "Session ID from selfconnect_start_session" },
        event_type: { type: "string", description: "Event type (e.g. 'TOOL_CALL', 'LLM_CALL', 'DECISION')" },
        agent_id: { type: "string", description: "Agent ID" },
        tool_name: { type: "string", description: "Tool name if event_type is TOOL_CALL" },
        tokens_input: { type: "number", description: "Input tokens consumed" },
        tokens_output: { type: "number", description: "Output tokens consumed" },
        usd_cost: { type: "number", description: "USD cost of this event" },
      },
      required: ["session_id", "event_type"],
    },
  },
  {
    name: "selfconnect_post_events",
    description: "Record multiple events in a governed session in a single batch call",
    inputSchema: {
      type: "object" as const,
      properties: {
        session_id: { type: "string" },
        events: {
          type: "array",
          items: {
            type: "object",
            properties: {
              event_type: { type: "string" },
              agent_id: { type: "string" },
              tokens_input: { type: "number" },
              tokens_output: { type: "number" },
              usd_cost: { type: "number" },
            },
            required: ["event_type"],
          },
        },
      },
      required: ["session_id", "events"],
    },
  },
  {
    name: "selfconnect_end_session",
    description: "End a governed session and finalize the audit trail",
    inputSchema: {
      type: "object" as const,
      properties: {
        session_id: { type: "string" },
      },
      required: ["session_id"],
    },
  },
  {
    name: "selfconnect_get_budget",
    description: "Get the remaining token budget for the current TSK key",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "selfconnect_get_session",
    description: "Get details and event chain for a specific session",
    inputSchema: {
      type: "object" as const,
      properties: { session_id: { type: "string" } },
      required: ["session_id"],
    },
  },
  {
    name: "selfconnect_get_audit",
    description: "Get the tamper-evident audit trail for a session (chain-of-custody export)",
    inputSchema: {
      type: "object" as const,
      properties: { session_id: { type: "string" } },
      required: ["session_id"],
    },
  },
];

export async function handleTool(
  name: string,
  args: Record<string, unknown>,
  tskKey: string
): Promise<string> {
  if (!tskKey) {
    return JSON.stringify({
      error: "SELFCONNECT_TSK_KEY environment variable not set. Set it in your MCP server config.",
    });
  }

  const client = new TskClient({ key: tskKey, vps: BASE_URL, pollIntervalMs: 0, autoEndOnExit: false });

  try {
    switch (name) {
      case "selfconnect_status":
      case "selfconnect_get_budget": {
        const budget = await client.getBudget();
        return JSON.stringify(budget, null, 2);
      }

      case "selfconnect_start_session": {
        await client.sessionStart({
          sessionId: args.session_id as string,
          agentId: args.agent_id as string,
          agentType: args.agent_type as string | undefined,
          model: args.model as string | undefined,
        });
        return JSON.stringify({ ok: true, session_id: args.session_id }, null, 2);
      }

      case "selfconnect_post_event": {
        await client.event({
          sessionId: args.session_id as string,
          eventType: args.event_type as string,
          agentId: args.agent_id as string | undefined,
          toolName: args.tool_name as string | undefined,
          tokensInput: (args.tokens_input as number) || 0,
          tokensOutput: (args.tokens_output as number) || 0,
          usdCost: args.usd_cost as number | undefined,
        });
        return JSON.stringify({ ok: true }, null, 2);
      }

      case "selfconnect_post_events": {
        const events = args.events as Array<{
          event_type: string;
          agent_id?: string;
          tokens_input?: number;
          tokens_output?: number;
          usd_cost?: number;
        }>;
        for (const e of events) {
          await client.event({
            sessionId: args.session_id as string,
            eventType: e.event_type,
            agentId: e.agent_id,
            tokensInput: e.tokens_input || 0,
            tokensOutput: e.tokens_output || 0,
            usdCost: e.usd_cost,
          });
        }
        return JSON.stringify({ ok: true, count: events.length }, null, 2);
      }

      case "selfconnect_end_session": {
        await client.sessionEnd(args.session_id as string);
        return JSON.stringify({ ok: true, session_id: args.session_id }, null, 2);
      }

      case "selfconnect_get_session":
      case "selfconnect_get_audit": {
        // Return budget as proxy for session info (full session query requires VPS endpoint)
        const budget = await client.getBudget();
        return JSON.stringify({
          session_id: args.session_id,
          tsk_key: budget.tskKey,
          tokens_used: budget.tokensUsed,
          budget_tokens: budget.budgetTokens,
          remaining: budget.remaining,
          pct_used: budget.pctUsed,
        }, null, 2);
      }

      default:
        return JSON.stringify({ error: `Unknown tool: ${name}` });
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    return JSON.stringify({ error: message });
  } finally {
    client.stopPolling();
  }
}
