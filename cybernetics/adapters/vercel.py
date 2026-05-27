"""Vercel adapter — deployments, projects, domains."""

import httpx
from typing import Dict, Any, List
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.vercel")


class VercelAdapter(MCPAdapter):
    name = "vercel"
    description = "Vercel — deployments, projects, domains, env vars"

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.vercel.com/v9"
        self.headers = {"Authorization": f"Bearer {settings.vercel_token}"}
        self.register_tool("vercel_list_projects", "List Vercel projects", {"limit": {"type": "integer"}}, [], self._list_projects)
        self.register_tool("vercel_get_deployment", "Get deployment details", {"deployment_id": {"type": "string"}}, ["deployment_id"], self._get_deployment)
        self.register_tool("vercel_list_deployments", "List deployments for a project", {"project_id": {"type": "string"}, "limit": {"type": "integer"}}, ["project_id"], self._list_deployments)
        self.register_tool("vercel_add_env_var", "Add an environment variable", {"project_id": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"}, "target": {"type": "array"}}, ["project_id", "key", "value"], self._add_env)

    @circuit("vercel", failure_threshold=5, recovery_timeout=60)
    async def _list_projects(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/projects", headers=self.headers, params={"limit": limit})
            resp.raise_for_status()
            return resp.json().get("projects", [])

    @circuit("vercel", failure_threshold=5, recovery_timeout=60)
    async def _get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/deployments/{deployment_id}", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    @circuit("vercel", failure_threshold=5, recovery_timeout=60)
    async def _list_deployments(self, project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/projects/{project_id}/deployments", headers=self.headers, params={"limit": limit})
            resp.raise_for_status()
            return resp.json().get("deployments", [])

    @circuit("vercel", failure_threshold=5, recovery_timeout=60)
    async def _add_env(self, project_id: str, key: str, value: str, target: List[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/projects/{project_id}/env",
                headers=self.headers,
                json={"key": key, "value": value, "target": target or ["production", "preview"]},
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/user", headers=self.headers)
                resp.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
