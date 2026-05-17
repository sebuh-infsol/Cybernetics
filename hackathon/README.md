# Cybernetics — Omni-MCP Broker

**Google Cloud Rapid Agent Hackathon Entry** — A composable, multi-track MCP Broker that acts as a unified gateway for Google Cloud Agents (Gemini 3) to dynamically connect to multiple partner MCP servers with layered governance.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Google Cloud Agent Builder              │
│              (Gemini 3 Pro via SSE endpoint)             │
└──────────────────────┬──────────────────────────────────┘
                       │  MCP SSE Protocol
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Omni-MCP Broker (FastAPI)               │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Router   │  │ Registry │  │ Sentinel Middleware  │  │
│  │          │→ │          │  │  ┌────────────────┐  │  │
│  │          │  │          │  │  │ Auditor        │  │  │
│  │          │←─┤          │  │  │ SafetyGuard    │  │  │
│  │          │  │          │  │  │ CostEstimator  │  │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┬───────────────┐
       ▼               ▼               ▼               ▼
  ┌─────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ GitLab  │    │ GitHub   │   │ MongoDB  │   │ Elastic  │
  │  MCP    │    │ Adapter  │   │  MCP     │   │  MCP     │
  └─────────┘    └──────────┘   └──────────┘   └──────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r hackathon/requirements.txt

# Configure partner MCP endpoints
cp hackathon/config.example.yaml hackathon/config.yaml
# Edit config.yaml with your API keys

# Start the broker
cd hackathon
python -m broker.server

# The broker exposes:
#   MCP SSE endpoint:     http://localhost:8000/mcp/sse
#   MCP JSON-RPC:         http://localhost:8000/mcp
#   Health check:         http://localhost:8000/health
#   Registry status:      http://localhost:8000/registry/status
#   Available tools:      http://localhost:8000/tools
```

## Partner Tracks

| Track | MCP Server | Status |
|-------|-----------|--------|
| **GitLab** | GitLab MCP Server | ✅ Primary |
| **GitHub** | GitHub REST API Adapter | ✅ Primary |
| MongoDB | MongoDB MCP Server | 🔄 Pluggable |
| Elastic | Elastic MCP Server | 🔄 Pluggable |
| Arize | Arize MCP Server | 🔄 Pluggable |
| Fivetran | Fivetran MCP Server | 🔄 Pluggable |
| Dynatrace | Dynatrace MCP Server | 🔄 Pluggable |

## Hackathon Requirements

- ✅ Built using **Gemini 3** (Agent Builder SSE endpoint)
- ✅ Uses **Google Cloud Agent Builder**
- ✅ Integrates **partner MCP servers** (GitLab primary, GitHub adapter, others pluggable)
- ✅ Multi-track composable architecture
- ✅ Governance/sentinel layer for tool call auditing

## Project Structure

```
hackathon/
├── broker/              # FastAPI MCP broker server
│   ├── __init__.py      # FastAPI app entry point
│   ├── server.py        # MCP SSE/JSON-RPC server
│   └── router.py        # MCP request router
├── registry/            # Dynamic MCP server registry
│   └── loader.py        # YAML/JSON config loader
├── sentinels/           # Governance middleware
│   ├── auditor.py       # Tool call auditor
│   ├── safety.py        # Safety guard
│   └── cost.py          # Cost estimator
├── adapters/            # Partner MCP adapters
│   ├── gitlab.py        # GitLab MCP adapter
│   ├── github_adapter.py # GitHub REST API adapter
│   └── base.py          # Base adapter class
├── google-cloud/        # Google Cloud Agent Builder config
│   └── agent-config.json
├── config.yaml          # Partner MCP configurations
├── requirements.txt     # Python dependencies
└── README.md
```

## Demo Scenario

1. Start the broker: `python -m broker.server`
2. Query tools: `curl http://localhost:8000/tools`
3. Test GitLab integration: `curl -X POST http://localhost:8000/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"gitlab_get_project","params":{"project_id":"1"},"id":1}'`
4. Test GitHub integration: `curl -X POST http://localhost:8000/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"github_get_repo","params":{"owner":"strawberr0","repo":"Cybernetics"},"id":2}'`
5. Check audit log: `cat logs/audit.jsonl`

### Full Demo

Run the automated demo that walks through the complete flow:

```bash
python3 demo.py
```

The demo covers:
1. Broker health check
2. Available tools listing
3. Registered partner servers
4. End-to-end GitLab issue creation via the broker
5. GitHub repository query via the broker
6. Multi-track routing architecture overview

## Google Cloud

- **Project ID:** `strawberry-fields-496517`
- **Region:** `us-central1`
- **Agent Builder:** https://agentbuilder.cloud.google.com

## License

MIT
