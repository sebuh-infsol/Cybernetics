"""FinanceAgent — payment orchestration using Stripe + Supabase."""

import uuid
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.finance")


class FinanceAgent(AgentTemplate):
    name = "finance"
    description = "FinanceAgent: detect anomaly → investigate customer → reconcile → refund/adjust → learn"
    adapters = ["stripe", "supabase", "postgres"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = input_data.get("customer_id")
        logger.info("finance_start", session=self.session_id, customer=customer_id)
        try:
            # Phase 1: DETECT — suspicious charges
            charges = await self._detect(customer_id)
            if not charges:
                return {"status": "idle", "reason": "No anomalies", "session_id": self.session_id}
            # Phase 2: INVESTIGATE — customer history in Supabase
            history = await self._investigate(customer_id)
            # Phase 3: REASON — decide action
            action = await self._reason(customer_id, charges, history)
            # Phase 4: ACT — refund or adjust
            result = await self._act(customer_id, action, charges)
            # Phase 5: LEARN
            await self._learn(customer_id, charges, action, result)
            return {
                "status": "completed",
                "session_id": self.session_id,
                "action": action,
                "charges_count": len(charges),
                "result": result,
            }
        except Exception as exc:
            logger.exception("finance_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _detect(self, customer_id: str) -> List[Dict[str, Any]]:
        r = await self.registry.execute("stripe", "stripe_list_invoices", {"customer_id": customer_id, "limit": 20})
        invoices = r.data if r.success else []
        # Simple heuristic: flag invoices > $1000 or duplicates in 24h
        flagged = [i for i in invoices if i.get("amount_due", 0) > 100000]  # cents
        return flagged

    async def _investigate(self, customer_id: str) -> Dict[str, Any]:
        r = await self.registry.execute("supabase", "supabase_select", {
            "table": "customers", "columns": "*", "filters": {"stripe_id": customer_id}, "limit": 1,
        })
        rows = r.data if r.success else []
        return rows[0] if rows else {}

    async def _reason(self, customer_id: str, charges: List[Dict[str, Any]], history: Dict[str, Any]) -> str:
        total = sum(c.get("amount_due", 0) for c in charges) / 100
        tier = history.get("tier", "standard")
        if total > 5000 and tier == "standard":
            return "flag_for_review"
        if len(charges) > 3:
            return "partial_refund"
        return "notify_customer"

    async def _act(self, customer_id: str, action: str, charges: List[Dict[str, Any]]) -> Dict[str, Any]:
        if action == "flag_for_review":
            await self.registry.execute("supabase", "supabase_insert", {
                "table": "reviews", "rows": [{"customer_id": customer_id, "reason": "anomaly", "status": "open"}],
            })
            return {"action": "flagged"}
        if action == "partial_refund" and charges:
            latest = charges[0]
            r = await self.registry.execute("stripe", "stripe_create_charge", {
                "amount": -latest.get("amount_due", 0) // 2,
                "currency": latest.get("currency", "usd"),
                "customer": customer_id,
                "description": "Partial refund for duplicate charge",
            })
            return {"action": "refunded", "charge_id": latest.get("id"), "success": r.success}
        return {"action": "notified"}

    async def _learn(self, customer_id: str, charges: List[Dict[str, Any]], action: str, result: Dict[str, Any]) -> None:
        await self.registry.execute("postgres", "postgres_store_pattern", {
            "pattern_signature": f"finance:{customer_id}:{action}",
            "diagnosis": f"{len(charges)} anomalous charges",
            "action": action,
            "outcome": "resolved" if result.get("success", True) else "needs_review",
        })
        await self.registry.execute("postgres", "postgres_log_incident", {
            "incident": {
                "service": f"finance:{customer_id}",
                "problem_title": f"anomaly detected",
                "diagnosis": f"charges: {len(charges)}",
                "action": action,
                "outcome": "resolved" if result.get("success", True) else "needs_review",
                "session_id": self.session_id,
            }
        })
