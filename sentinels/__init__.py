"""
Sentinel Layer
Middleware templates that wrap tool calls for governance.
"""
from typing import Callable, Any

class Sentinel:
    """Base class for Sentinel templates."""
    def __init__(self, name: str):
        self.name = name

    async def before(self, tool_call: dict) -> dict:
        """Run before tool execution."""
        return tool_call

    async def after(self, result: Any) -> Any:
        """Run after tool execution."""
        return result

class Auditor(Sentinel):
    """Logs all tool calls and results."""
    async def before(self, tool_call: dict) -> dict:
        print(f"[AUDIT] Before: {tool_call}")
        return tool_call

    async def after(self, result: Any) -> Any:
        print(f"[AUDIT] After: {result}")
        return result

class SafetyGuard(Sentinel):
    """Validates inputs/outputs against policy."""
    async def before(self, tool_call: dict) -> dict:
        # Add validation logic here
        return tool_call

class SentinelPipeline:
    """Chain of Sentinels."""
    def __init__(self):
        self.sentinels = []

    def add(self, sentinel: Sentinel):
        self.sentinels.append(sentinel)

    async def execute(self, tool_call: dict, executor: Callable):
        """Run tool call through the pipeline."""
        for s in self.sentinels:
            tool_call = await s.before(tool_call)
        
        result = await executor(tool_call)
        
        for s in self.sentinels:
            result = await s.after(result)
        
        return result
