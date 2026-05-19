"""Sentinel — self-healing SRE agent template."""

import uuid
import asyncio
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.sentinel")


class SentinelAgent(AgentTemplate):
    name = "sentinel"
    description = "Self-healing SRE agent: detect → investigate → reason → act → evaluate → learn"
    adapters = ["dynatrace", "elastic", "postgres", "gitlab", "arize", "fivetran"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        logger.info("sentinel_cycle_start", session=self.session_id)
        try:
            problems = await self._detect()
            if not problems:
                return {"status": "idle", "reason": "No active problems", "session_id": self.session_id}
            problem = problems[0]
            service = problem.get("affectedEntities", [{}])[0].get("name", "unknown")
            similar, runbooks = await self._investigate(service, problem.get("title", ""))
            diagnosis, action = await self._reason(service, problem.get("title", ""))
            issue = await self._act(service, problem.get("title", ""), diagnosis, action)
            resolved = await self._verify(service)
            score = await self._evaluate(diagnosis, action)
            await self._learn(service, problem.get("title", ""), diagnosis, action, resolved, issue, score)
            return {
                "status": "completed",
                "service": service,
                "problem": problem.get("title"),
                "diagnosis": diagnosis,
                "action": action,
                "resolved": resolved,
                "issue_iid": issue.get("iid"),
                "judge_score": score,
                "session_id": self.session_id,
            }
        except Exception as exc:
            logger.exception("sentinel_cycle_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _detect(self) -> List[Dict[str, Any]]:
        r = await self.registry.execute("dynatrace", "dynatrace_get_problems", {"from": "now-1h", "status": "OPEN"})
        return r.data if r.success else []

    async def _investigate(self, service: str, title: str):
        similar = await self.registry.execute("elastic", "elastic_search_incidents", {"query": service, "size": 5})
        runbooks = await self.registry.execute("elastic", "elastic_search_runbooks", {"symptom": title, "size": 3})
        return (similar.data if similar.success else []), (runbooks.data if runbooks.success else [])

    async def _reason(self, service: str, title: str):
        sig = f"{service}:{title}"
        mem = await self.registry.execute("postgres", "postgres_recall_pattern", {"pattern_signature": sig})
        if mem.success and mem.data:
            return mem.data.get("diagnosis", ""), mem.data.get("action", "")
        return f"New pattern on {service}: {title}", "Investigate and apply standard remediation"

    async def _act(self, service: str, title: str, diagnosis: str, action: str):
        r = await self.registry.execute("gitlab", "gitlab_create_issue", {
            "title": f"[Sentinel] Auto-detected: {title}",
            "description": f"**Service:** {service}\n\n**Diagnosis:** {diagnosis}\n\n**Action:** {action}",
            "labels": ["sentinel-auto", "incident"],
        })
        return r.data if r.success else {}

    async def _verify(self, service: str) -> bool:
        # Poll Dynatrace with backoff instead of sleep
        for attempt in range(5):
            traces = await self.registry.execute("dynatrace", "dynatrace_get_traces", {"service_name": service, "limit": 10})
            if traces.success:
                data = traces.data
                if isinstance(data, list):
                    errors = sum(1 for t in data if t.get("status", {}).get("code", 0) >= 400)
                    if (errors / max(len(data), 1)) < 0.01:
                        return True
            await asyncio.sleep(2 ** attempt)
        return False

    async def _evaluate(self, diagnosis: str, action: str) -> float:
        trace = f"Diagnosis: {diagnosis}\nAction: {action}"
        r = await self.registry.execute("arize", "arize_run_judge", {
            "trace_id": self.session_id,
            "criteria": "Was the diagnosis accurate and the action appropriate?",
            "trace_content": trace,
        })
        return r.data.get("score", 0.5) if r.success else 0.5

    async def _learn(self, service: str, title: str, diagnosis: str, action: str, resolved: bool, issue: Dict[str, Any], score: float):
        sig = f"{service}:{title}"
        outcome = "resolved" if resolved else "needs_review"
        await self.registry.execute("postgres", "postgres_store_pattern", {
            "pattern_signature": sig, "diagnosis": diagnosis, "action": action, "outcome": outcome,
        })
        await self.registry.execute("postgres", "postgres_log_incident", {
            "incident": {
                "service": service, "problem_title": title, "diagnosis": diagnosis,
                "action": action, "outcome": outcome, "issue_iid": issue.get("iid"),
                "judge_score": score, "session_id": self.session_id,
            }
        })
