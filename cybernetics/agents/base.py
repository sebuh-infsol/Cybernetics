"""Base agent template interface with A2A, A2P & ERC-8004 hooks."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from cybernetics.registry.manager import Registry
from cybernetics.logging.logger import get_logger
from cybernetics.a2a.hooks import (
    A2ACapability,
    A2PProtocol,
    get_a2a_registry,
    get_erc8004_resolver,
)

logger = get_logger("cybernetics.agents")


class AgentTemplate(ABC):
    name: str = ""
    description: str = ""
    adapters: list[str] = []

    def __init__(self, registry: Registry):
        self.registry = registry
        self.a2a_registry = get_a2a_registry()
        self.erc8004 = get_erc8004_resolver()
        self._register_default_capability()

    def _register_default_capability(self) -> None:
        """Auto-register this agent as an A2A capability."""
        if not self.name:
            return
        cap = A2ACapability(
            id=self.name,
            name=self.name,
            description=self.description or f"{self.name} agent",
            input_schema={"input_data": {"type": "object"}},
            output_schema={"status": {"type": "string"}, "session_id": {"type": "string"}},
        )
        self.a2a_registry.register_capability(cap)
        logger.info("a2a_capability_auto_registered", agent=self.name)

    # ── A2A helpers ───────────────────────────────────────────────────────

    def register_capability(self, cap: A2ACapability) -> None:
        self.a2a_registry.register_capability(cap)

    def register_protocol(self, proto: A2PProtocol) -> None:
        self.a2a_registry.register_protocol(proto)

    def add_hook(self, event: str, handler) -> None:
        self.a2a_registry.add_hook(event, handler)

    async def run_hooks(self, event: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return await self.a2a_registry.run_hooks(event, ctx)

    def resolve_capabilities(self, requested: list[str]) -> Dict[str, Any]:
        """ERC-8004: check which capabilities are available."""
        return self.erc8004.resolve(requested)

    def negotiate_capabilities(self, remote_caps: list[Dict[str, Any]]) -> list[str]:
        """ERC-8004: intersect local + remote capabilities."""
        return self.erc8004.negotiate(remote_caps)

    # ── A2P event emission ──────────────────────────────────────────────

    async def emit(self, protocol_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Emit an A2P event to all registered hooks for that protocol."""
        ctx = {
            "protocol_id": protocol_id,
            "event_type": event_type,
            "agent": self.name,
            "payload": payload,
        }
        await self.run_hooks(f"a2p:{protocol_id}:{event_type}", ctx)
        logger.info("a2p_event_emitted", protocol=protocol_id, event=event_type, agent=self.name)

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        ...
