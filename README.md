# Sentinel

> Google Cloud Rapid Agent Hackathon — June 11, 2026

**Sentinel** is a self-healing infrastructure agent that detects system anomalies, investigates root causes using contextual data, takes corrective action, and continuously evaluates its own performance to improve over time.

Built with **Gemini 3** and the **Google Cloud Agent Development Kit (ADK)**, Sentinel integrates six partner MCP servers into a single autonomous workflow: each partner carries a load-bearing role — no bolt-ons.

---

## What It Does

Sentinel operates as a closed-loop SRE agent:

1. **Detect** — Dynatrace monitors your services and fires alerts
2. **Investigate** — Elastic hybrid search surfaces logs, incidents, and runbooks
3. **Reason** — MongoDB persistent memory recalls past patterns and resolutions
4. **Act** — GitLab creates issues, opens merge requests, and triggers CI/CD pipelines
5. **Evaluate** — Arize traces every reasoning step and runs LLM-as-a-Judge self-evals
6. **Learn** — Fivetran ensures all telemetry is pipelined into BigQuery for long-term analysis

The agent does not just suggest fixes. It **ships them** and **verifies them**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Sentinel Agent (ADK)                    │
│  Gemini 3 → Planning → Tool Selection → Execution → Eval   │
└──────────────────┬────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┬──────────┐
    ▼              ▼              ▼              ▼          ▼
┌────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐  ┌────────┐
│Dynatrace│   │  Elastic │   │ MongoDB  │   │ GitLab │  │ Arize  │
│  MCP   │   │   MCP    │   │   MCP    │   │  MCP   │  │  MCP   │
└────────┘   └──────────┘   └──────────┘   └────────┘  └────────┘
    │              │              │              │           │
    ▼              ▼              ▼              ▼           ▼
 Alerts/     Logs/Incidents/  Memory/      Issues/    Traces/
 Metrics     Docs/Runbooks    State        MRs/CI     Evals
    │                                               ▲
    └───────────────────────────────────────────────┘
                          Fivetran MCP → BigQuery
                          (observability data warehouse)
```

---

## Partner Integrations

| Partner | Role | Why It Is Essential |
|---------|------|---------------------|
| **Dynatrace** | Detection | No anomalies, no agent. Provides real-time alerts, traces, and DQL queries |
| **Elastic** | Investigation | Hybrid semantic/keyword/vector search across logs, incidents, and documentation |
| **MongoDB** | Memory | Persistent incident history and learned remediation patterns; without it, the agent is amnesiac |
| **GitLab** | Action | Creates issues, opens MRs, reads configs, triggers CI/CD — the agent actually ships fixes |
| **Arize** | Cognition | Traces every reasoning step, runs LLM-as-a-Judge evals, queries its own history to self-correct |
| **Fivetran** | Foundation | Pipelines observability data into BigQuery so the agent always works with fresh telemetry |

---

## Tech Stack

- **Agent Framework:** Google ADK (Python)
- **LLM:** Gemini 3 via Vertex AI
- **Deployment:** Cloud Run
- **Data:** BigQuery
- **Observability:** OpenTelemetry → Arize Phoenix + Dynatrace

---

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud project with Vertex AI and Agent Builder enabled
- Partner accounts (free trials linked below)

### 1. Clone and install

```bash
git clone https://github.com/strawberr0/Cybernetics.git
cd Cybernetics
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your partner credentials:

```bash
cp .env.example .env
```

| Variable | Source |
|----------|--------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `DYNATRACE_API_TOKEN` | [Dynatrace Hub](https://www.dynatrace.com/hub/detail/dynatrace-mcp-server/) |
| `ELASTIC_API_KEY` | [Elastic Cloud](https://cloud.elastic.co) |
| `MONGODB_URI` | [MongoDB Atlas](https://www.mongodb.com/products/platform/atlas) |
| `GITLAB_TOKEN` | [GitLab Access Tokens](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) |
| `ARIZE_API_KEY` | [Arize Phoenix Cloud](https://app.phoenix.arize.com) |
| `FIVETRAN_API_KEY` | [Fivetran](https://fivetran.com/signup) |

### 3. Run the agent locally

```bash
python src/agent.py
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy sentinel-agent --source . --region us-central1
```

---

## Project Structure

```
.
├── src/
│   ├── agent.py              # ADK agent definition + workflow orchestration
│   ├── tools/
│   │   ├── dynatrace_tools.py
│   │   ├── elastic_tools.py
│   │   ├── mongodb_tools.py
│   │   ├── gitlab_tools.py
│   │   ├── arize_tools.py
│   │   └── fivetran_tools.py
│   ├── evals/
│   │   └── judge.py          # LLM-as-a-Judge evaluators
│   └── config.py
├── tests/
├── Dockerfile
├── cloudbuild.yaml
├── requirements.txt
├── .env.example
├── README.md
└── LICENSE
```

---

## Demo Scenario

A production service `trade-backend` suddenly shows a 5% error rate spike.

1. **Dynatrace** fires an alert
2. Sentinel queries traces — affected endpoint: `/api/positions`
3. Sentinel searches **Elastic** — finds 3 similar incidents in the last 30 days, all memory-related
4. Sentinel queries **MongoDB** — confirms this matches pattern #7 (position manager memory leak)
5. Sentinel reasons (traced in **Arize**) — diagnosis: bump memory limit, restart container
6. Sentinel calls **GitLab** — creates issue `#742`, opens MR bumping limit in `docker-compose.prod.yml`
7. Sentinel triggers CI/CD pipeline for staging deployment
8. Sentinel verifies via **Dynatrace** — error rate returns to baseline
9. Sentinel logs the resolution to **MongoDB** memory
10. **Arize** runs LLM-as-a-Judge — "Was the diagnosis correct?" → score: 0.94
11. **Fivetran** pipelines the full incident telemetry into BigQuery for future analysis

---

## Partner Resources

- [Arize Phoenix MCP Server](https://arize.com/docs/phoenix/integrations/phoenix-mcp-server)
- [Elastic Agent Builder MCP Server](https://www.elastic.co/docs/explore-analyze/ai-features/agent-builder/mcp-server)
- [MongoDB MCP Server](https://www.mongodb.com/docs/mcp-server/get-started/)
- [GitLab MCP Server](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/)
- [Fivetran MCP Server](https://github.com/fivetran/fivetran-mcp)
- [Dynatrace MCP Server](https://www.dynatrace.com/hub/detail/dynatrace-mcp-server/)

---

## License

MIT — see [LICENSE](LICENSE).
