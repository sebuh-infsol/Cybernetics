# GitHub Adapter — Implementation Summary

## Overview
Added a local GitHub REST API adapter to the Cybernetics Omni-MCP Broker, enabling the Google Cloud Agent (Gemini 3) to interact with GitHub repositories through the same unified MCP protocol used by the GitLab adapter.

## Files Created
- `broker/adapters/github_adapter.py` — Full adapter implementation (9,013 bytes)

## Files Modified
- `config.yaml` — Added GitHub partner entry with 4 tools and sentinel routing
- `registry/loader.py` — Added dynamic adapter auto-loading from `adapter:` config field
- `README.md` — Updated architecture diagram, partner table, demo steps, and project structure

## Adapter Design
The GitHub adapter follows the same pattern as the GitLab adapter but uses direct REST API calls instead of SSE MCP protocol:

```python
class GitHubAdapter:
    def __init__(self, token: Optional[str] = None)
    def _get(path, params) -> Dict  # GET requests to api.github.com
    def _post(path, data) -> Dict   # POST requests to api.github.com
    def get_repo(owner, repo) -> Dict
    def create_issue(owner, repo, title, body, labels) -> Dict
    def create_pr(owner, repo, title, head, base, body) -> Dict
    def list_prs(owner, repo, state, per_page) -> list
    def get_tools() -> list          # 4 tool definitions for MCP
    def resolve(tool_name, params) -> Dict  # Tool execution dispatcher
```

## Tools Implemented
| Tool | Method | Description |
|------|--------|-------------|
| `github_get_repo` | GET `/repos/{owner}/{repo}` | Get repo metadata (stars, forks, branches, URL) |
| `github_create_issue` | POST `/repos/{owner}/{repo}/issues` | Create an issue with optional labels |
| `github_create_pr` | POST `/repos/{owner}/{repo}/pulls` | Create a PR from head→base branch |
| `github_list_prs` | GET `/repos/{owner}/{repo}/pulls` | List PRs filtered by state (open/closed/all) |

## Configuration
Added to `config.yaml` under `partners.github`:
```yaml
github:
  name: "GitHub"
  enabled: true
  adapter: "github_adapter"
  tools:
    - "github_get_repo"
    - "github_create_issue"
    - "github_create_pr"
    - "github_list_prs"
  sentinels:
    - auditor
    - safety
    - cost
```

## How It Works
1. Broker loads `config.yaml` at startup
2. `RegistryLoader` detects `adapter: "github_adapter"` in the GitHub partner config
3. Dynamically imports `broker.adapters.github_adapter` and instantiates `GitHubAdapter()`
4. The adapter instance is stored on the `PartnerServer` object
5. When a tool call arrives (e.g., `github_get_repo`), the router resolves it to the GitHub server
6. `PartnerServer.forward()` detects the adapter and delegates to `adapter.resolve()`
7. The adapter executes the appropriate GitHub REST API call and returns a standardized response

## Authentication
Set `GITHUB_TOKEN` environment variable:
```bash
export GITHUB_TOKEN=ghp_your_personal_access_token
```

The token is passed in the `Authorization: Bearer <token>` header for all API calls.

## Testing
```python
from broker.adapters.github_adapter import GitHubAdapter
adapter = GitHubAdapter(token="ghp_your_token")
result = adapter.resolve("github_get_repo", {"owner": "sebuh-infsol", "repo": "infsol-website"})
print(result)
```

## Cost Estimates (in config.yaml)
| Tool | Estimated Cost |
|------|---------------|
| github_get_repo | $0.001 |
| github_create_issue | $0.002 |
| github_create_pr | $0.003 |
| github_list_prs | $0.001 |

## Architecture Diagram Update
The broker's partner layer now includes GitHub alongside GitLab:
```
┌─────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐
│ GitLab  │    │ GitHub   │   │ MongoDB  │   │ Elastic  │
│  MCP    │    │ Adapter  │   │  MCP     │   │  MCP     │
└─────────┘    └──────────┘   └──────────┘   └──────────┘
```

## Status
✅ Complete — ready for hackathon demo and Cloud Run deployment.
