"""GitLab adapter — async, URL-safe."""

from typing import Dict, Any, List, Optional
import httpx
from urllib.parse import quote
from cybernetics.adapters.base import MCPAdapter
from cybernetics.config.settings import settings
from cybernetics.circuit.breaker import circuit
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.adapters.gitlab")


class GitLabAdapter(MCPAdapter):
    name = "gitlab"
    description = "GitLab — issues, merge requests, CI/CD"

    def __init__(self):
        super().__init__()
        self.base_url = settings.gitlab_url.rstrip("/")
        self.project_id = quote(str(settings.gitlab_project_id), safe="")
        self.headers = {"PRIVATE-TOKEN": settings.gitlab_token}
        self.register_tool(
            "gitlab_create_issue",
            "Create an issue",
            {"title": {"type": "string"}, "description": {"type": "string"}, "labels": {"type": "array"}},
            ["title", "description"],
            self._create_issue,
        )
        self.register_tool(
            "gitlab_create_mr",
            "Create a merge request",
            {"title": {"type": "string"}, "source_branch": {"type": "string"}, "target_branch": {"type": "string"}, "description": {"type": "string"}},
            ["title", "source_branch", "target_branch"],
            self._create_mr,
        )
        self.register_tool(
            "gitlab_get_file",
            "Read a file from the repo",
            {"file_path": {"type": "string"}, "ref": {"type": "string"}},
            ["file_path"],
            self._get_file,
        )
        self.register_tool(
            "gitlab_trigger_pipeline",
            "Trigger a CI/CD pipeline",
            {"ref": {"type": "string"}, "variables": {"type": "object"}},
            ["ref"],
            self._trigger_pipeline,
        )

    @circuit("gitlab", failure_threshold=5, recovery_timeout=60)
    async def _create_issue(self, title: str, description: str, labels: List[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v4/projects/{self.project_id}/issues",
                headers=self.headers,
                json={"title": title, "description": description, "labels": labels or ["sentinel-auto"]},
            )
            resp.raise_for_status()
            return resp.json()

    @circuit("gitlab", failure_threshold=5, recovery_timeout=60)
    async def _create_mr(self, title: str, source_branch: str, target_branch: str, description: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v4/projects/{self.project_id}/merge_requests",
                headers=self.headers,
                json={"title": title, "source_branch": source_branch, "target_branch": target_branch, "description": description, "remove_source_branch": False},
            )
            resp.raise_for_status()
            return resp.json()

    @circuit("gitlab", failure_threshold=5, recovery_timeout=60)
    async def _get_file(self, file_path: str, ref: str = "main") -> Optional[str]:
        safe_path = quote(file_path, safe="/")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/api/v4/projects/{self.project_id}/repository/files/{safe_path}/raw",
                headers=self.headers, params={"ref": ref},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.text

    @circuit("gitlab", failure_threshold=5, recovery_timeout=60)
    async def _trigger_pipeline(self, ref: str = "main", variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/v4/projects/{self.project_id}/pipeline",
                headers=self.headers, json={"ref": ref, "variables": variables or {}},
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/v4/user", headers=self.headers)
                resp.raise_for_status()
            return {"status": "healthy"}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}
