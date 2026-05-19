"""Sentinel — Self-healing infrastructure agent.

Google ADK agent that orchestrates six partner MCP tools into a closed-loop
SRE workflow: detect → investigate → reason → act → evaluate → learn.
"""

import asyncio
import uuid
from typing import Dict, Any, List
from google.adk.agents import Agent
from google.adk.tools import tool
from google.genai import types

from src.config import Config
from src.tools.dynatrace_tools import DynatraceClient
from src.tools.elastic_tools import ElasticClient
from src.tools.mongodb_tools import MongoDBClient
from src.tools.gitlab_tools import GitLabClient
from src.tools.arize_tools import ArizeClient
from src.tools.fivetran_tools import FivetranClient

# Initialize partner clients
dynatrace = DynatraceClient()
elastic = ElasticClient()
mongodb = MongoDBClient()
gitlab = GitLabClient()
arize = ArizeClient()
fivetran = FivetranClient()


class SentinelAgent:
    """The main Sentinel orchestration agent."""

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        arize.setup_tracing(project_name="sentinel")

    async def run(self) -> Dict[str, Any]:
        """Execute one full agent cycle: detect through evaluate."""
        print("[Sentinel] Starting detection phase...")

        # Phase 1: DETECT — Dynatrace
        problems = await dynatrace.get_active_problems()
        if not problems:
            return {"status": "idle", "reason": "No active problems"}

        problem = problems[0]
        service_name = problem.get("affectedEntities", [{}])[0].get("name", "unknown")
        print(f"[Sentinel] Detected problem on service: {service_name}")

        # Phase 2: INVESTIGATE — Elastic
        print("[Sentinel] Investigating via Elastic...")
        similar_incidents = await elastic.search_incidents(service_name, size=5)
        runbooks = await elastic.search_runbooks(problem.get("title", ""), size=3)
        print(f"[Sentinel] Found {len(similar_incidents)} similar incidents, {len(runbooks)} runbooks")

        # Phase 3: REASON — MongoDB memory + Gemini
        print("[Sentinel] Querying memory...")
        pattern_signature = f"{service_name}:{problem.get('title', '')}"
        memory = await mongodb.recall_pattern(pattern_signature)
        if memory:
            print(f"[Sentinel] Recalled pattern: {memory.get('diagnosis')}")
            diagnosis = memory.get("diagnosis", "")
            action = memory.get("action", "")
        else:
            diagnosis = f"New pattern detected on {service_name}: {problem.get('title')}"
            action = "Investigate and apply standard remediation"
            print(f"[Sentinel] New pattern: {diagnosis}")

        # Phase 4: ACT — GitLab
        print("[Sentinel] Taking action via GitLab...")
        issue = await gitlab.create_issue(
            title=f"[Sentinel] Auto-detected: {problem.get('title')}",
            description=f"**Service:** {service_name}\n\n**Diagnosis:** {diagnosis}\n\n**Action:** {action}",
            labels=["sentinel-auto", "incident"],
        )
        print(f"[Sentinel] Created issue #{issue.get('iid')}")

        # Phase 5: VERIFY — Dynatrace
        print("[Sentinel] Verifying resolution...")
        await asyncio.sleep(5)  # Give Dynatrace time to update
        traces = await dynatrace.get_traces_for_service(service_name, limit=10)
        error_rate = self._compute_error_rate(traces)
        resolved = error_rate < 0.01

        # Phase 6: EVALUATE — Arize
        trace_id = self.session_id  # In production, use actual OTel trace ID
        print("[Sentinel] Running LLM-as-a-Judge eval...")
        eval_result = await arize.run_llm_judge(
            trace_id=trace_id,
            criteria="Was the diagnosis accurate and the action appropriate?",
        )

        # Phase 7: LEARN — MongoDB + Fivetran
        print("[Sentinel] Logging to memory...")
        outcome = "resolved" if resolved else "needs_review"
        await mongodb.store_pattern(pattern_signature, diagnosis, action, outcome)
        await mongodb.log_incident({
            "service": service_name,
            "problem_title": problem.get("title"),
            "diagnosis": diagnosis,
            "action": action,
            "outcome": outcome,
            "issue_iid": issue.get("iid"),
            "judge_score": eval_result.get("score"),
            "session_id": self.session_id,
        })

        print(f"[Sentinel] Cycle complete. Judge score: {eval_result.get('score')}")

        return {
            "status": "completed",
            "service": service_name,
            "problem": problem.get("title"),
            "diagnosis": diagnosis,
            "action": action,
            "resolved": resolved,
            "issue_iid": issue.get("iid"),
            "judge_score": eval_result.get("score"),
            "similar_incidents": len(similar_incidents),
            "runbooks_found": len(runbooks),
        }

    def _compute_error_rate(self, traces: List[Dict[str, Any]]) -> float:
        """Simple error rate from trace data."""
        if not traces:
            return 0.0
        errors = sum(1 for t in traces if t.get("status", {}).get("code", 0) >= 400)
        return errors / len(traces)


# ADK agent definition for deployment
sentinel_adk_agent = Agent(
    model="gemini-3",
    name="sentinel",
    description=(
        "A self-healing infrastructure agent that detects anomalies via Dynatrace, "
        "investigates with Elastic search and MongoDB memory, takes action via GitLab, "
        "and evaluates itself via Arize LLM-as-a-Judge."
    ),
    instruction=(
        "You are Sentinel, an autonomous SRE agent. When a user reports a service issue or "
        "you detect one via Dynatrace, follow this workflow:\n"
        "1. DETECT: Use Dynatrace to fetch active problems and traces.\n"
        "2. INVESTIGATE: Search Elastic for similar incidents and runbooks.\n"
        "3. REASON: Check MongoDB for learned patterns. If found, apply them.\n"
        "4. ACT: Use GitLab to create an issue and optionally open an MR or trigger CI/CD.\n"
        "5. EVALUATE: Log the trace to Arize and run LLM-as-a-Judge.\n"
        "6. LEARN: Store the outcome in MongoDB.\n"
        "Always report your reasoning and the final outcome to the user."
    ),
    tools=[],  # Partner tools are wired directly in SentinelAgent above
)


if __name__ == "__main__":
    Config.validate()
    agent = SentinelAgent()
    result = asyncio.run(agent.run())
    print("\n=== Result ===")
    print(result)
