"""DataAgent — ETL pipeline orchestration, data quality, and schema drift detection."""

import uuid
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.data")


class DataAgent(AgentTemplate):
    name = "data"
    description = "DataAgent: extract → validate → transform → load → monitor"
    adapters = ["postgres", "supabase", "fivetran", "slack"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        source = input_data.get("source_table")
        destination = input_data.get("destination_table")
        logger.info("data_start", session=self.session_id, source=source, dest=destination)
        try:
            # Phase 1: EXTRACT
            raw = await self._extract(source)
            # Phase 2: VALIDATE
            quality = await self._validate(raw)
            # Phase 3: TRANSFORM
            transformed = await self._transform(raw, quality)
            # Phase 4: LOAD
            loaded = await self._load(destination, transformed)
            # Phase 5: MONITOR
            await self._monitor(source, destination, loaded)
            # Phase 6: LEARN
            await self._learn(source, destination, quality, loaded)
            return {
                "status": "completed",
                "session_id": self.session_id,
                "rows": len(raw),
                "quality_score": quality.get("score", 0),
                "loaded": loaded,
            }
        except Exception as exc:
            logger.exception("data_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _extract(self, source: str) -> List[Dict[str, Any]]:
        r = await self.registry.execute("supabase", "supabase_select", {"table": source, "columns": "*", "limit": 1000})
        return r.data if r.success else []

    async def _validate(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not rows:
            return {"score": 0, "issues": ["empty_source"]}
        null_counts = {}
        for col in rows[0].keys():
            nulls = sum(1 for r in rows if r.get(col) is None)
            null_counts[col] = nulls
        total = len(rows)
        score = max(0, 100 - sum(null_counts.values()) * 100 // max(total, 1))
        return {"score": score, "null_counts": null_counts, "row_count": total}

    async def _transform(self, rows: List[Dict[str, Any]], quality: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Simple dedupe + normalize
        seen = set()
        out = []
        for row in rows:
            key = str(row.get("id", row))
            if key not in seen:
                seen.add(key)
                out.append(row)
        return out

    async def _load(self, destination: str, rows: List[Dict[str, Any]]) -> bool:
        if not rows:
            return False
        r = await self.registry.execute("postgres", "postgres_upsert", {"table": destination, "rows": rows, "conflict_column": "id"})
        return r.success

    async def _monitor(self, source: str, destination: str, loaded: bool):
        if loaded:
            await self.registry.execute("slack", "slack_post_message", {
                "channel": "#data-pipelines",
                "text": f"Pipeline {self.session_id}: {source} -> {destination} completed successfully",
            })

    async def _learn(self, source: str, destination: str, quality: Dict[str, Any], loaded: bool):
        await self.registry.execute("postgres", "postgres_store_pattern", {
            "pattern_signature": f"data:{source}:{destination}",
            "diagnosis": f"quality score {quality.get('score', 0)}",
            "action": "ETL pipeline run",
            "outcome": "resolved" if loaded else "needs_review",
        })
