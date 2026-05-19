"""Health and readiness probes."""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import asyncio
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.health")


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    detail: str
    latency_ms: float = 0.0


class HealthRegistry:
    """Registry of health check probes."""

    def __init__(self):
        self._probes: List[callable] = []

    def register(self, probe: callable) -> None:
        self._probes.append(probe)

    async def run_all(self) -> Dict[str, Any]:
        results: List[HealthCheck] = []
        for probe in self._probes:
            start = asyncio.get_event_loop().time()
            try:
                check = await probe()
            except Exception as exc:
                check = HealthCheck(
                    name=probe.__name__,
                    status=HealthStatus.UNHEALTHY,
                    detail=str(exc),
                )
            check.latency_ms = round((asyncio.get_event_loop().time() - start) * 1000, 2)
            results.append(check)

        overall = HealthStatus.HEALTHY
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            overall = HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.DEGRADED for r in results):
            overall = HealthStatus.DEGRADED

        return {
            "status": overall.value,
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "detail": r.detail,
                    "latency_ms": r.latency_ms,
                }
                for r in results
            ],
        }


registry = HealthRegistry()
