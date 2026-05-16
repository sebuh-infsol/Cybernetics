# Omni-MCP Broker — FastAPI server with MCP SSE endpoint
# Unified gateway for Google Cloud Agent Builder (Gemini 3)

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from broker.router import Router
from registry.loader import RegistryLoader
from sentinels.auditor import Auditor
from sentinels.safety import SafetyGuard
from sentinels.cost import CostEstimator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cybernetics.broker")


class MCPRequest(BaseModel):
    """MCP protocol request wrapper."""
    jsonrpc: str = "2.0"
    method: str
    params: dict = Field(default_factory=dict)
    id: Optional[int] = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    uptime: float
    registered_servers: int
    active_tools: int
    version: str = "0.1.0-hackathon"


class RegistryStatus(BaseModel):
    """Registry status endpoint response."""
    servers: dict
    total_tools: int
    active_sentinels: list
    last_updated: float


# Global state
_start_time = time.time()
registry: Optional[RegistryLoader] = None
router: Optional[Router] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global registry, router

    # Startup
    logger.info("Cybernetics Omni-MCP Broker starting up...")

    # Load configuration
    config_path = Path(__file__).parent.parent / "config.yaml"
    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}, using defaults")
        config_path = None

    # Initialize registry
    registry = RegistryLoader(config_path)
    await registry.load()
    logger.info(f"Registry loaded: {len(registry.servers)} servers, {registry.total_tools} tools")

    # Initialize sentinels
    auditor = Auditor()
    safety = SafetyGuard()
    cost = CostEstimator()
    logger.info("Sentinel middleware initialized")

    # Initialize router
    router = Router(registry, [auditor, safety, cost])
    logger.info("Router initialized with %d sentinels", len([auditor, safety, cost]))

    yield

    # Shutdown
    logger.info("Cybernetics Omni-MCP Broker shutting down...")
    await registry.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Cybernetics Omni-MCP Broker",
    description="Composable MCP server for Google Cloud Rapid Agent Hackathon",
    version="0.1.0-hackathon",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        uptime=time.time() - _start_time,
        registered_servers=len(registry.servers) if registry else 0,
        active_tools=registry.total_tools if registry else 0,
    )


@app.get("/registry/status", response_model=RegistryStatus)
async def registry_status():
    """Get registry status."""
    if not registry:
        raise HTTPException(status_code=503, detail="Registry not initialized")

    return RegistryStatus(
        servers={name: s.config for name, s in registry.servers.items()},
        total_tools=registry.total_tools,
        active_sentinels=["auditor", "safety", "cost"],
        last_updated=registry.last_updated,
    )


@app.post("/registry/reload")
async def reload_registry():
    """Reload registry from config."""
    if not registry:
        raise HTTPException(status_code=503, detail="Registry not initialized")

    await registry.reload()
    return {
        "status": "reloaded",
        "servers": len(registry.servers),
        "tools": registry.total_tools,
    }


@app.get("/mcp/sse")
async def mcp_sse():
    """MCP SSE endpoint for Gemini 3 Agent Builder."""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")

    async def event_stream():
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'version': '2025-03-26'})}\n\n"

        # Read incoming requests from client
        while True:
            try:
                # Read JSON-RPC request
                request = await app.request_body()
                if request:
                    data = json.loads(request)
                    # Process through router with sentinels
                    result = await router.route(data)
                    # Send response back
                    yield f"data: {json.dumps(result)}\n\n"
            except Exception as e:
                logger.error(f"SSE error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/mcp")
async def mcp_json_rpc(request: MCPRequest):
    """MCP JSON-RPC endpoint."""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")

    result = await router.route({
        "jsonrpc": request.jsonrpc,
        "method": request.method,
        "params": request.params,
        "id": request.id,
    })
    return JSONResponse(content=result)


@app.get("/tools")
async def list_tools():
    """List all available tools from all registered servers."""
    if not registry:
        raise HTTPException(status_code=503, detail="Registry not initialized")

    tools = []
    for name, server in registry.servers.items():
        for tool in server.tools:
            tools.append({
                "name": tool["name"],
                "server": name,
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
            })

    return {"tools": tools, "total": len(tools)}


@app.get("/partners")
async def list_partners():
    """List all configured partner tracks."""
    if not registry:
        raise HTTPException(status_code=503, detail="Registry not initialized")

    partners = []
    for name, server in registry.servers.items():
        partners.append({
            "name": name,
            "display_name": server.config.get("name", name),
            "enabled": server.enabled,
            "tool_count": len(server.tools),
            "transport": server.config.get("transport", "unknown"),
        })

    return {"partners": partners, "total": len(partners)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "broker.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
