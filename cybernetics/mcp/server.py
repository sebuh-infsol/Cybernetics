"""MCP stdio server — JSON-RPC 2.0 over stdin/stdout per MCP spec."""

import json
import sys
from typing import Any, Dict, List, Optional

from cybernetics.registry.manager import Registry
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.mcp")


class MCPServer:
    """Model Context Protocol server over stdio transport."""

    def __init__(self, registry: Registry):
        self.registry = registry
        self._initialized = False

    def _send(self, msg: Dict[str, Any]) -> None:
        raw = json.dumps(msg, separators=(",", ":"))
        sys.stdout.write(raw + "\n")
        sys.stdout.flush()

    def _reply(self, req_id: Any, result: Any) -> None:
        self._send({"jsonrpc": "2.0", "id": req_id, "result": result})

    def _error(self, req_id: Any, code: int, message: str) -> None:
        self._send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})

    async def _handle(self, req: Dict[str, Any]) -> None:
        method = req.get("method")
        req_id = req.get("id")
        params = req.get("params", {})

        if method == "initialize":
            self._initialized = True
            self._reply(req_id, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "cybernetics", "version": "2026.5.2"},
                "capabilities": {"tools": {}},
            })
            return

        if not self._initialized:
            self._error(req_id, -32000, "Server not initialized")
            return

        if method == "initialized":
            # Client notification, no response needed
            return

        if method == "tools/list":
            tools = self.registry.all_tools()
            mcp_tools = []
            for t in tools:
                mcp_tools.append({
                    "name": f"{t['adapter']}_{t['tool']}",
                    "description": t.get("description", ""),
                    "inputSchema": {
                        "type": "object",
                        "properties": t.get("schema", {}),
                        "required": t.get("required", []),
                    },
                })
            self._reply(req_id, {"tools": mcp_tools})
            return

        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            # Parse adapter_tool name format
            if "_" not in name:
                self._error(req_id, -32602, "Invalid tool name format (expected adapter_tool)")
                return
            adapter_name, tool_name = name.split("_", 1)
            try:
                result = await self.registry.execute(adapter_name, tool_name, arguments)
                content = [{"type": "text", "text": json.dumps(result)}]
                self._reply(req_id, {"content": content, "isError": not result.get("success", True)})
            except Exception as exc:
                logger.error("mcp_tool_call_failed", adapter=adapter_name, tool=tool_name, error=str(exc))
                content = [{"type": "text", "text": str(exc)}]
                self._reply(req_id, {"content": content, "isError": True})
            return

        self._error(req_id, -32601, f"Method not found: {method}")

    async def run(self) -> None:
        logger.info("mcp_server_started", transport="stdio")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                self._send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
                continue
            await self._handle(req)


async def main() -> None:
    """Entry point for `python -m cybernetics.mcp.server`."""
    reg = Registry()
    reg.load([
        "dynatrace", "elastic", "postgres", "gitlab",
        "arize", "fivetran", "github", "stripe", "aws",
        "vercel", "supabase", "cloudflare", "browser",
    ])
    server = MCPServer(reg)
    await server.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
