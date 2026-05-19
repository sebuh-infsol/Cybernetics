"""A2A (Agent-to-Agent) and A2P (Agent-to-Protocol) hooks for Google ADK interoperability.

ERC-8004 (8004.org) — Ethereum standard for agent capability discovery and identity,
authored by Google. Provides on-chain resolution contracts for A2A capability negotiation.
"""

from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.a2a")


@dataclass
class A2ACapability:
    """A capability an agent exposes via the A2A protocol."""

    id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    endpoint: Optional[str] = None


@dataclass
class A2PProtocol:
    """An A2P protocol definition that agents can subscribe to or emit."""

    id: str
    name: str
    version: str
    schema_uri: str
    event_types: List[str]


class A2ARegistry:
    """Registry for agent capabilities in the A2A ecosystem."""

    def __init__(self):
        self._capabilities: Dict[str, A2ACapability] = {}
        self._protocols: Dict[str, A2PProtocol] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def register_capability(self, cap: A2ACapability) -> None:
        self._capabilities[cap.id] = cap
        logger.info("a2a_capability_registered", id=cap.id, name=cap.name)

    def list_capabilities(self) -> List[A2ACapability]:
        return list(self._capabilities.values())

    def get_capability(self, cap_id: str) -> Optional[A2ACapability]:
        return self._capabilities.get(cap_id)

    def register_protocol(self, proto: A2PProtocol) -> None:
        self._protocols[proto.id] = proto
        logger.info("a2p_protocol_registered", id=proto.id, name=proto.name)

    def list_protocols(self) -> List[A2PProtocol]:
        return list(self._protocols.values())

    def get_protocol(self, proto_id: str) -> Optional[A2PProtocol]:
        return self._protocols.get(proto_id)

    def add_hook(self, event: str, handler: Callable) -> None:
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    async def run_hooks(self, event: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
        for handler in self._hooks.get(event, []):
            try:
                result = handler(ctx)
                if result is not None:
                    ctx.update(result)
            except Exception as exc:
                logger.error("a2a_hook_failed", event=event, error=str(exc))
        return ctx


# ── ERC-8004 Extension Resolution Contract ──────────────────────────────

class ERC8004Resolver:
    """ERC-8004 Extension Resolution Contract for capability negotiation."""

    def __init__(self, registry: A2ARegistry):
        self.registry = registry

    def resolve(self, requested_caps: List[str]) -> Dict[str, Any]:
        """Given a list of requested capability IDs, return which are available."""
        available = {}
        for cap_id in requested_caps:
            cap = self.registry.get_capability(cap_id)
            available[cap_id] = {
                "available": cap is not None,
                "schema": cap.input_schema if cap else None,
                "endpoint": cap.endpoint if cap else None,
            }
        return available

    def negotiate(self, remote_caps: List[Dict[str, Any]]) -> List[str]:
        """Given remote capabilities, return intersecting IDs."""
        local_ids = {c.id for c in self.registry.list_capabilities()}
        remote_ids = {c["id"] for c in remote_caps}
        return list(local_ids & remote_ids)


# ── Global singletons ─────────────────────────────────────────────────

_a2a_registry = A2ARegistry()
_erc8004_resolver = ERC8004Resolver(_a2a_registry)


def get_a2a_registry() -> A2ARegistry:
    return _a2a_registry


def get_erc8004_resolver() -> ERC8004Resolver:
    return _erc8004_resolver
