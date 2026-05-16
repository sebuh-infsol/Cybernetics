# Omni-MCP Broker — Request Router
# Routes MCP requests to appropriate partner MCP servers
# with Sentinel middleware layering

import json
import time
import logging
from typing import Any, Optional
from registry.loader import RegistryLoader

logger = logging.getLogger("cybernetics.router")


class Router:
    """Routes MCP requests to registered partner servers."""

    def __init__(self, registry: RegistryLoader, sentinels: list):
        self.registry = registry
        self.sentinels = sentinels

    async def route(self, request: dict) -> dict:
        """Route an MCP request through the sentinel pipeline."""
        start_time = time.time()
        method = request.get("method", "")
        params = request.get("params", {})

        # 1. Pre-sentinel checks
        for sentinel in self.sentinels:
            if hasattr(sentinel, "pre_check"):
                result = await sentinel.pre_check(method, params)
                if result.get("blocked"):
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": f"Blocked by {sentinel.name}: {result.get('reason', 'Policy violation')}",
                        },
                        "id": request.get("id"),
                    }

        # 2. Determine target server
        target_server = self._resolve_server(method, params)
        if not target_server:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"No server registered for method: {method}",
                },
                "id": request.get("id"),
            }

        # 3. Forward to target server
        try:
            result = await target_server.forward(request)
        except Exception as e:
            logger.error(f"Forward error to {target_server.name}: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Server error: {str(e)}",
                },
                "id": request.get("id"),
            }

        # 4. Post-sentinel checks
        latency = time.time() - start_time
        for sentinel in self.sentinels:
            if hasattr(sentinel, "post_check"):
                await sentinel.post_check(method, result, latency)

        # 5. Return response
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request.get("id"),
        }

    def _resolve_server(self, method: str, params: dict) -> Optional[Any]:
        """Resolve which server should handle this request."""
        # Try to extract server name from params
        server_hint = params.get("server") or params.get("partner")

        if server_hint and server_hint in self.registry.servers:
            server = self.registry.servers[server_hint]
            if server.enabled:
                return server

        # Try to match by method name prefix
        for name, server in self.registry.servers.items():
            if not server.enabled:
                continue
            for tool in server.tools:
                if tool["name"] == method:
                    return server

        # Default to first enabled server
        for name, server in self.registry.servers.items():
            if server.enabled:
                return server

        return None
