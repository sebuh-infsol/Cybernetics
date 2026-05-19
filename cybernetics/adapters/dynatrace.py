"""Dynatrace adapter — async, circuit breaker, DQL sanitization."""

import re
import httpx
from typing import Dict, Any, List
from cybernetics.adapters.base import MCPAdapter, ToolResult
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.dynatrace")

_DQL_SAFE = re.compile(r"^[a-zA-Z0-9_\.\-\s=><!\(\)\|'\"]+$")


def _sanitize_dql(query: str) -> str:
    if not _DQL_SAFE.match(query):
        raise ValueError("DQL query contains unsafe characters")
    return query


class DynatraceAdapter(MCPAdapter):
    name = "dynatrace"
    description = "Dynatrace observability — problems, traces, DQL"

    def __init__(self):
        super().__init__()
        self.base_url = settings.dynatrace_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Api-Token {settings.dynatrace_api_token}",
            "Content-Type": "application/json",
        }
        self.register_tool(
            "dynatrace_get_problems",
            "Fetch active problems from Dynatrace",
            {"from": {"type": "string"}, "status": {"type": "string"}},
            ["from"],
            self._get_problems,
        )
        self.register_tool(
            "dynatrace_get_traces",
            "Fetch distributed traces for a service",
            {"service_name": {"type": "string"}, "limit": {"type": "integer"}},
            ["service_name"],
            self._get_traces,
        )
        self.register_tool(
            "dynatrace_run_dql",
            "Execute a Dynatrace Query Language statement",
            {"query": {"type": "string"}},
            ["query"],
            self._run_dql,
        )

    @circuit("dynatrace", failure_threshold=5, recovery_timeout=60)
    async def _get_problems(self, from_: str = "now-1h", status: str = "OPEN") -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/v2/problems",
                headers=self.headers,
                params={"from": from_, "problemSelector": f"status({status})"},
            )
            resp.raise_for_status()
            return resp.json().get("problems", [])

    @circuit("dynatrace", failure_threshold=5, recovery_timeout=60)
    async def _get_traces(self, service_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "", service_name)
        query = f"fetch spans | filter service.name == '{safe_name}' | limit {limit}"
        return await self._run_dql(query)

    @circuit("dynatrace", failure_threshold=5, recovery_timeout=60)
    async def _run_dql(self, query: str) -> Dict[str, Any]:
        _sanitize_dql(query)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/logs/query",
                headers=self.headers,
                json={"query": query},
            )
            resp.raise_for_status()
            return resp.json().get("results", {})

    async def health(self) -> Dict[str, Any]:
        try:
            problems = await self._get_problems(from_="now-5m")
            return {"status": "healthy", "problems_count": len(problems)}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
