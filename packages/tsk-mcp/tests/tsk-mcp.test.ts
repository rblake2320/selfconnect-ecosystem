/**
 * Tests for @selfconnect/tsk-mcp MCP server tool definitions and handlers.
 */

import { TOOLS, handleTool } from "../src/tools";

describe("TSK MCP Tool Definitions", () => {
  test("exports 8 tools", () => {
    expect(TOOLS).toHaveLength(8);
  });

  test("all tools have required fields", () => {
    for (const tool of TOOLS) {
      expect(tool).toHaveProperty("name");
      expect(tool).toHaveProperty("description");
      expect(tool).toHaveProperty("inputSchema");
      expect(tool.inputSchema).toHaveProperty("type", "object");
    }
  });

  test("tool names are correct", () => {
    const names = TOOLS.map((t) => t.name);
    expect(names).toContain("selfconnect_status");
    expect(names).toContain("selfconnect_start_session");
    expect(names).toContain("selfconnect_post_event");
    expect(names).toContain("selfconnect_post_events");
    expect(names).toContain("selfconnect_end_session");
    expect(names).toContain("selfconnect_get_budget");
    expect(names).toContain("selfconnect_get_session");
    expect(names).toContain("selfconnect_get_audit");
  });

  test("selfconnect_start_session requires session_id and agent_id", () => {
    const tool = TOOLS.find((t) => t.name === "selfconnect_start_session")!;
    expect(tool.inputSchema.required).toContain("session_id");
    expect(tool.inputSchema.required).toContain("agent_id");
  });

  test("selfconnect_post_event requires session_id and event_type", () => {
    const tool = TOOLS.find((t) => t.name === "selfconnect_post_event")!;
    expect(tool.inputSchema.required).toContain("session_id");
    expect(tool.inputSchema.required).toContain("event_type");
  });
});

describe("TSK MCP Tool Handlers", () => {
  test("returns error when TSK key not set", async () => {
    const result = await handleTool("selfconnect_status", {}, "");
    const parsed = JSON.parse(result);
    expect(parsed.error).toContain("SELFCONNECT_TSK_KEY");
  });

  test("unknown tool returns error", async () => {
    const result = await handleTool("unknown_tool", {}, "sc-tsk-test");
    const parsed = JSON.parse(result);
    expect(parsed.error).toContain("Unknown tool");
  });
});
