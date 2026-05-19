"""Arize MCP tools — tracing, LLM-as-a-Judge, and self-introspection."""

import os
from typing import Dict, Any, List
from phoenix.otel import register
from openinference.instrumentation.gemini import GeminiInstrumentor
from phoenix import Client as PhoenixClient
from src.config import Config

class ArizeClient:
    def __init__(self):
        self.endpoint = Config.ARIZE_ENDPOINT
        self.api_key = Config.ARIZE_API_KEY
        self._instrumentor = None
        self._phoenix = None

    def setup_tracing(self, project_name: str = "sentinel"):
        """Register OpenTelemetry and instrument Gemini calls."""
        os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = self.endpoint
        os.environ["PHOENIX_API_KEY"] = self.api_key
        tracer_provider = register(project_name=project_name)
        self._instrumentor = GeminiInstrumentor()
        self._instrumentor.instrument()
        self._phoenix = PhoenixClient(endpoint=self.endpoint, api_key=self.api_key)
        return tracer_provider

    async def run_llm_judge(self, trace_id: str, criteria: str) -> Dict[str, Any]:
        """Run an LLM-as-a-Judge evaluation on a completed trace."""
        if not self._phoenix:
            raise RuntimeError("Tracing not initialized. Call setup_tracing() first.")

        # Fetch the trace from Phoenix
        trace = self._phoenix.get_trace(trace_id)

        # Simple heuristic judge: score based on criteria keywords found in reasoning
        reasoning = trace.get("attributes", {}).get("llm.prompts", "")
        score = 1.0 if criteria.lower() in reasoning.lower() else 0.5

        # Log the eval result back to Phoenix
        self._phoenix.log_evaluations(
            project_name="sentinel",
            evaluations=[
                {
                    "trace_id": trace_id,
                    "name": "llm_judge",
                    "score": score,
                    "label": "correct" if score > 0.8 else "needs_review",
                    "explanation": f"Evaluated against criteria: {criteria}",
                }
            ],
        )

        return {"trace_id": trace_id, "score": score, "criteria": criteria}

    async def query_own_history(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Query the agent's own trace history for self-introspection."""
        if not self._phoenix:
            raise RuntimeError("Tracing not initialized.")

        # Use Phoenix datasets to retrieve past traces matching the query
        traces = self._phoenix.query_spans(
            project_name="sentinel",
            query=query,
            limit=limit,
        )
        return traces
