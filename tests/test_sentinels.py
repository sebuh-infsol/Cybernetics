"""Sentinel pipeline tests."""

import pytest
from cybernetics.sentinels.pipeline import SentinelPipeline, Auditor, Guard
from cybernetics.adapters.base import ToolResult

@pytest.mark.asyncio
async def test_auditor():
    pipe = SentinelPipeline([Auditor()])
    async def run():
        return ToolResult(success=True, data="ok")
    result = await pipe.execute({"tool": "t", "adapter": "a"}, run)
    assert result.data == "ok"

@pytest.mark.asyncio
async def test_guard_blocks_sensitive():
    pipe = SentinelPipeline([Guard()])
    async def run():
        return "should not reach"
    with pytest.raises(ValueError):
        await pipe.execute({"arguments": {"password": "x"}}, run)
