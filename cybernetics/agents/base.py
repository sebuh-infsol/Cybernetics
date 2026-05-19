"""Base agent template interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from cybernetics.registry.manager import Registry
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents")


class AgentTemplate(ABC):
    name: str = ""
    description: str = ""
    adapters: list[str] = []

    def __init__(self, registry: Registry):
        self.registry = registry

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        ...
