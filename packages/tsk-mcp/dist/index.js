#!/usr/bin/env node
"use strict";
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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const readline = __importStar(require("readline"));
const tools_1 = require("./tools");
const TSK_KEY = process.env.SELFCONNECT_TSK_KEY || "";
async function main() {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
        terminal: false,
    });
    function send(msg) {
        process.stdout.write(JSON.stringify(msg) + "\n");
    }
    rl.on("line", async (line) => {
        let msg;
        try {
            msg = JSON.parse(line);
        }
        catch {
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
        }
        else if (method === "tools/list") {
            send({ jsonrpc: "2.0", id, result: { tools: tools_1.TOOLS } });
        }
        else if (method === "tools/call") {
            const toolName = params.name;
            const toolArgs = params.arguments || {};
            const content = await (0, tools_1.handleTool)(toolName, toolArgs, TSK_KEY);
            send({
                jsonrpc: "2.0",
                id,
                result: {
                    content: [{ type: "text", text: content }],
                    isError: false,
                },
            });
        }
        else if (method === "notifications/initialized") {
            // no response needed
        }
        else if (id !== undefined) {
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
//# sourceMappingURL=index.js.map