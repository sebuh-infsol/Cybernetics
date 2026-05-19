"""Google ADK bridge — exposes agent templates as ADK tools."""

from typing import Dict, Any
from google.adk.agents import Agent
from google.adk.tools import tool
from google.genai import types
import httpx
from cybernetics.config.settings import settings
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adk")


class MCPBrokerClient:
    """HTTP client to the Cybernetics MCP broker."""

    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or f"http://{settings.broker_host}:{settings.broker_port}").rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key or settings.broker_api_key}", "Content-Type": "application/json"}

    async def invoke(self, adapter: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/mcp/invoke",
                headers=self.headers,
                json={"adapter": adapter, "tool": tool_name, "arguments": arguments},
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/health", headers=self.headers)
            resp.raise_for_status()
            return resp.json()


# Singleton client
_broker = MCPBrokerClient()


@tool
def broker_invoke(adapter: str, tool_name: str, arguments: str = "{}") -> str:
    """Invoke any MCP tool through the Cybernetics broker.
    Args:
        adapter: e.g. 'postgres', 'github', 'stripe', 'aws'
        tool_name: e.g. 'postgres_log_incident', 'github_create_issue'
        arguments: JSON string of arguments
    """
    import json, asyncio
    args = json.loads(arguments)
    result = asyncio.get_event_loop().run_until_complete(_broker.invoke(adapter, tool_name, args))
    return json.dumps(result, indent=2)


@tool
def broker_list_tools() -> str:
    """List all available MCP tools."""
    import asyncio, json
    result = asyncio.get_event_loop().run_until_complete(
        asyncio.get_event_loop().run_in_executor(None, _sync_list_tools)
    )
    return json.dumps(result, indent=2)


def _sync_list_tools() -> Dict[str, Any]:
    import httpx
    r = httpx.get(f"{_broker.base_url}/mcp/tools", headers=_broker.headers)
    r.raise_for_status()
    return r.json()


@tool
def sentinel_run(service_name: str = "") -> str:
    """Run the Sentinel SRE agent. Detects problems and auto-remediates.
    Args:
        service_name: Optional service to focus on.
    """
    import json, asyncio
    from cybernetics.agents.sentinel import SentinelAgent
    from cybernetics.registry.manager import Registry
    reg = Registry()
    reg.load(["dynatrace", "elastic", "postgres", "gitlab", "arize", "fivetran"])
    agent = SentinelAgent(reg)
    result = asyncio.get_event_loop().run_until_complete(agent.run({"service": service_name}))
    return json.dumps(result, indent=2)


@tool
def deploy_run(owner: str, repo: str, branch: str = "main", vercel_project_id: str = "", s3_bucket: str = "") -> str:
    """Run the Deploy agent to build and deploy.
    Args:
        owner: GitHub org/owner
        repo: Repository name
        branch: Git branch
        vercel_project_id: Vercel project ID
        s3_bucket: S3 bucket for artifacts
    """
    import json, asyncio
    from cybernetics.agents.deploy import DeployAgent
    from cybernetics.registry.manager import Registry
    reg = Registry()
    reg.load(["github", "vercel", "aws", "postgres"])
    agent = DeployAgent(reg)
    result = asyncio.get_event_loop().run_until_complete(agent.run({
        "owner": owner, "repo": repo, "branch": branch,
        "vercel_project_id": vercel_project_id, "s3_bucket": s3_bucket,
    }))
    return json.dumps(result, indent=2)


@tool
def finance_run(customer_id: str) -> str:
    """Run the Finance agent to detect payment anomalies.
    Args:
        customer_id: Stripe customer ID
    """
    import json, asyncio
    from cybernetics.agents.finance import FinanceAgent
    from cybernetics.registry.manager import Registry
    reg = Registry()
    reg.load(["stripe", "supabase", "postgres"])
    agent = FinanceAgent(reg)
    result = asyncio.get_event_loop().run_until_complete(agent.run({"customer_id": customer_id}))
    return json.dumps(result, indent=2)


@tool
def infra_run(zone_id: str, service_name: str) -> str:
    """Run the Infra agent for DNS + EC2 optimization.
    Args:
        zone_id: Cloudflare zone ID
        service_name: Service name in Dynatrace
    """
    import json, asyncio
    from cybernetics.agents.infra import InfraAgent
    from cybernetics.registry.manager import Registry
    reg = Registry()
    reg.load(["dynatrace", "cloudflare", "aws", "postgres"])
    agent = InfraAgent(reg)
    result = asyncio.get_event_loop().run_until_complete(agent.run({"zone_id": zone_id, "service_name": service_name}))
    return json.dumps(result, indent=2)


# ADK Agent definition
cybernetics_adk_agent = Agent(
    model="gemini-3",
    name="cybernetics",
    description="Composable MCP broker for Google Cloud Agents. Can deploy, monitor, secure, and optimize infrastructure.",
    instruction=(
        "You are the Cybernetics meta-agent. You orchestrate 13 MCP adapters and 4 agent templates:\n"
        "1. Sentinel — self-healing SRE (Dynatrace, Elastic, GitLab)\n"
        "2. DeployAgent — CI/CD (GitHub, Vercel, AWS)\n"
        "3. FinanceAgent — payment ops (Stripe, Supabase)\n"
        "4. InfraAgent — DNS + compute optimization (Cloudflare, AWS, Dynatrace)\n"
        "Use broker_invoke for any raw MCP tool call. Use the template tools for full workflows."
    ),
    tools=[broker_invoke, broker_list_tools, sentinel_run, deploy_run, finance_run, infra_run],
)
