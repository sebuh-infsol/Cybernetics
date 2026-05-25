"""
MCP Registry
Manages the dynamic loading and routing of MCP servers.
"""
import yaml
from typing import Dict, Any

class Registry:
    def __init__(self):
        self.servers: Dict[str, Any] = {}

    async def load_config(self, path: str):
        """Load MCP server configs from YAML."""
        with open(path) as f:
            config = yaml.safe_load(f)
        
        for name, settings in config.get('servers', {}).items():
            await self.register_server(name, settings)

    async def register_server(self, name: str, settings: dict):
        """Register a new MCP server dynamically."""
        # Logic to connect to MCP endpoint (SSE/HTTP)
        self.servers[name] = settings
        print(f"Registered MCP Server: {name}")

    def get_server(self, name: str):
        return self.servers.get(name)

    def list_servers(self):
        return list(self.servers.keys())
