"""Dynatrace MCP tools — anomaly detection, traces, and DQL queries."""

import httpx
from typing import List, Dict, Any
from src.config import Config

class DynatraceClient:
    def __init__(self):
        self.base_url = Config.DYNATRACE_BASE_URL
        self.token = Config.DYNATRACE_API_TOKEN
        self.headers = {
            "Authorization": f"Api-Token {self.token}",
            "Content-Type": "application/json",
        }

    async def get_active_problems(self) -> List[Dict[str, Any]]:
        """Fetch active problems/alerts from Dynatrace."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v2/problems",
                headers=self.headers,
                params={"from": "now-1h", "problemSelector": "status(OPEN)"},
            )
            resp.raise_for_status()
            return resp.json().get("problems", [])

    async def get_traces_for_service(self, service_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch distributed traces for a given service."""
        query = f"fetch spans | filter service.name == '{service_name}' | limit {limit}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/logs/query",
                headers=self.headers,
                json={"query": query},
            )
            resp.raise_for_status()
            return resp.json().get("results", [])

    async def run_dql(self, query: str) -> Dict[str, Any]:
        """Execute a Dynatrace Query Language (DQL) statement."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v2/logs/query",
                headers=self.headers,
                json={"query": query},
            )
            resp.raise_for_status()
            return resp.json()
