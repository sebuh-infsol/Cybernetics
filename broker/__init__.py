"""
Omni-MCP Broker
Main entry point for the composable MCP server.
"""
import asyncio
from fastapi import FastAPI
from mcp.server import Server
from registry import Registry
from sentinels import SentinelPipeline

app = FastAPI()
registry = Registry()
sentinel_pipeline = SentinelPipeline()

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    await registry.load_config("config.yaml")
    # Register with Google Cloud Agent Builder
    print("Broker started. Ready for Agent Builder.")
