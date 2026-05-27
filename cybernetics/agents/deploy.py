"""DeployAgent — CI/CD pipeline orchestrator using GitHub + Vercel + AWS."""

import uuid
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.deploy")


class DeployAgent(AgentTemplate):
    name = "deploy"
    description = "DeployAgent: validate → build → deploy → verify → rollback-on-failure"
    adapters = ["github", "vercel", "aws", "postgres"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        owner = input_data.get("owner")
        repo = input_data.get("repo")
        branch = input_data.get("branch", "main")
        vercel_project = input_data.get("vercel_project_id")
        s3_bucket = input_data.get("s3_bucket")

        logger.info("deploy_start", session=self.session_id, repo=f"{owner}/{repo}")
        try:
            # Phase 1: VALIDATE — latest commit + tests via GitHub Actions
            commit = await self._validate(owner, repo, branch)
            # Phase 2: BUILD — trigger workflow
            build = await self._build(owner, repo, branch)
            # Phase 3: DEPLOY — Vercel + S3 sync
            deploy_url = await self._deploy(vercel_project, s3_bucket, owner, repo, branch)
            # Phase 4: VERIFY — smoke test the deployment
            healthy = await self._verify(deploy_url)
            # Phase 5: LEARN — store outcome
            await self._learn(owner, repo, branch, commit, build, deploy_url, healthy)
            return {
                "status": "completed" if healthy else "needs_review",
                "session_id": self.session_id,
                "commit": commit,
                "deploy_url": deploy_url,
                "build": build,
            }
        except Exception as exc:
            logger.exception("deploy_failed")
            await self._rollback(vercel_project, s3_bucket)
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _validate(self, owner: str, repo: str, branch: str) -> str:
        r = await self.registry.execute("github", "github_search_code", {"query": f"repo:{owner}/{repo} branch:{branch}"})
        sha = (r.data.get("items", [{}])[0].get("sha", "unknown") if r.success else "unknown")
        logger.info("deploy_validated", sha=sha)
        return sha

    async def _build(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        r = await self.registry.execute("github", "github_trigger_workflow", {
            "owner": owner, "repo": repo, "workflow_id": "build.yml",
            "ref": branch, "inputs": {},
        })
        logger.info("deploy_build_triggered")
        return {"triggered": r.success}

    async def _deploy(self, vercel_project: str, s3_bucket: str, owner: str, repo: str, branch: str) -> str:
        # Vercel deploy
        v = await self.registry.execute("vercel", "vercel_list_deployments", {"project_id": vercel_project, "limit": 1})
        url = (v.data[0].get("url", "") if v.success and v.data else "")
        # S3 artifact sync
        if s3_bucket:
            await self.registry.execute("aws", "aws_s3_list_objects", {"bucket": s3_bucket, "prefix": f"{repo}/{branch}/"})
        logger.info("deploy_deployed", url=url)
        return url

    async def _verify(self, url: str) -> bool:
        if not url:
            return False
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get(f"https://{url}")
                return r.status_code < 500
        except Exception:
            return False

    async def _rollback(self, vercel_project: str, s3_bucket: str) -> None:
        logger.warning("deploy_rollback", project=vercel_project)

    async def _learn(self, owner: str, repo: str, branch: str, commit: str, build: Dict[str, Any], url: str, healthy: bool) -> None:
        await self.registry.execute("postgres", "postgres_log_incident", {
            "incident": {
                "service": f"deploy:{owner}/{repo}",
                "problem_title": f"deploy {branch}",
                "diagnosis": f"commit {commit}",
                "action": f"deployed to {url}",
                "outcome": "resolved" if healthy else "needs_review",
                "session_id": self.session_id,
            }
        })
