"""Sentinel middleware pipeline."""

from typing import Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.sentinels")


class Sentinel:
    async def before(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        return tool_call
    async def after(self, result: Any) -> Any:
        return result


class Auditor(Sentinel):
    async def before(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("sentinel_audit_before", tool=tool_call.get("tool"), adapter=tool_call.get("adapter"))
        return tool_call
    async def after(self, result: Any) -> Any:
        logger.info("sentinel_audit_after", success=getattr(result, "success", True))
        return result


class Guard(Sentinel):
    BLOCKED = {"password", "secret", "token", "key", "private_key"}
    async def before(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        args = tool_call.get("arguments", {})
        for k in args:
            if any(b in k.lower() for b in self.BLOCKED):
                logger.warning("sentinel_guard_blocked", key=k)
                raise ValueError(f"Guard blocked sensitive key: {k}")
        return tool_call


class CostEstimator(Sentinel):
    async def before(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("sentinel_cost_estimate", tool=tool_call.get("tool"), adapter=tool_call.get("adapter"))
        return tool_call


class SentinelPipeline:
    def __init__(self, sentinels: List[Sentinel] = None):
        self.sentinels = sentinels or []
    def add(self, s: Sentinel) -> None:
        self.sentinels.append(s)
    async def execute(self, tool_call: Dict[str, Any], executor: Callable[[], Awaitable[Any]]) -> Any:
        tc = tool_call
        for s in self.sentinels:
            tc = await s.before(tc)
        result = await executor()
        for s in self.sentinels:
            result = await s.after(result)
        return result
