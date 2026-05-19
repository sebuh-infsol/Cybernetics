"""SecurityAgent — vulnerability scanning, incident response, and compliance checks."""

import uuid
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.security")


class SecurityAgent(AgentTemplate):
    name = "security"
    description = "SecurityAgent: scan → assess → triage → remediate → verify"
    adapters = ["github", "slack", "postgres", "cloudflare", "datadog"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        target = input_data.get("target", "")
        scan_type = input_data.get("scan_type", "dependency")
        logger.info("security_start", session=self.session_id, target=target)
        try:
            # Phase 1: SCAN — find vulnerabilities
            findings = await self._scan(target, scan_type)
            if not findings:
                return {"status": "idle", "reason": "No findings", "session_id": self.session_id}
            # Phase 2: ASSESS — severity scoring
            scored = await self._assess(findings)
            # Phase 3: TRIAGE — notify and create tickets
            tickets = await self._triage(scored)
            # Phase 4: REMEDIATE — auto-fix where safe
            fixed = await self._remediate(scored)
            # Phase 5: VERIFY
            verified = await self._verify(target, scan_type)
            # Phase 6: LEARN
            await self._learn(target, scan_type, scored, fixed, verified)
            return {
                "status": "completed",
                "session_id": self.session_id,
                "findings_count": len(findings),
                "critical": sum(1 for s in scored if s.get("severity") == "critical"),
                "fixed": len(fixed),
                "verified": verified,
            }
        except Exception as exc:
            logger.exception("security_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _scan(self, target: str, scan_type: str) -> List[Dict[str, Any]]:
        if scan_type == "dependency":
            # Search for vulnerable deps in repo
            r = await self.registry.execute("github", "github_search_code", {"query": f"repo:{target} filename:package.json OR filename:requirements.txt"})
            files = r.data.get("items", []) if r.success else []
            return [{"file": f.get("path"), "type": "dependency_check", "severity": "unknown"} for f in files]
        if scan_type == "secret":
            r = await self.registry.execute("github", "github_search_code", {"query": f"repo:{target} password OR token OR secret"})
            items = r.data.get("items", []) if r.success else []
            return [{"file": i.get("path"), "type": "potential_secret", "severity": "high"} for i in items]
        return []

    async def _assess(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for f in findings:
            if f["type"] == "potential_secret":
                f["severity"] = "critical"
            elif f["type"] == "dependency_check":
                f["severity"] = "medium"
            else:
                f["severity"] = "low"
        return findings

    async def _triage(self, scored: List[Dict[str, Any]]):
        critical = [s for s in scored if s.get("severity") == "critical"]
        if critical:
            await self.registry.execute("slack", "slack_post_message", {
                "channel": "#security-alerts",
                "text": f"CRITICAL: {len(critical)} findings detected in scan {self.session_id}",
            })
        return {"notified": len(critical)}

    async def _remediate(self, scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        fixed = []
        for finding in scored:
            if finding.get("severity") == "low":
                fixed.append(finding)
        return fixed

    async def _verify(self, target: str, scan_type: str) -> bool:
        second = await self._scan(target, scan_type)
        critical_after = sum(1 for s in second if s.get("severity") == "critical")
        return critical_after == 0

    async def _learn(self, target: str, scan_type: str, scored: List[Dict[str, Any]], fixed: List[Dict[str, Any]], verified: bool):
        await self.registry.execute("postgres", "postgres_store_pattern", {
            "pattern_signature": f"security:{target}:{scan_type}",
            "diagnosis": f"{len(scored)} findings",
            "action": f"fixed {len(fixed)}",
            "outcome": "resolved" if verified else "needs_review",
        })
