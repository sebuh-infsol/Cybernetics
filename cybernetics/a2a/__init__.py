"""A2A (Agent-to-Agent) and A2P (Agent-to-Protocol) interoperability package."""

from cybernetics.a2a.hooks import (
    A2ACapability,
    A2PProtocol,
    A2ARegistry,
    ERC8004Resolver,
    get_a2a_registry,
    get_erc8004_resolver,
)

__all__ = [
    "A2ACapability",
    "A2PProtocol",
    "A2ARegistry",
    "ERC8004Resolver",
    "get_a2a_registry",
    "get_erc8004_resolver",
]
