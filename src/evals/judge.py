"""LLM-as-a-Judge evaluators for Sentinel self-evaluation.

Evaluates agent reasoning quality, action appropriateness, and
whether the diagnosis matched the actual root cause.
"""

from typing import Dict, Any
from google import genai
from src.config import Config

class LLMJudge:
    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    async def evaluate_diagnosis(self, problem: str, diagnosis: str, context: str) -> Dict[str, Any]:
        """Score whether the diagnosis correctly identifies the root cause."""
        prompt = f"""You are an expert SRE evaluator. Rate the quality of this diagnosis on a scale of 0.0 to 1.0.

Problem: {problem}
Diagnosis: {diagnosis}
Context: {context}

Respond ONLY in this format:
Score: <float between 0.0 and 1.0>
Reasoning: <one sentence explanation>
Label: <"correct" if score > 0.8, "partial" if 0.5-0.8, "incorrect" if < 0.5>
"""
        response = await self.client.aio.models.generate_content(
            model="gemini-3",
            contents=prompt,
        )
        text = response.text

        # Parse structured response
        score = 0.5
        reasoning = ""
        label = "partial"

        for line in text.split("\n"):
            if line.startswith("Score:"):
                try:
                    score = float(line.replace("Score:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("Reasoning:"):
                reasoning = line.replace("Reasoning:", "").strip()
            elif line.startswith("Label:"):
                label = line.replace("Label:", "").strip()

        return {
            "score": max(0.0, min(1.0, score)),
            "reasoning": reasoning,
            "label": label,
            "evaluator": "gemini-3-llm-judge",
        }

    async def evaluate_action(self, diagnosis: str, action: str, outcome: str) -> Dict[str, Any]:
        """Score whether the action was appropriate given the diagnosis and outcome."""
        prompt = f"""You are an expert SRE evaluator. Rate whether the action taken was appropriate.

Diagnosis: {diagnosis}
Action: {action}
Outcome: {outcome}

Respond ONLY in this format:
Score: <float between 0.0 and 1.0>
Reasoning: <one sentence explanation>
Label: <"correct" if score > 0.8, "partial" if 0.5-0.8, "incorrect" if < 0.5>
"""
        response = await self.client.aio.models.generate_content(
            model="gemini-3",
            contents=prompt,
        )
        text = response.text

        score = 0.5
        reasoning = ""
        label = "partial"

        for line in text.split("\n"):
            if line.startswith("Score:"):
                try:
                    score = float(line.replace("Score:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("Reasoning:"):
                reasoning = line.replace("Reasoning:", "").strip()
            elif line.startswith("Label:"):
                label = line.replace("Label:", "").strip()

        return {
            "score": max(0.0, min(1.0, score)),
            "reasoning": reasoning,
            "label": label,
            "evaluator": "gemini-3-llm-judge",
        }
