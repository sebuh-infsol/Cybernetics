"""FastAPI MCP Broker — SSE endpoint, tool routing, auth."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer
import json
import asyncio

from cybernetics.config.settings import settings
from cybernetics.logging.logger import configure_logging, get_logger
from cybernetics.auth.middleware import APIKeyAuth, require_api_key
from cybernetics.registry.manager import Registry, register_adapter
from cybernetics.health.checks import registry as health_registry, HealthCheck, HealthStatus
from cybernetics.circuit.breaker import get_breaker, _breakers

# Import all adapters so they auto-register
from cybernetics.adapters.dynatrace import DynatraceAdapter
from cybernetics.adapters.elastic import ElasticAdapter
from cybernetics.adapters.postgres import PostgresAdapter
from cybernetics.adapters.gitlab import GitLabAdapter
from cybernetics.adapters.arize import ArizeAdapter
from cybernetics.adapters.fivetran import FivetranAdapter
from cybernetics.adapters.github import GitHubAdapter
from cybernetics.adapters.stripe import StripeAdapter
from cybernetics.adapters.aws import AWSAdapter
from cybernetics.adapters.vercel import VercelAdapter
from cybernetics.adapters.supabase import SupabaseAdapter
from cybernetics.adapters.cloudflare import CloudflareAdapter
from cybernetics.adapters.browser import BrowserAdapter
from cybernetics.adapters.chrome import ChromeAdapter
from cybernetics.adapters.firefox import FirefoxAdapter
from cybernetics.adapters.brave import BraveAdapter
from cybernetics.adapters.slack import SlackAdapter
from cybernetics.adapters.kubernetes import KubernetesAdapter
from cybernetics.adapters.datadog import DatadogAdapter
from cybernetics.adapters.notion import NotionAdapter
from cybernetics.adapters.linear import LinearAdapter

register_adapter("dynatrace", DynatraceAdapter)
register_adapter("elastic", ElasticAdapter)
register_adapter("postgres", PostgresAdapter)
register_adapter("gitlab", GitLabAdapter)
register_adapter("arize", ArizeAdapter)
register_adapter("fivetran", FivetranAdapter)
register_adapter("github", GitHubAdapter)
register_adapter("stripe", StripeAdapter)
register_adapter("aws", AWSAdapter)
register_adapter("vercel", VercelAdapter)
register_adapter("supabase", SupabaseAdapter)
register_adapter("cloudflare", CloudflareAdapter)
register_adapter("browser", BrowserAdapter)
register_adapter("chrome", ChromeAdapter)
register_adapter("firefox", FirefoxAdapter)
register_adapter("brave", BraveAdapter)
register_adapter("slack", SlackAdapter)
register_adapter("kubernetes", KubernetesAdapter)
register_adapter("datadog", DatadogAdapter)
register_adapter("notion", NotionAdapter)
register_adapter("linear", LinearAdapter)

logger = get_logger("cybernetics.broker")
bearer = HTTPBearer()

# Global registry
mcp_registry = Registry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("broker_startup", environment=settings.environment)
    # Load adapters based on config or all by default
    mcp_registry.load(list(ADAPTER_MAP.keys()))
    # Register health probes
    health_registry.register(lambda: _adapter_health_probe())
    yield
    logger.info("broker_shutdown")
    await mcp_registry.close_all()


app = FastAPI(title="Cybernetics MCP Broker", version="2026.5.2", lifespan=lifespan)
app.add_middleware(APIKeyAuth)


async def _adapter_health_probe() -> HealthCheck:
    checks = await mcp_registry.health()
    healthy = sum(1 for v in checks.values() if v.get("status") == "healthy")
    total = len(checks)
    status = HealthStatus.HEALTHY if healthy == total else (HealthStatus.DEGRADED if healthy > 0 else HealthStatus.UNHEALTHY)
    return HealthCheck(name="adapters", status=status, detail=f"{healthy}/{total} adapters healthy")


@app.get("/health")
async def health():
    return await health_registry.run_all()


@app.get("/mcp/tools")
async def list_tools(_: str = Depends(require_api_key)):
    return {"tools": mcp_registry.all_tools()}


@app.post("/mcp/invoke")
async def invoke_tool(request: Request, _: str = Depends(require_api_key)):
    body = await request.json()
    adapter_name = body.get("adapter")
    tool_name = body.get("tool")
    arguments = body.get("arguments", {})
    if not adapter_name or not tool_name:
        raise HTTPException(status_code=400, detail="adapter and tool required")
    result = await mcp_registry.execute(adapter_name, tool_name, arguments)
    return {"result": result}


@app.get("/mcp/sse")
async def mcp_sse(_: str = Depends(require_api_key)):
    """Server-Sent Events endpoint for real-time MCP streams."""
    async def event_stream():
        while True:
            health = await health_registry.run_all()
            yield f"data: {json.dumps({'type': 'health', 'payload': health})}\n\n"
            await asyncio.sleep(30)
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/mcp/circuits")
async def list_circuits(_: str = Depends(require_api_key)):
    return {"circuits": {name: get_breaker(name).state() for name in list(_breakers.keys())}}
