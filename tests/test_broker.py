"""Broker endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from cybernetics.broker.server import app, mcp_registry
from cybernetics.registry.manager import register_adapter
from cybernetics.adapters.base import MCPAdapter, ToolResult

class MockAdapter(MCPAdapter):
    name = "mock"
    description = "Mock"
    def __init__(self):
        super().__init__()
        self.register_tool("mock_echo", "Echo", {"msg": {"type": "string"}}, ["msg"], self._echo)
    async def _echo(self, msg: str) -> str:
        return msg
    async def health(self):
        return {"status": "healthy"}

register_adapter("mock", MockAdapter)
mcp_registry.load(["mock"])

client = TestClient(app, raise_server_exceptions=False)

@pytest.fixture(autouse=True)
def reset_registry():
    mcp_registry.load(["mock"])

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("healthy", "degraded")

def test_list_tools_unauth():
    r = client.get("/mcp/tools")
    assert r.status_code == 401

def test_list_tools_auth():
    r = client.get("/mcp/tools", headers={"Authorization": "Bearer test-key"})
    assert r.status_code == 200
    assert "tools" in r.json()

def test_invoke_tool():
    r = client.post("/mcp/invoke", headers={"Authorization": "Bearer test-key"}, json={"adapter": "mock", "tool": "mock_echo", "arguments": {"msg": "hello"}})
    assert r.status_code == 200
    assert r.json()["result"]["data"] == "hello"
