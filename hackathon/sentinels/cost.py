# Sentinel: CostEstimator
# Tracks and estimates costs for tool calls

import logging
from typing import Any, Optional

logger = logging.getLogger("cybernetics.sentinels.cost")


class CostEstimator:
    """Tool call cost estimator and budget tracker."""

    name = "cost"

    def __init__(
        self,
        estimated_costs: dict = None,
        budget_limit: float = 5.00,
        warn_threshold: float = 3.00,
        currency: str = "USD",
    ):
        self.estimated_costs = estimated_costs or {}
        self.budget_limit = budget_limit
        self.warn_threshold = warn_threshold
        self.currency = currency
        self._total_cost = 0.0
        self._call_count = 0

    async def pre_check(self, method: str, params: dict) -> dict:
        """Estimate cost before executing tool call."""
        cost = self.estimated_costs.get(method, 0.0)
        new_total = self._total_cost + cost

        # Check budget
        if new_total > self.budget_limit:
            logger.warning(f"Cost: budget exceeded (${new_total:.2f} > ${self.budget_limit:.2f})")
            return {
                "blocked": True,
                "reason": f"Budget exceeded: ${new_total:.2f} > ${self.budget_limit:.2f} {self.currency}",
            }

        # Warn if approaching threshold
        if new_total > self.warn_threshold:
            logger.warning(f"Cost: approaching limit (${new_total:.2f} > ${self.warn_threshold:.2f})")

        return {"blocked": False, "estimated_cost": cost}

    async def post_check(self, method: str, result: Any, latency: float):
        """Record actual cost after execution."""
        cost = self.estimated_costs.get(method, 0.0)
        self._total_cost += cost
        self._call_count += 1
        logger.info(f"Cost: {method} = ${cost:.4f}, total = ${self._total_cost:.4f}")

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.budget_limit - self._total_cost)
