"""Arize adapter — real LLM-as-a-Judge via Gemini."""

from typing import Dict, Any, List
import httpx
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.arize")


class ArizeAdapter(MCPAdapter):
    name = "arize"
    description = "Arize Phoenix — tracing, LLM-as-a-Judge"

    def __init__(self):
        super().__init__()
        self.endpoint = settings.arize_endpoint.rstrip("/")
        self.api_key = settings.arize_api_key
        self._project = "sentinel"
        self.register_tool(
            "arize_run_judge",
            "Run LLM-as-a-Judge on a trace using Gemini",
            {"trace_id": {"type": "string"}, "criteria": {"type": "string"}, "trace_content": {"type": "string"}},
            ["trace_id", "criteria", "trace_content"],
            self._run_judge,
        )
        self.register_tool(
            "arize_log_eval",
            "Log an evaluation result to Phoenix",
            {"trace_id": {"type": "string"}, "score": {"type": "number"}, "label": {"type": "string"}, "explanation": {"type": "string"}},
            ["trace_id", "score", "label"],
            self._log_eval,
        )

    @circuit("arize", failure_threshold=5, recovery_timeout=60)
    async def _run_judge(self, trace_id: str, criteria: str, trace_content: str) -> Dict[str, Any]:
        """Call Gemini to judge the trace content against criteria."""
        import json
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"You are an expert evaluator. Score the following trace content against the criteria.\n\n"
            f"Criteria: {criteria}\n\n"
            f"Trace content: {trace_content}\n\n"
            f"Respond with a JSON object: {{'score': float 0-1, 'label': 'correct' or 'needs_review', 'explanation': string}}"
        )
        response = model.generate_content(prompt)
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            result = {}
        return {
            "trace_id": trace_id,
            "score": result.get("score", 0.5),
            "label": result.get("label", "needs_review"),
            "explanation": result.get("explanation", ""),
        }

    @circuit("arize", failure_threshold=5, recovery_timeout=60)
    async def _log_eval(self, trace_id: str, score: float, label: str, explanation: str = "") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.endpoint}/v1/evaluations",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "project_name": self._project,
                    "evaluations": [{
                        "trace_id": trace_id,
                        "name": "llm_judge",
                        "score": score,
                        "label": label,
                        "explanation": explanation,
                    }],
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.endpoint}/health", headers={"Authorization": f"Bearer {self.api_key}"})
                resp.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
