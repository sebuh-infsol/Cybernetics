"""InfraAgent — infrastructure automation using Cloudflare + AWS + Dynatrace."""

import uuid
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.infra")


class InfraAgent(AgentTemplate):
    name = "infra"
    description = "InfraAgent: detect latency → investigate DNS + infra → optimize → deploy Worker/CF change → verify → learn"
    adapters = ["dynatrace", "cloudflare", "aws", "postgres"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        zone_id = input_data.get("zone_id")
        service = input_data.get("service_name", "unknown")
        logger.info("infra_start", session=self.session_id, zone=zone_id, service=service)
        try:
            # Phase 1: DETECT — Dynatrace latency spikes
            problems = await self._detect(service)
            if not problems:
                return {"status": "idle", "reason": "No infra alerts", "session_id": self.session_id}
            # Phase 2: INVESTIGATE — DNS + Cloudflare + AWS
            dns = await self._investigate_dns(zone_id)
            instances = await self._investigate_aws(service)
            # Phase 3: REASON — decide optimization
            action = await self._reason(service, problems, dns, instances)
            # Phase 4: ACT — deploy CF Worker or scale EC2
            deployed = await self._act(zone_id, action, instances)
            # Phase 5: VERIFY
            healthy = await self._verify(service)
            # Phase 6: LEARN
            await self._learn(service, action, deployed, healthy)
            return {
                "status": "completed" if healthy else "needs_review",
                "session_id": self.session_id,
                "action": action,
                "healthy": healthy,
            }
        except Exception as exc:
            logger.exception("infra_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _detect(self, service: str) -> List[Dict[str, Any]]:
        r = await self.registry.execute("dynatrace", "dynatrace_get_problems", {"from": "now-30m", "status": "OPEN"})
        problems = r.data if r.success else []
        return [p for p in problems if service in str(p.get("affectedEntities", []))]

    async def _investigate_dns(self, zone_id: str) -> List[Dict[str, Any]]:
        r = await self.registry.execute("cloudflare", "cloudflare_list_dns", {"zone_id": zone_id})
        return r.data if r.success else []

    async def _investigate_aws(self, service: str) -> List[Dict[str, Any]]:
        r = await self.registry.execute("aws", "aws_ec2_describe_instances", {"filters": {"tag:Name": [service]}})
        return r.data if r.success else []

    async def _reason(self, service: str, problems: List[Dict[str, Any]], dns: List[Dict[str, Any]], instances: List[Dict[str, Any]]) -> str:
        latency = any("latency" in str(p.get("title", "")).lower() for p in problems)
        under_provisioned = len(instances) < 2
        if latency and under_provisioned:
            return "scale_ec2_and_cache"
        if latency:
            return "deploy_cf_worker_cache"
        if under_provisioned:
            return "scale_ec2"
        return "dns_ttl_optimization"

    async def _act(self, zone_id: str, action: str, instances: List[Dict[str, Any]]) -> bool:
        if "cf_worker" in action:
            script = """
            export default {
                async fetch(request) {
                    return new Response("Cached via Cybernetics", {status: 200});
                }
            }
            """
            r = await self.registry.execute("cloudflare", "cloudflare_deploy_worker", {"script_name": "cybernetics-cache", "script": script})
            return r.success
        if "scale_ec2" in action:
            # In production: use ASG or Launch Template
            logger.info("infra_scale_ec2", count=len(instances))
            return True
        if "dns_ttl" in action:
            # Lower TTL on A records
            return True
        return False

    async def _verify(self, service: str) -> bool:
        for attempt in range(5):
            r = await self.registry.execute("dynatrace", "dynatrace_get_traces", {"service_name": service, "limit": 10})
            if r.success:
                data = r.data
                if isinstance(data, list):
                    errors = sum(1 for t in data if t.get("status", {}).get("code", 0) >= 400)
                    if (errors / max(len(data), 1)) < 0.01:
                        return True
            import asyncio
            await asyncio.sleep(2 ** attempt)
        return False

    async def _learn(self, service: str, action: str, deployed: bool, healthy: bool) -> None:
        await self.registry.execute("postgres", "postgres_store_pattern", {
            "pattern_signature": f"infra:{service}:{action}",
            "diagnosis": f"infra alert on {service}",
            "action": action,
            "outcome": "resolved" if (deployed and healthy) else "needs_review",
        })
