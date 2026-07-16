"""
SelfConnect MCP Server — exposes SelfConnect API client tools via MCP.

This server lets MCP-compatible AI agents (Claude, Cursor, etc.) directly:
  - Check and monitor token budgets
  - Request session start and end operations
  - Post caller-reported events
  - Retrieve server-reported event hash chains
  - Inspect and manage TSK keys

Usage (stdio transport — works with Claude Desktop, Cursor, etc.):
    selfconnect-mcp

Usage (SSE transport — for remote agents):
    selfconnect-mcp --transport sse --port 8765

Configuration (env vars or ~/.selfconnect/config.json):
    SELFCONNECT_TSK_KEY=sc-tsk-YOUR-KEY
    SELFCONNECT_BASE_URL=https://api.selfconnect.ai  (optional)
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

# MCP SDK — installed via mcp[cli] extra
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        TextContent,
        Tool,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from selfconnect.cli.config import get_base_url, get_tsk_key


# ─── Tool definitions ─────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "selfconnect_status",
        "description": (
            "Get the current status of a SelfConnect TSK key: budget, usage, "
            "remaining tokens, and whether the key is active."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tsk_key": {
                    "type": "string",
                    "description": "TSK key to check (uses configured key if omitted)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "selfconnect_start_session",
        "description": (
            "Request a new server session for an AI agent. Returns a session_id "
            "that must be used for all subsequent events in this session."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Identifier for the agent (e.g. 'research-agent-v2')",
                },
                "meta": {
                    "type": "object",
                    "description": "Optional metadata to attach to the session",
                },
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "selfconnect_end_session",
        "description": "Request that the configured server end an active session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID returned by selfconnect_start_session",
                },
                "summary": {
                    "type": "string",
                    "description": "Human-readable summary of what the agent accomplished",
                },
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "selfconnect_post_event",
        "description": (
            "Post a caller-reported agent event to the configured server. "
            "The server may place accepted events into a retained hash chain. "
            "A server-side budget rejection is returned as an error."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Active session ID"},
                "event_type": {
                    "type": "string",
                    "description": "Event type: llm_call, tool_use, policy_check, decision, etc.",
                },
                "tokens_input": {"type": "integer", "description": "Input tokens consumed", "default": 0},
                "tokens_output": {"type": "integer", "description": "Output tokens generated", "default": 0},
                "decision": {"type": "string", "description": "Decision made (approved/denied/etc.)"},
                "meta": {"type": "object", "description": "Additional metadata"},
            },
            "required": ["session_id", "event_type"],
        },
    },
    {
        "name": "selfconnect_get_audit",
        "description": (
            "Retrieve the configured server's workflow and retained event hash-chain "
            "data for a session. This does not prove completeness or authorization."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to retrieve workflow data for",
                }
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "selfconnect_recent_events",
        "description": "Get recent events posted under this TSK key across all sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return (default: 20)",
                    "default": 20,
                }
            },
            "required": [],
        },
    },
    {
        "name": "selfconnect_key_info",
        "description": "Get detailed metadata about a TSK key: creation time, revocation status, user ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tsk_key": {
                    "type": "string",
                    "description": "TSK key to inspect (uses configured key if omitted)",
                }
            },
            "required": [],
        },
    },
]


# ─── Tool handler ─────────────────────────────────────────────────────────────

def _get_client(tsk_key: Optional[str] = None):
    from selfconnect import TskClient
    key = tsk_key or get_tsk_key()
    if not key:
        raise ValueError(
            "No TSK key configured. Set SELFCONNECT_TSK_KEY env var or run: selfconnect login"
        )
    return TskClient(tsk_key=key, base_url=get_base_url())


def _fmt(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


async def handle_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Dispatch a tool call and return a JSON string result."""
    try:
        client = _get_client(arguments.get("tsk_key"))

        if name == "selfconnect_status":
            budget = client.get_budget()
            return _fmt(budget)

        elif name == "selfconnect_start_session":
            session_id = client.start_session(
                agent_id=arguments["agent_id"],
                meta=arguments.get("meta"),
            )
            return _fmt({"session_id": session_id, "agent_id": arguments["agent_id"]})

        elif name == "selfconnect_end_session":
            result = client.end_session(
                session_id=arguments["session_id"],
                summary=arguments.get("summary"),
            )
            return _fmt(result)

        elif name == "selfconnect_post_event":
            result = client.post_event(
                session_id=arguments["session_id"],
                event_type=arguments["event_type"],
                tokens_input=int(arguments.get("tokens_input", 0)),
                tokens_output=int(arguments.get("tokens_output", 0)),
                decision=arguments.get("decision"),
                meta=arguments.get("meta"),
            )
            return _fmt(result)

        elif name == "selfconnect_get_audit":
            workflow = client.get_session_workflow(arguments["session_id"])
            return _fmt(workflow)

        elif name == "selfconnect_recent_events":
            events = client.get_tsk_events(limit=int(arguments.get("limit", 20)))
            return _fmt(events)

        elif name == "selfconnect_key_info":
            info = client.get_tsk_info()
            return _fmt(info)

        else:
            return _fmt({"error": f"Unknown tool: {name}"})

    except Exception as exc:
        return _fmt({"error": str(exc), "tool": name})


# ─── Server entry point ───────────────────────────────────────────────────────

def create_server() -> "Server":
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install selfconnect[mcp]"
        )

    server = Server("selfconnect")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]):
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    return server


async def run_stdio():
    """Run the MCP server over stdio (for Claude Desktop, Cursor, etc.)."""
    if not MCP_AVAILABLE:
        print(
            "ERROR: MCP SDK not installed. Install with: pip install selfconnect[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Entry point for selfconnect-mcp command."""
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(
        prog="selfconnect-mcp",
        description="SelfConnect API client tools for MCP-compatible agents",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for SSE transport (default: 8765)",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(run_stdio())
    else:
        # SSE transport for remote agents
        try:
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Route
            import uvicorn

            server = create_server()
            sse = SseServerTransport("/messages")

            async def handle_sse(request):
                async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                    await server.run(streams[0], streams[1], server.create_initialization_options())

            app = Starlette(routes=[Route("/sse", endpoint=handle_sse)])
            print(f"SelfConnect MCP server running on http://0.0.0.0:{args.port}/sse")
            uvicorn.run(app, host="0.0.0.0", port=args.port)
        except ImportError as e:
            print(f"SSE transport requires extra deps: pip install selfconnect[mcp-sse]\n{e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
