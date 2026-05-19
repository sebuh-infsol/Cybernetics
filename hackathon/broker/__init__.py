# Omni-MCP Broker — Google Cloud Rapid Agent Hackathon
# FastAPI MCP server with unified SSE endpoint for Gemini 3 agents

from .server import app
from .router import Router

__all__ = ["app", "Router"]
