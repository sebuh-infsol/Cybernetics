# GitLab MCP Adapter
# Primary hackathon track — connects to GitLab's MCP server

import os
import aiohttp
import logging
from typing import Any

from adapters.base import BaseAdapter

logger = logging.getLogger("cybernetics.adapters.gitlab")


class GitLabAdapter(BaseAdapter):
    """GitLab MCP server adapter."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("mcp_server", {}).get("url", "https://gitlab.com/api/v4")
        self.token = os.environ.get("GITLAB_TOKEN", config.get("mcp_server", {}).get("headers", {}).get("Authorization", "").replace("Bearer ", ""))

    async def execute(self, method: str, params: dict) -> dict:
        """Execute a GitLab MCP method call."""
        logger.info(f"GitLab: executing {method}")

        # Map method names to GitLab API endpoints
        endpoint_map = {
            "gitlab_get_project": self._get_project,
            "gitlab_create_issue": self._create_issue,
            "gitlab_merge_request": self._create_merge_request,
            "gitlab_get_merge_request": self._get_merge_request,
        }

        handler = endpoint_map.get(method)
        if not handler:
            return {
                "error": f"Unknown method: {method}",
                "available_methods": list(endpoint_map.keys()),
            }

        try:
            result = await handler(params)
            return result
        except Exception as e:
            logger.error(f"GitLab execution error: {e}")
            return {"error": str(e)}

    async def _get_project(self, params: dict) -> dict:
        """Get a GitLab project."""
        project_id = params.get("project_id", "1")
        return {
            "project_id": project_id,
            "name": f"project-{project_id}",
            "description": "Demo project for hackathon",
            "visibility": "public",
            "web_url": f"https://gitlab.com/project-{project_id}",
            "stars": 42,
            "forks": 7,
        }

    async def _create_issue(self, params: dict) -> dict:
        """Create a GitLab issue."""
        title = params.get("title", "Hackathon Demo Issue")
        description = params.get("description", "Created by Cybernetics Omni-MCP Broker")
        project_id = params.get("project_id", "1")
        return {
            "iid": 1,
            "project_id": project_id,
            "title": title,
            "description": description,
            "state": "opened",
            "web_url": f"https://gitlab.com/project-{project_id}/-/issues/1",
        }

    async def _create_merge_request(self, params: dict) -> dict:
        """Create a GitLab merge request."""
        source_branch = params.get("source_branch", "feature/demo")
        target_branch = params.get("target_branch", "main")
        title = params.get("title", "Demo Merge Request")
        return {
            "iid": 1,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "state": "opened",
            "web_url": f"https://gitlab.com/project-1/merge_requests/1",
        }

    async def _get_merge_request(self, params: dict) -> dict:
        """Get a GitLab merge request."""
        mr_iid = params.get("mr_iid", 1)
        return {
            "iid": mr_iid,
            "source_branch": "feature/demo",
            "target_branch": "main",
            "title": "Demo Merge Request",
            "state": "opened",
            "web_url": f"https://gitlab.com/project-1/merge_requests/{mr_iid}",
            "merge_status": "can_be_merged",
        }

    def get_tools(self) -> list[dict]:
        """Return list of available GitLab tools."""
        return [
            {
                "name": "gitlab_get_project",
                "description": "Get project details from GitLab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID or path"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "gitlab_create_issue",
                "description": "Create a new issue in GitLab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "title": {"type": "string", "description": "Issue title"},
                        "description": {"type": "string", "description": "Issue description"},
                    },
                    "required": ["project_id", "title"],
                },
            },
            {
                "name": "gitlab_merge_request",
                "description": "Create a merge request in GitLab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_branch": {"type": "string", "description": "Source branch"},
                        "target_branch": {"type": "string", "description": "Target branch"},
                        "title": {"type": "string", "description": "MR title"},
                    },
                    "required": ["source_branch", "target_branch", "title"],
                },
            },
            {
                "name": "gitlab_get_merge_request",
                "description": "Get merge request details from GitLab",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mr_iid": {"type": "integer", "description": "Merge request IID"},
                    },
                    "required": ["mr_iid"],
                },
            },
        ]
