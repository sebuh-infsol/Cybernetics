import httpx
from typing import Dict, Any, List
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit

class CloudflareAdapter(MCPAdapter):
    name = "cloudflare"
    description = "Cloudflare — DNS, workers, pages, zones"
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.headers = {"Authorization": f"Bearer {settings.cloudflare_api_token}"}
        self.account_id = settings.cloudflare_account_id
        self.register_tool("cloudflare_list_zones", "List DNS zones", {}, [], self._list_zones)
        self.register_tool("cloudflare_list_dns", "List DNS records", {"zone_id": {"type": "string"}}, ["zone_id"], self._list_dns)
        self.register_tool("cloudflare_create_dns", "Create a DNS record", {"zone_id": {"type": "string"}, "type": {"type": "string"}, "name": {"type": "string"}, "content": {"type": "string"}, "ttl": {"type": "integer"}}, ["zone_id", "type", "name", "content"], self._create_dns)
        self.register_tool("cloudflare_list_workers", "List Workers scripts", {}, [], self._list_workers)
        self.register_tool("cloudflare_deploy_worker", "Deploy a Worker script", {"script_name": {"type": "string"}, "script": {"type": "string"}}, ["script_name", "script"], self._deploy_worker)
    @circuit("cloudflare", failure_threshold=5, recovery_timeout=60)
    async def _list_zones(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(f"{self.base_url}/zones", headers=self.headers)
            r.raise_for_status()
            return r.json().get("result", [])
    @circuit("cloudflare", failure_threshold=5, recovery_timeout=60)
    async def _list_dns(self, zone_id: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(f"{self.base_url}/zones/{zone_id}/dns_records", headers=self.headers)
            r.raise_for_status()
            return r.json().get("result", [])
    @circuit("cloudflare", failure_threshold=5, recovery_timeout=60)
    async def _create_dns(self, zone_id: str, type: str, name: str, content: str, ttl: int = 120) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(f"{self.base_url}/zones/{zone_id}/dns_records", headers=self.headers, json={"type": type, "name": name, "content": content, "ttl": ttl})
            r.raise_for_status()
            return r.json().get("result", {})
    @circuit("cloudflare", failure_threshold=5, recovery_timeout=60)
    async def _list_workers(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(f"{self.base_url}/accounts/{self.account_id}/workers/scripts", headers=self.headers)
            r.raise_for_status()
            return r.json().get("result", [])
    @circuit("cloudflare", failure_threshold=5, recovery_timeout=60)
    async def _deploy_worker(self, script_name: str, script: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.put(f"{self.base_url}/accounts/{self.account_id}/workers/scripts/{script_name}", headers={**self.headers, "Content-Type": "application/javascript"}, content=script)
            r.raise_for_status()
            return r.json().get("result", {})
    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(f"{self.base_url}/user/tokens/verify", headers=self.headers)
                r.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
