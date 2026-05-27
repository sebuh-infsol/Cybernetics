"""Circuit breaker for external service calls."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, Any, Optional
from functools import wraps
import time
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.circuit")


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class CircuitBreaker:
    """Per-service circuit breaker."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _failures: int = field(default=0, repr=False)
    _last_failure_time: Optional[float] = field(default=None, repr=False)
    _half_open_calls: int = field(default=0, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def call(self, fn: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and (time.monotonic() - self._last_failure_time) >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info("circuit_half_open", breaker=self.name)
                else:
                    raise CircuitOpenError(f"Circuit OPEN for {self.name}")

            if self._state == CircuitState.HALF_OPEN and self._half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError(f"Circuit HALF_OPEN limit reached for {self.name}")

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        try:
            result = await fn(*args, **kwargs)
            async with self._lock:
                self._state = CircuitState.CLOSED
                self._failures = 0
                self._last_failure_time = None
            return result
        except Exception as exc:
            async with self._lock:
                self._failures += 1
                self._last_failure_time = time.monotonic()
                if self._failures >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.error("circuit_opened", breaker=self.name, failures=self._failures)
            raise

    def state(self) -> str:
        return self._state.name


class CircuitOpenError(Exception):
    pass


# Global breaker registry
_breakers: Dict[str, CircuitBreaker] = {}


def get_breaker(name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _breakers[name]


def circuit(name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0):
    """Decorator to wrap an async function with a circuit breaker."""
    breaker = get_breaker(name, failure_threshold, recovery_timeout)

    def decorator(fn: Callable):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            return await breaker.call(fn, *args, **kwargs)
        return wrapper
    return decorator
