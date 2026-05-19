# Sentinel: SafetyGuard
# Validates tool calls against safety policies

import logging
from typing import Any

logger = logging.getLogger("cybernetics.sentinels.safety")


class SafetyGuard:
    """Tool call safety validator."""

    name = "safety"

    def __init__(
        self,
        max_tool_calls: int = 10,
        blocklist: list = None,
        require_approval: list = None,
    ):
        self.max_tool_calls = max_tool_calls
        self.blocklist = blocklist or []
        self.require_approval = require_approval or []
        self._call_count = 0

    async def pre_check(self, method: str, params: dict) -> dict:
        """Check if the tool call is safe."""
        # Check against blocklist
        for blocked in self.blocklist:
            if blocked in method:
                logger.warning(f"Safety: blocked method '{method}'")
                return {
                    "blocked": True,
                    "reason": f"Method '{method}' is blocked by safety policy",
                }

        # Check call count
        self._call_count += 1
        if self._call_count > self.max_tool_calls:
            logger.warning(f"Safety: max tool calls exceeded ({self._call_count})")
            return {
                "blocked": True,
                "reason": f"Maximum tool calls ({self.max_tool_calls}) exceeded",
            }

        # Check if approval is required
        for approval_method in self.require_approval:
            if approval_method in method:
                logger.warning(f"Safety: method '{method}' requires approval")
                return {
                    "blocked": True,
                    "reason": f"Method '{method}' requires manual approval",
                }

        return {"blocked": False}

    async def post_check(self, method: str, result: Any, latency: float):
        """Post-call safety review."""
        # Could implement anomaly detection here
        pass
