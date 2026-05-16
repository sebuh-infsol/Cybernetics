# Sentinel: Auditor
# Logs all tool calls for governance and compliance

import json
import time
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("cybernetics.sentinels.auditor")


class Auditor:
    """Tool call auditor — logs every request for governance."""

    name = "auditor"

    def __init__(self, log_path: str = "logs/audit.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = None
        self._entry_count = 0

    async def pre_check(self, method: str, params: dict) -> dict:
        """Pre-request audit check."""
        entry = {
            "timestamp": time.time(),
            "type": "audit",
            "event": "request",
            "method": method,
            "params": params,
        }
        self._log(entry)
        return {"blocked": False}

    async def post_check(self, method: str, result: Any, latency: float):
        """Post-request audit log."""
        entry = {
            "timestamp": time.time(),
            "type": "audit",
            "event": "response",
            "method": method,
            "latency_ms": round(latency * 1000, 2),
            "result": result,
        }
        self._log(entry)

    def _log(self, entry: dict):
        """Write audit entry to log file."""
        self._entry_count += 1
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

    @property
    def entry_count(self) -> int:
        return self._entry_count
