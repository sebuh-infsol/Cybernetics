"""
GitHub Adapter — wraps GitHub REST API as MCP-compatible tools.

Tools:
  github_get_repo     — Get repository info
  github_create_issue — Create an issue
  github_create_pr    — Create a pull request
  github_list_prs     — List pull requests
"""

import os
import json
import requests
from typing import Any, Dict, Optional


class GitHubAdapter:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: Dict) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, headers=self.headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository info."""
        return self._get(f"/repos/{owner}/{repo}")

    def create_issue(
        self, owner: str, repo: str, title: str, body: str, labels: Optional[list] = None
    ) -> Dict[str, Any]:
        """Create an issue."""
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        return self._post(f"/repos/{owner}/{repo}/issues", data)

    def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> Dict[str, Any]:
        """Create a pull request."""
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }
        return self._post(f"/repos/{owner}/{repo}/pulls", data)

    def list_prs(
        self, owner: str, repo: str, state: str = "open", per_page: int = 10
    ) -> list:
        """List pull requests."""
        return self._get(
            f"/repos/{owner}/{repo}/pulls",
            {"state": state, "per_page": per_page},
        )

    def get_tools(self) -> list:
        """Return tool definitions for MCP."""
        return [
            {
                "name": "github_get_repo",
                "description": "Get repository information including stats, branches, and settings",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "GitHub org or user"},
                        "repo": {"type": "string", "description": "Repository name"},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "github_create_issue",
                "description": "Create a new issue in a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional labels",
                        },
                    },
                    "required": ["owner", "repo", "title", "body"],
                },
            },
            {
                "name": "github_create_pr",
                "description": "Create a new pull request",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "head": {"type": "string", "description": "Source branch"},
                        "base": {
                            "type": "string",
                            "description": "Target branch (default: main)",
                        },
                        "body": {"type": "string"},
                    },
                    "required": ["owner", "repo", "title", "head"],
                },
            },
            {
                "name": "github_list_prs",
                "description": "List pull requests in a repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "default": "open",
                        },
                        "per_page": {
                            "type": "integer",
                            "default": 10,
                            "description": "Results per page",
                        },
                    },
                    "required": ["owner", "repo"],
                },
            },
        ]

    def resolve(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a tool call and return results."""
        try:
            if tool_name == "github_get_repo":
                result = self.get_repo(params["owner"], params["repo"])
                return {
                    "status": "success",
                    "data": {
                        "name": result.get("full_name"),
                        "description": result.get("description"),
                        "stars": result.get("stargazers_count"),
                        "forks": result.get("forks_count"),
                        "open_issues": result.get("open_issues_count"),
                        "default_branch": result.get("default_branch"),
                        "language": result.get("language"),
                        "url": result.get("html_url"),
                    },
                }

            elif tool_name == "github_create_issue":
                result = self.create_issue(
                    params["owner"],
                    params["repo"],
                    params["title"],
                    params["body"],
                    params.get("labels"),
                )
                return {
                    "status": "success",
                    "data": {
                        "issue_url": result.get("html_url"),
                        "number": result.get("number"),
                        "title": result.get("title"),
                        "state": result.get("state"),
                    },
                }

            elif tool_name == "github_create_pr":
                result = self.create_pr(
                    params["owner"],
                    params["repo"],
                    params["title"],
                    params["head"],
                    params.get("base", "main"),
                    params.get("body", ""),
                )
                return {
                    "status": "success",
                    "data": {
                        "pr_url": result.get("html_url"),
                        "number": result.get("number"),
                        "title": result.get("title"),
                        "state": result.get("state"),
                    },
                }

            elif tool_name == "github_list_prs":
                result = self.list_prs(
                    params["owner"],
                    params["repo"],
                    params.get("state", "open"),
                    params.get("per_page", 10),
                )
                return {
                    "status": "success",
                    "data": [
                        {
                            "title": pr.get("title"),
                            "number": pr.get("number"),
                            "state": pr.get("state"),
                            "url": pr.get("html_url"),
                            "author": pr.get("user", {}).get("login"),
                        }
                        for pr in result
                    ],
                }

            else:
                return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        except requests.exceptions.HTTPError as e:
            return {"status": "error", "message": f"GitHub API error: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {e}"}
