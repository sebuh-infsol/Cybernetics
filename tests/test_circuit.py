"""Circuit breaker tests."""

import asyncio
import pytest
from cybernetics.circuit.breaker import CircuitBreaker, CircuitOpenError, circuit

@pytest.mark.asyncio
async def test_circuit_closes_after_failures():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
    async def fail():
        raise RuntimeError("boom")
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    with pytest.raises(CircuitOpenError):
        await cb.call(fail)
    assert cb.state() == "OPEN"

@pytest.mark.asyncio
async def test_circuit_recover():
    cb = CircuitBreaker("test2", failure_threshold=1, recovery_timeout=0.05)
    async def fail():
        raise RuntimeError("boom")
    with pytest.raises(RuntimeError):
        await cb.call(fail)
    with pytest.raises(CircuitOpenError):
        await cb.call(fail)
    await asyncio.sleep(0.06)
    async def ok():
        return 42
    r = await cb.call(ok)
    assert r == 42
    assert cb.state() == "CLOSED"

@pytest.mark.asyncio
async def test_decorator():
    @circuit("decorated", failure_threshold=1, recovery_timeout=0.1)
    async def flaky():
        raise RuntimeError("x")
    with pytest.raises(RuntimeError):
        await flaky()
    with pytest.raises(CircuitOpenError):
        await flaky()
