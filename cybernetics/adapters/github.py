"""GitHub adapter — issues, PRs, actions, repos."""

import httpx
from typing import Dict, Any, List, Optional
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.github")


class GitHubAdapter(MCPAdapter):
    name = "github"
    description = "GitHub — issues, pull requests, actions, repositories"

    def __init__(self):
        super().__init__()
        self.base_url = settings.github_api_url.rstrip("/")
        self.headers = {"Authorization": f"token {settings.github_token}", "Accept": "application/vnd.github.v3+json"}
        self.register_tool("github_create_issue", "Create an issue", {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "labels": {"type": "array"}}, ["owner", "repo", "title"], self._create_issue)
        self.register_tool("github_get_issue", "Get an issue", {"owner": {"type": "string"}, "repo": {"type": "string"}, "issue_number": {"type": "integer"}}, ["owner", "repo", "issue_number"], self._get_issue)
        self.register_tool("github_create_pr", "Create a pull request", {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}, "head": {"type": "string"}, "base": {"type": "string"}, "body": {"type": "string"}}, ["owner", "repo", "title", "head", "base"], self._create_pr)
        self.register_tool("github_list_repos", "List repos for an org or user", {"owner": {"type": "string"}, "type": {"type": "string"}}, ["owner"], self._list_repos)
        self.register_tool("github_trigger_workflow", "Trigger a GitHub Actions workflow", {"owner": {"type": "string"}, "repo": {"type": "string"}, "workflow_id": {"type": "string"}, "ref": {"type": "string"}, "inputs": {"type": "object"}}, ["owner", "repo", "workflow_id", "ref"], self._trigger_workflow)
        self.register_tool("github_search_code", "Search code across GitHub", {"query": {"type": "string"}}, ["query"], self._search_code)

    @circuit("github", failure_threshold=5, recovery_timeout=60)
    async def _create_issue(self, owner: str, repo: str, title: str, body: str = "", labels: List[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/repos/{owner}/{repo}/issues", headers=self.headers, json={"title": title, "body": body, "labels": labels or []})
            resp.raise_for_status()
            return resp.json()

    @circuit("github", failure_threshold=5, recovery_timeout=60)
    async def _get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    @circuit("github", failure_threshold=5, recovery_timeout=60)
    async def _create_pr(self, owner: str, repo: str, title: str, head: str, base: str, body: str = "") -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/repos/{owner}/{repo}/pulls", headers=self.headers, json={"title": title, "head": head, "base": base, "body": body})
            resp.raise_for_status()
            return resp.json()

    @circuit("github", failure_threshold=5, recovery_timeout=60)
    async def _list_repos(self, owner: str, type_: str = "owner") -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/users/{owner}/repos", headers=self.headers, params={"type": type_})
            resp.raise_for_status()
            return resp.json()

    @circuit("github", failure_threshold=5, recovery_timeout=60)
    async def _trigger_workflow(self, owner: str, repo: str, workflow_id: str, ref: str, inputs: Optional[Dict[str, str]] = None) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches", headers=self.headers, json={"ref": ref, "inputs": inputs or {}})
            resp.raise_for_status()

    @circuit("github", failure_threshold=5, recovery_timeout=60)
    async def _search_code(self, query: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.base_url}/search/code", headers=self.headers, params={"q": query})
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/user", headers=self.headers)
                resp.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
