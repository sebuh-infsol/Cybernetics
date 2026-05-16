# Dynamic MCP Server Registry Loader
# Loads partner MCP server configurations from YAML/JSON
# Supports hot-reload and runtime server management

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger("cybernetics.registry")


@dataclass
class PartnerServer:
    """Represents a registered partner MCP server."""
    name: str
    config: dict
    enabled: bool = True
    tools: list = field(default_factory=list)
    last_health_check: float = 0.0
    health_status: str = "unknown"

    async def forward(self, request: dict) -> dict:
        """Forward a request to this partner's MCP server."""
        # In production, this would make an HTTP call to the partner's MCP endpoint
        # For the hackathon demo, we simulate the response
        method = request.get("method", "")
        params = request.get("params", {})

        logger.info(f"Forwarding {method} to {self.name}")

        # Simulate MCP server response
        return {
            "server": self.name,
            "method": method,
            "params": params,
            "response": f"Response from {self.name} for {method}",
            "timestamp": time.time(),
        }


class RegistryLoader:
    """Loads and manages MCP server configurations."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self.servers: dict[str, PartnerServer] = {}
        self.total_tools: int = 0
        self.last_updated: float = 0.0
        self._config: dict = {}

    async def load(self, config_path: Optional[Path] = None):
        """Load configurations from YAML file."""
        path = config_path or self.config_path
        if not path or not path.exists():
            logger.warning(f"No config file found at {path}, using defaults")
            self._config = {"partners": {}, "sentinels": {}}
        else:
            with open(path, "r") as f:
                self._config = yaml.safe_load(f) or {"partners": {}, "sentinels": {}}

        # Load partner servers
        partners = self._config.get("partners", {})
        self.servers.clear()
        self.total_tools = 0

        for name, config in partners.items():
            if config.get("enabled", False):
                server = PartnerServer(
                    name=name,
                    config=config,
                    enabled=True,
                    tools=config.get("tools", []),
                )
                self.servers[name] = server
                self.total_tools += len(server.tools)
                logger.info(f"Loaded partner: {name} ({len(server.tools)} tools)")

        self.last_updated = time.time()
        logger.info(f"Registry loaded: {len(self.servers)} servers, {self.total_tools} tools")

    async def reload(self):
        """Reload configurations from disk."""
        await self.load()

    def get_server(self, name: str) -> Optional[PartnerServer]:
        """Get a registered server by name."""
        return self.servers.get(name)

    def get_enabled_servers(self) -> list[PartnerServer]:
        """Get all enabled servers."""
        return [s for s in self.servers.values() if s.enabled]

    def add_server(self, name: str, config: dict):
        """Add a new server to the registry."""
        server = PartnerServer(
            name=name,
            config=config,
            enabled=config.get("enabled", True),
            tools=config.get("tools", []),
        )
        self.servers[name] = server
        self.total_tools += len(server.tools)
        logger.info(f"Added server: {name}")

    def remove_server(self, name: str) -> bool:
        """Remove a server from the registry."""
        if name in self.servers:
            self.total_tools -= len(self.servers[name].tools)
            del self.servers[name]
            logger.info(f"Removed server: {name}")
            return True
        return False

    async def health_check(self):
        """Run health checks on all servers."""
        for name, server in self.servers.items():
            try:
                # In production, this would ping the actual MCP endpoint
                server.health_status = "healthy"
                server.last_health_check = time.time()
            except Exception as e:
                server.health_status = f"error: {e}"
                logger.error(f"Health check failed for {name}: {e}")

    async def cleanup(self):
        """Clean up resources."""
        self.servers.clear()
        logger.info("Registry cleaned up")
