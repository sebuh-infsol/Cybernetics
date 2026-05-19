"""GitLab MCP tools — issue creation, merge requests, and CI/CD triggers."""

import httpx
from typing import Dict, Any, Optional
from src.config import Config

class GitLabClient:
    def __init__(self):
        self.base_url = Config.GITLAB_URL.rstrip("/")
        self.project_id = Config.GITLAB_PROJECT_ID
        self.headers = {"PRIVATE-TOKEN": Config.GITLAB_TOKEN}

    async def create_issue(self, title: str, description: str, labels: list[str] = None) -> Dict[str, Any]:
        """Create an issue in the configured project."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v4/projects/{self.project_id}/issues",
                headers=self.headers,
                json={"title": title, "description": description, "labels": labels or ["sentinel-auto"]},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_merge_request(self, title: str, source_branch: str, target_branch: str, description: str) -> Dict[str, Any]:
        """Open an MR with the proposed fix."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v4/projects/{self.project_id}/merge_requests",
                headers=self.headers,
                json={
                    "title": title,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                    "description": description,
                    "remove_source_branch": False,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_file_contents(self, file_path: str, ref: str = "main") -> Optional[str]:
        """Read a file from the repository."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v4/projects/{self.project_id}/repository/files/{file_path}/raw",
                headers=self.headers,
                params={"ref": ref},
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.text

    async def trigger_pipeline(self, ref: str = "main", variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Trigger a CI/CD pipeline."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v4/projects/{self.project_id}/pipeline",
                headers=self.headers,
                json={"ref": ref, "variables": variables or {}},
            )
            resp.raise_for_status()
            return resp.json()
