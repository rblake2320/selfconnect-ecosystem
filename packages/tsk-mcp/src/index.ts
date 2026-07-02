#!/usr/bin/env node
/**
 * @selfconnect/tsk-mcp — MCP server for SelfConnect TSK governance.
 *
 * Claude Desktop config (~/.config/claude/claude_desktop_config.json):
 * {
 *   "mcpServers": {
 *     "selfconnect": {
 *       "command": "selfconnect-tsk-mcp",
 *       "env": { "SELFCONNECT_TSK_KEY": "sc-tsk-YOUR-KEY" }
 *     }
 *   }
 * }
 */

import * as readline from "readline";
import { TOOLS, handleTool } from "./tools";

const TSK_KEY = process.env.SELFCONNECT_TSK_KEY || "";

async function main() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  });

  function send(msg: object) {
    process.stdout.write(JSON.stringify(msg) + "\n");
  }

  rl.on("line", async (line) => {
    let msg: { jsonrpc: string; id?: unknown; method: string; params?: Record<string, unknown> };
    try {
      msg = JSON.parse(line);
    } catch {
      return;
    }

    const { method, id, params = {} } = msg;

    if (method === "initialize") {
      send({
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: { name: "@selfconnect/tsk-mcp", version: "1.0.0" },
        },
      });
    } else if (method === "tools/list") {
      send({ jsonrpc: "2.0", id, result: { tools: TOOLS } });
    } else if (method === "tools/call") {
      const toolName = params.name as string;
      const toolArgs = (params.arguments as Record<string, unknown>) || {};
      const content = await handleTool(toolName, toolArgs, TSK_KEY);
      send({
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: content }],
          isError: false,
        },
      });
    } else if (method === "notifications/initialized") {
      // no response needed
    } else if (id !== undefined) {
      send({
        jsonrpc: "2.0",
        id,
        error: { code: -32601, message: `Method not found: ${method}` },
      });
    }
  });

  rl.on("close", () => process.exit(0));
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err}\n`);
  process.exit(1);
});
