"""Fivetran adapter."""

import httpx
from typing import Dict, Any, List
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.fivetran")


class FivetranAdapter(MCPAdapter):
    name = "fivetran"
    description = "Fivetran — data pipeline orchestration"

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.fivetran.com/v1"
        self.auth = (settings.fivetran_api_key, settings.fivetran_api_secret)
        self.register_tool(
            "fivetran_list_connectors",
            "List connectors in a group",
            {"group_id": {"type": "string"}},
            ["group_id"],
            self._list_connectors,
        )
        self.register_tool(
            "fivetran_get_connector_status",
            "Get connector sync status",
            {"connector_id": {"type": "string"}},
            ["connector_id"],
            self._get_status,
        )
        self.register_tool(
            "fivetran_sync_connector",
            "Force a manual sync",
            {"connector_id": {"type": "string"}},
            ["connector_id"],
            self._sync,
        )
        self.register_tool(
            "fivetran_create_log_pipeline",
            "Create a log pipeline connector",
            {"service_name": {"type": "string"}, "destination_id": {"type": "string"}},
            ["service_name", "destination_id"],
            self._create_pipeline,
        )

    @circuit("fivetran", failure_threshold=5, recovery_timeout=60)
    async def _list_connectors(self, group_id: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/groups/{group_id}/connectors", auth=self.auth)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("items", [])

    @circuit("fivetran", failure_threshold=5, recovery_timeout=60)
    async def _get_status(self, connector_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/connectors/{connector_id}", auth=self.auth)
            resp.raise_for_status()
            return resp.json().get("data", {})

    @circuit("fivetran", failure_threshold=5, recovery_timeout=60)
    async def _sync(self, connector_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/connectors/{connector_id}/force", auth=self.auth)
            resp.raise_for_status()
            return resp.json()

    @circuit("fivetran", failure_threshold=5, recovery_timeout=60)
    async def _create_pipeline(self, service_name: str, destination_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/connectors", auth=self.auth,
                json={"service": service_name, "group_id": destination_id, "config": {}, "paused": False},
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/groups", auth=self.auth)
                resp.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
