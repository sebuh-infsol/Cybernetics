"""Adapter unit tests."""

import pytest
from cybernetics.adapters.base import MCPAdapter, ToolResult

class DummyAdapter(MCPAdapter):
    name = "dummy"
    def __init__(self):
        super().__init__()
        self.register_tool("add", "Add", {"a": {"type": "integer"}, "b": {"type": "integer"}}, ["a", "b"], self._add)
    async def _add(self, a: int, b: int) -> int:
        return a + b
    async def health(self):
        return {"status": "healthy"}

@pytest.mark.asyncio
async def test_execute_success():
    a = DummyAdapter()
    r = await a.execute("add", {"a": 2, "b": 3})
    assert r.success is True
    assert r.data == 5

@pytest.mark.asyncio
async def test_execute_unknown_tool():
    a = DummyAdapter()
    r = await a.execute("nope", {})
    assert r.success is False
    assert "not found" in r.error
