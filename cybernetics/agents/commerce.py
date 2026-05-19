"""CommerceAgent — e-commerce ops using Stripe, Supabase, and AWS."""

import uuid
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.commerce")


class CommerceAgent(AgentTemplate):
    name = "commerce"
    description = "CommerceAgent: catalog → pricing → checkout → fulfillment → reconcile"
    adapters = ["stripe", "supabase", "aws", "slack"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        order_id = input_data.get("order_id", "")
        customer_id = input_data.get("customer_id", "")
        logger.info("commerce_start", session=self.session_id, order=order_id)
        try:
            # Phase 1: CATALOG
            catalog = await self._catalog(order_id)
            # Phase 2: PRICING
            pricing = await self._pricing(catalog)
            # Phase 3: CHECKOUT
            checkout = await self._checkout(customer_id, pricing)
            # Phase 4: FULFILLMENT
            fulfilled = await self._fulfill(order_id, checkout)
            # Phase 5: RECONCILE
            reconciled = await self._reconcile(checkout)
            # Phase 6: NOTIFY
            await self._notify(customer_id, fulfilled, reconciled)
            return {
                "status": "completed",
                "session_id": self.session_id,
                "order_id": order_id,
                "amount": pricing.get("total", 0),
                "fulfilled": fulfilled,
            }
        except Exception as exc:
            logger.exception("commerce_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _catalog(self, order_id: str) -> Dict[str, Any]:
        r = await self.registry.execute("supabase", "supabase_select", {
            "table": "orders", "columns": "*", "filters": {"id": order_id}, "limit": 1,
        })
        rows = r.data if r.success else []
        return rows[0] if rows else {}

    async def _pricing(self, catalog: Dict[str, Any]) -> Dict[str, Any]:
        items = catalog.get("items", [])
        total = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)
        return {"items": items, "total": total, "currency": "usd"}

    async def _checkout(self, customer_id: str, pricing: Dict[str, Any]) -> Dict[str, Any]:
        r = await self.registry.execute("stripe", "stripe_create_charge", {
            "amount": pricing["total"],
            "currency": pricing["currency"],
            "customer": customer_id,
            "description": f"Order checkout {self.session_id}",
        })
        return {"charge_id": r.data.get("id", ""), "success": r.success} if r.success else {}

    async def _fulfill(self, order_id: str, checkout: Dict[str, Any]) -> bool:
        r = await self.registry.execute("supabase", "supabase_update", {
            "table": "orders", "filters": {"id": order_id},
            "data": {"status": "fulfilled", "charge_id": checkout.get("charge_id")},
        })
        return r.success

    async def _reconcile(self, checkout: Dict[str, Any]) -> bool:
        r = await self.registry.execute("aws", "aws_s3_list_buckets", {})
        return r.success

    async def _notify(self, customer_id: str, fulfilled: bool, reconciled: bool):
        status = "fulfilled" if fulfilled else "failed"
        await self.registry.execute("slack", "slack_post_message", {
            "channel": "#commerce",
            "text": f"Order {self.session_id} for {customer_id}: {status}",
        })
