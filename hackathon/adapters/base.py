# Base MCP Adapter
# Abstract base class for partner MCP server adapters

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Base class for partner MCP server adapters."""

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.name = config.get("name", self.__class__.__name__)

    @abstractmethod
    async def execute(self, method: str, params: dict) -> dict:
        """Execute an MCP method call."""
        pass

    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return list of available tools."""
        pass

    async def health_check(self) -> dict:
        """Check if the adapter is healthy."""
        return {"status": "healthy", "name": self.name}

    async def close(self):
        """Clean up resources."""
        pass
