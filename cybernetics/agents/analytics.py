"""AnalyticsAgent — metrics dashboards and intelligent alerting."""

import uuid
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.analytics")


class AnalyticsAgent(AgentTemplate):
    name = "analytics"
    description = "AnalyticsAgent: collect → aggregate → detect anomaly → alert → visualize"
    adapters = ["datadog", "postgres", "elastic", "slack"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        metric = input_data.get("metric", "")
        service = input_data.get("service", "")
        logger.info("analytics_start", session=self.session_id, metric=metric, service=service)
        try:
            # Phase 1: COLLECT
            raw = await self._collect(metric, service)
            # Phase 2: AGGREGATE
            aggregated = await self._aggregate(raw)
            # Phase 3: DETECT
            anomalies = await self._detect(aggregated)
            # Phase 4: ALERT
            await self._alert(anomalies, service, metric)
            # Phase 5: VISUALIZE
            dashboard = await self._visualize(service, aggregated)
            # Phase 6: LEARN
            await self._learn(service, metric, anomalies)
            return {
                "status": "completed",
                "session_id": self.session_id,
                "anomalies": len(anomalies),
                "dashboard_url": dashboard.get("url", ""),
            }
        except Exception as exc:
            logger.exception("analytics_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _collect(self, metric: str, service: str) -> List[Dict[str, Any]]:
        r = await self.registry.execute("datadog", "datadog_query_metrics", {
            "query": f"avg:{metric}{{service:{service}}}",
            "from": "now-24h",
        })
        return r.data.get("series", []) if r.success else []

    async def _aggregate(self, raw: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Compute basic stats from series
        values = []
        for series in raw:
            for point in series.get("pointlist", []):
                if point[1] is not None:
                    values.append(point[1])
        if not values:
            return {"count": 0, "mean": 0, "std": 0, "max": 0}
        import statistics
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "max": max(values),
            "min": min(values),
        }

    async def _detect(self, aggregated: Dict[str, Any]) -> List[Dict[str, Any]]:
        mean = aggregated.get("mean", 0)
        std = aggregated.get("std", 0)
        max_val = aggregated.get("max", 0)
        threshold = mean + 3 * std
        if max_val > threshold:
            return [{"type": "spike", "value": max_val, "threshold": threshold}]
        return []

    async def _alert(self, anomalies: List[Dict[str, Any]], service: str, metric: str):
        if anomalies:
            await self.registry.execute("slack", "slack_post_message", {
                "channel": "#analytics-alerts",
                "text": f"ANOMALY: {service}.{metric} spike detected — {anomalies[0]['value']:.2f} (threshold: {anomalies[0]['threshold']:.2f})",
            })

    async def _visualize(self, service: str, aggregated: Dict[str, Any]) -> Dict[str, Any]:
        # Store aggregated metrics in Postgres for dashboard queries
        r = await self.registry.execute("postgres", "postgres_log_incident", {
            "incident": {
                "service": f"analytics:{service}",
                "problem_title": "metrics snapshot",
                "diagnosis": f"mean={aggregated.get('mean', 0):.2f}, max={aggregated.get('max', 0):.2f}",
                "action": "snapshot",
                "outcome": "resolved",
                "session_id": self.session_id,
            }
        })
        return {"url": "", "stored": r.success}

    async def _learn(self, service: str, metric: str, anomalies: List[Dict[str, Any]]):
        await self.registry.execute("postgres", "postgres_store_pattern", {
            "pattern_signature": f"analytics:{service}:{metric}",
            "diagnosis": f"{len(anomalies)} anomalies detected",
            "action": "alert and snapshot",
            "outcome": "resolved",
        })
