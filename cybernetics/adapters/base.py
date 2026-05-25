"""Base adapter interface for all MCP server integrations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from cybernetics.logging.logger import get_logger
from cybernetics.sentinels.pipeline import SentinelPipeline, Auditor, Guard, CostEstimator
from cybernetics.config.settings import settings

logger = get_logger("cybernetics.adapters.base")


@dataclass
class ToolDefinition:
    """MCP tool definition."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    """MCP tool execution result."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPAdapter(ABC):
    """Abstract base for every MCP server adapter."""

    name: str = ""
    description: str = ""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
        self._pipeline = self._setup_pipeline()

    def _setup_pipeline(self) -> SentinelPipeline:
        pipeline = SentinelPipeline()
        enabled = settings.sentinels_enabled
        if "audit" in enabled:
            pipeline.add(Auditor())
        if "guard" in enabled:
            pipeline.add(Guard())
        if "cost" in enabled:
            pipeline.add(CostEstimator())
        return pipeline

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        required: List[str],
        handler: Callable,
    ) -> None:
        self._tools[name] = handler
        self._definitions[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            required=required,
        )

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._definitions.values())

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        handler = self._tools.get(tool_name)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found in adapter '{self.name}'",
            )
        
        tool_call = {"adapter": self.name, "tool": tool_name, "arguments": arguments}
        
        try:
            async def _executor():
                return await handler(**arguments)
            
            result_data = await self._pipeline.execute(tool_call, _executor)
            return ToolResult(success=True, data=result_data)
        except Exception as exc:
            logger.exception("tool_execution_failed", adapter=self.name, tool=tool_name)
            return ToolResult(success=False, error=str(exc))

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Return health status for this adapter."""
        ...

    async def close(self) -> None:
        """Clean up connections. Override if needed."""
        pass
