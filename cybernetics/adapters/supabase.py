"""Supabase adapter — database, auth, storage, edge functions."""

import httpx
from typing import Dict, Any, List, Optional
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.supabase")


class SupabaseAdapter(MCPAdapter):
    name = "supabase"
    description = "Supabase — database, auth, storage, edge functions"

    def __init__(self):
        super().__init__()
        self.base_url = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
        }
        self.register_tool("supabase_select", "Select rows from a table", {"table": {"type": "string"}, "columns": {"type": "string"}, "filters": {"type": "object"}, "limit": {"type": "integer"}}, ["table"], self._select)
        self.register_tool("supabase_insert", "Insert rows into a table", {"table": {"type": "string"}, "rows": {"type": "array"}}, ["table", "rows"], self._insert)
        self.register_tool("supabase_update", "Update rows in a table", {"table": {"type": "string"}, "data": {"type": "object"}, "filters": {"type": "object"}}, ["table", "data"], self._update)
        self.register_tool("supabase_delete", "Delete rows from a table", {"table": {"type": "string"}, "filters": {"type": "object"}}, ["table", "filters"], self._delete)
        self.register_tool("supabase_rpc", "Call a stored procedure / edge function", {"function_name": {"type": "string"}, "params": {"type": "object"}}, ["function_name"], self._rpc)

    def _build_query(self, filters: Optional[Dict[str, Any]] = None) -> str:
        parts = []
        if filters:
            for col, val in filters.items():
                if isinstance(val, dict):
                    for op, v in val.items():
                        parts.append(f"{col}={op}.{v}")
                else:
                    parts.append(f"{col}=eq.{val}")
        return "&".join(parts)

    @circuit("supabase", failure_threshold=5, recovery_timeout=60)
    async def _select(self, table: str, columns: str = "*", filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/v1/{table}"
        params = {"select": columns, "limit": limit}
        if filters:
            params.update({k: f"eq.{v}" for k, v in filters.items()})
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    @circuit("supabase", failure_threshold=5, recovery_timeout=60)
    async def _insert(self, table: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/rest/v1/{table}", headers={**self.headers, "Prefer": "return=representation"}, json=rows)
            resp.raise_for_status()
            return resp.json()

    @circuit("supabase", failure_threshold=5, recovery_timeout=60)
    async def _update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.patch(f"{self.base_url}/rest/v1/{table}", headers={**self.headers, "Prefer": "return=representation"}, params=params, json=data)
            resp.raise_for_status()
            return resp.json()

    @circuit("supabase", failure_threshold=5, recovery_timeout=60)
    async def _delete(self, table: str, filters: Dict[str, Any]) -> None:
        params = {k: f"eq.{v}" for k, v in filters.items()}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.delete(f"{self.base_url}/rest/v1/{table}", headers=self.headers, params=params)
            resp.raise_for_status()

    @circuit("supabase", failure_threshold=5, recovery_timeout=60)
    async def _rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/rest/v1/rpc/{function_name}", headers=self.headers, json=params or {})
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/rest/v1/", headers=self.headers)
                resp.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
