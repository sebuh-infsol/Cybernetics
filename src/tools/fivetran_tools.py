"""Fivetran MCP tools — data pipeline creation and status monitoring."""

import base64
import httpx
from typing import Dict, Any, List
from src.config import Config

class FivetranClient:
    def __init__(self):
        self.base_url = "https://api.fivetran.com/v1"
        self.auth = (
            Config.FIVETRAN_API_KEY,
            Config.FIVETRAN_API_SECRET,
        )

    async def list_connectors(self, group_id: str) -> List[Dict[str, Any]]:
        """List all connectors in a Fivetran group."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/groups/{group_id}/connectors",
                auth=self.auth,
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("items", [])

    async def get_connector_status(self, connector_id: str) -> Dict[str, Any]:
        """Get sync status for a specific connector."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/connectors/{connector_id}",
                auth=self.auth,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def sync_connector(self, connector_id: str) -> Dict[str, Any]:
        """Force a manual sync for a connector."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/connectors/{connector_id}/force",
                auth=self.auth,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_log_pipeline(self, service_name: str, destination_id: str) -> Dict[str, Any]:
        """Create a new connector to pipeline a service's logs into BigQuery."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/connectors",
                auth=self.auth,
                json={
                    "service": service_name,
                    "group_id": destination_id,
                    "config": {},
                    "paused": False,
                },
            )
            resp.raise_for_status()
            return resp.json().get("data", {})
