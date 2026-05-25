<div align="center">

<!-- Cybernetics Banner: see assets/banner.svg -->

</div>

<p align="center">
  <strong>Composable Meta-MCP for Google Cloud Agents</strong><br/>
  <sub>v0.1.1  •  20 Adapters  •  80+ Tools  •  Agent Composer  •  A2A/ERC-8004 Ready</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-production--ready-emerald?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxNiAxNiI+PGNpcmNsZSBjeD0iOCIgY3k9IjgiIHI9IjgiIGZpbGw9IiMxMGI5ODEiLz48L3N2Zz4=" alt="Status"/>
  <img src="https://img.shields.io/badge/Go-1.22-blue?style=flat-square&logo=go&logoColor=white" alt="Go"/>
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/React-19-blue?style=flat-square&logo=react&logoColor=white" alt="React"/>
  <img src="https://img.shields.io/badge/TypeScript-strict-blue?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/license-Apache%202.0-slate?style=flat-square" alt="License"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/MCP-2024--11--05-green?style=flat-square" alt="MCP"/>
  <img src="https://img.shields.io/badge/A2A-compatible-green?style=flat-square" alt="A2A"/>
  <img src="https://img.shields.io/badge/ERC--8004-compatible-green?style=flat-square" alt="ERC-8004"/>
  <img src="https://img.shields.io/badge/Google%20Cloud-Run-orange?style=flat-square&logo=google-cloud&logoColor=white" alt="Google Cloud"/>
  <img src="https://img.shields.io/badge/Gemini-3.x-orange?style=flat-square&logo=google&logoColor=white" alt="Gemini"/>
</p>

---

**Classification:** UNCLASSIFIED / OPEN SOURCE  
**Authors:** plasmaraygun, GoryGrey, royhodge812, sebuh-infsol  (strawberr0)  
**Version:** 0.1.1  
**Status:** Production-Ready  

---

## 1. Executive Summary

Cybernetics is a **composable Model Context Protocol (MCP) meta-broker** designed for Google Cloud enterprise environments. It aggregates 13+ third-party MCP servers into a unified, authenticated, auditable control plane and exposes composable **agent templates** that execute multi-phase autonomous workflows on top of that plane.

### Key Differentiators
- **Zero Trust by default** — every request authenticated, no anonymous endpoints beyond health probes
- **Defense in depth** — circuit breakers, input sanitization, sentinel middleware, structured logging
- **Multi-tenant ready** — per-adapter isolation, API-key scoping, audit trails
- **Operational hardening** — non-root containers, Cloud IAM binding, Secret Manager injection, VPC-SC compatible

---

## 2. Threat Model & Security Posture

| Threat | Mitigation | Verification |
|---|---|---|
| Secret exfiltration from Docker image | Multi-stage build; `.env` excluded; secrets via `--set-secrets` | `docker inspect` shows no `Env` secrets |
| Unauthorized broker access | `--no-allow-unauthenticated` + Identity-Aware Proxy (IAP) | `gcloud run services describe` |
| Timing attacks on API key | `hmac.compare_digest` + random delay on mismatch | Static analysis via `bandit` |
| DQL / SQL injection | Regex allow-list sanitization (`_sanitize_dql`) + parameterized queries | Unit test `test_dql_sanitization` |
| SSRF via adapter callbacks | URL prefix validation, no redirects, `httpx` timeout caps | Respx mock tests |
| ReDoS in regex filters | Bounded regex (`^...$`), no `.*` backtracking | Code review |
| Credential leakage in logs | `Guard` sentinel blocks keys named `password`, `secret`, `token` | `test_guard_blocks_sensitive` |
| Supply-chain compromise | Pinned hashes in `requirements.txt`; `pip-audit` in CI | SBOM generation in build |
| Async blocking I/O | All network clients use `httpx.AsyncClient`, `AsyncIOMotorClient`, `AsyncElasticsearch`, `asyncpg` | `pytest-asyncio` coverage |

### Compliance Mapping
- **NIST 800-53:** AC-3 (access enforcement), AU-6 (audit review), SC-28 (encryption at rest via Cloud SQL)
- **FedRAMP Moderate:** Covered via Cloud Run + Cloud SQL + Secret Manager
- **SOC 2 Type II:** Audit logs in Cloud Logging; structured JSON format

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Google Cloud (VPC-SC)                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │ Cloud Run   │◄──►│  Cloud SQL  │◄──►│ Secret Manager  │  │
│  │ (Broker)    │    │  (Postgres) │    │                 │  │
│  └──────┬──────┘    └─────────────┘    └─────────────────┘  │
│         │                                                    │
│  ┌──────┴──────────────────────────────────────────────┐   │
│  │                  Cybernetics Broker                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │   │
│  │  │ Auth MW  │  │ Registry │  │Circuits  │  │Health  │  │   │
│  │  │ (Bearer) │  │ (Adapters│  │(CBs)     │  │Probes  │  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘  │   │
│  │  ┌────────────────────────────────────────────────────┐ │   │
│  │  │            Agent Template Engine                    │ │   │
│  │  │  Sentinel  │  DeployAgent │ FinanceAgent │ InfraAgent │ │   │
│  │  └────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                      │
│  ┌──────┴──────────────────────────────────────────────┐      │
│  │                  MCP Adapter Layer                   │      │
│  │  Dynatrace  Elastic  Postgres  GitLab  Arize  Fivetran │      │
│  │  GitHub     Stripe   AWS       Vercel  Supabase     │      │
│  │  Cloudflare Browser (Playwright CDP)                 │      │
│  └──────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
         │
    ┌────┴──────────────────────────────────────┐
    │            Google ADK / Vertex AI          │
    │   (Agent orchestration, LLM-as-a-Judge)   │
    └───────────────────────────────────────────┘
```

### Data Flow
1. **Request** → Cloud Run → `APIKeyAuth` middleware validates Bearer token
2. **Routing** → FastAPI dispatches to `/mcp/invoke`, `/mcp/tools`, or `/mcp/sse`
3. **Sentinel Pipeline** → `Auditor.before()` logs call, `Guard.before()` blocks sensitive keys
4. **Registry** → Loads adapter from `ADAPTER_MAP`, executes tool via circuit breaker
5. **Adapter** → Async HTTP/SQL client calls downstream MCP server
6. **Response** → `Auditor.after()` logs result, circuit breaker state updated

---

## 4. Cybernetics MCP Server — Usage Guide

Cybernetics is a **first-class MCP server** that exposes its adapters and agent templates as tools over the Model Context Protocol. Any MCP client (Claude Desktop, Cursor, Windsurf, etc.) can connect to it.

### 4.1 What Is the Cybernetics MCP Server?

The Cybernetics MCP server is a single stdio-based MCP peer that aggregates all configured adapters into one unified tool namespace. Instead of installing 20 separate MCP servers, you install **one**:

```json
{
  "mcpServers": {
    "cybernetics": {
      "command": "python",
      "args": ["-m", "cybernetics.mcp"],
      "env": {
        "BROKER_API_KEY": "your-broker-key",
        "POSTGRES_DSN": "postgresql+asyncpg://user:pass@localhost/sentinel"
      }
    }
  }
}
```

Once connected, your MCP client sees **all tools** from **all enabled adapters** as a flat list:

| Tool | What it does |
|---|---|
| `dynatrace_get_problems` | Fetch active problems from Dynatrace |
| `github_create_issue` | Create a GitHub issue |
| `slack_post_message` | Post to a Slack channel |
| `browser_screenshot` | Take a browser screenshot via CDP |
| `sentinel_run` | Execute the full Sentinel agent workflow |
| `deploy_trigger_pipeline` | Trigger a GitLab CI/CD pipeline |

### 4.2 How It Works

```
┌─────────────┐      stdio       ┌──────────────────────────────────────────┐
│   Claude    │ ◄──────────────► │  Cybernetics MCP Server                  │
│   Desktop   │   JSON-RPC 2.0   │  ┌─────────────┐  ┌──────────────────┐  │
└─────────────┘                  │  │  Registry   │  │  Dynatrace       │  │
                                 │  │  (loads    │──►│  GitHub          │  │
                                 │  │  adapters) │  │  Slack           │  │
                                 │  └─────────────┘  │  Browser...      │  │
                                 │                   └──────────────────┘  │
                                 └───────────────────────────────────────────┘
```

**You do not configure each adapter individually.** Adapters are loaded from the Cybernetics broker's registry based on the environment variables already set on the host.

### 4.3 Required Environment (Preset by Ops)

These are **connection settings** that your platform team configures once:

| Variable | Purpose | Example |
|---|---|---|
| `POSTGRES_DSN` | Database connection | `postgresql+asyncpg://...` |
| `DYNATRACE_BASE_URL` | Dynatrace tenant URL | `https://xyz.live.dynatrace.com` |
| `ELASTIC_CLOUD_ID` | Elastic Cloud deployment ID | `my-deployment:ZXUta2...` |
| `GITLAB_URL` | GitLab instance | `https://gitlab.com` |
| `ARIZE_ENDPOINT` | Arize Phoenix URL | `https://app.phoenix.arize.com` |
| `DATADOG_SITE` | Datadog region | `datadoghq.com` |
| `BROWSER_CDP_HOST` | Browser CDP host | `localhost` |
| `BROWSER_CDP_PORT` | Browser CDP port | `9222` |

### 4.4 Secret Keys (Injected per User / Team)

These are the **only** values users typically need to provide:

| Variable | Adapter | Where to get it |
|---|---|---|
| `BROKER_API_KEY` | Cybernetics | Your admin issues this |
| `DYNATRACE_API_TOKEN` | Dynatrace | Settings → Access tokens |
| `ELASTIC_API_KEY` | Elastic | Stack Management → API Keys |
| `GITLAB_TOKEN` | GitLab | User Settings → Access Tokens |
| `GITHUB_TOKEN` | GitHub | Settings → Developer settings → PAT |
| `SLACK_BOT_TOKEN` | Slack | api.slack.com/apps → OAuth & Permissions |
| `DATADOG_API_KEY` / `APP_KEY` | Datadog | Organization Settings → API Keys |
| `NOTION_TOKEN` | Notion | notion.so/my-integrations |
| `LINEAR_API_KEY` | Linear | Settings → API |

### 4.5 Example: Using Cybernetics from Claude Desktop

**Step 1:** Install the Cybernetics MCP package:

```bash
pip install cybernetics-mcp
```

**Step 2:** Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cybernetics": {
      "command": "cybernetics-mcp",
      "env": {
        "BROKER_API_KEY": "your-key",
        "POSTGRES_DSN": "postgresql+asyncpg://user:pass@localhost/sentinel",
        "DYNATRACE_BASE_URL": "https://xyz.live.dynatrace.com",
        "DYNATRACE_API_TOKEN": "dt0c01.xxx"
      }
    }
  }
}
```

**Step 3:** Ask Claude to use it:

> "Check Dynatrace for active problems on the api service, then post a summary to Slack #incidents"

Claude will:
1. Call `tools/list` and see `dynatrace_get_problems` + `slack_post_message`
2. Call `dynatrace_get_problems` with `{ "service": "api" }`
3. Call `slack_post_message` with the results

### 4.6 Example: Using Cybernetics from Cursor

Cursor supports MCP servers via `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "cybernetics": {
      "command": "cybernetics-mcp",
      "env": { "BROKER_API_KEY": "...", "POSTGRES_DSN": "..." }
    }
  }
}
```

In Cursor's chat, type `@cybernetics` and ask:

> "Run the sentinel agent to check for production issues"

Cursor will invoke `sentinel_run` and stream the multi-phase results.

### 4.7 Protocol Details

Implements MCP protocol `2024-11-05` over stdio (JSON-RPC 2.0):

| Method | Purpose |
|---|---|
| `initialize` | Handshake + capability exchange |
| `tools/list` | Discover all tools from all adapters |
| `tools/call` | Invoke any tool by `adapter_tool` name |

Tool names are namespaced: `dynatrace_get_problems`, `github_create_issue`, `browser_screenshot`, etc.

---

## 5. Adapter Catalog (20 Adapters, 80+ Tools)

| Adapter | Protocol | Auth | Circuit | Tools (complete) |
|---|---|---|---|---|
| `dynatrace` | REST | `Api-Token` | dynatrace | `dynatrace_get_problems`, `dynatrace_get_traces`, `dynatrace_run_dql` |
| `elastic` | REST | `ApiKey` | elastic | `elastic_search_incidents`, `elastic_search_runbooks`, `elastic_write_insight` |
| `postgres` | TCP | DSN | postgres | `postgres_recall_pattern`, `postgres_store_pattern`, `postgres_log_incident` |
| `gitlab` | REST | `PRIVATE-TOKEN` | gitlab | `gitlab_create_issue`, `gitlab_create_mr`, `gitlab_get_file`, `gitlab_trigger_pipeline` |
| `arize` | REST | `Bearer` | arize | `arize_run_judge` (Gemini), `arize_log_eval` |
| `fivetran` | REST | Basic | fivetran | `fivetran_list_connectors`, `fivetran_get_status`, `fivetran_sync`, `fivetran_create_pipeline` |
| `github` | REST | `token` | github | `github_create_issue`, `github_create_pr`, `github_list_repos`, `github_trigger_workflow`, `github_search_code` |
| `stripe` | REST | `Bearer` | stripe | `stripe_create_customer`, `stripe_get_customer`, `stripe_create_charge`, `stripe_list_invoices`, `stripe_create_subscription` |
| `aws` | boto3 | IAM / keys | aws | `aws_s3_list_buckets`, `aws_ec2_describe`, `aws_lambda_invoke`, `aws_cloudwatch_metrics` |
| `vercel` | REST | `Bearer` | vercel | `vercel_list_projects`, `vercel_get_deployment`, `vercel_list_deployments`, `vercel_add_env_var` |
| `supabase` | REST | `apikey` | supabase | `supabase_select`, `supabase_insert`, `supabase_update`, `supabase_delete`, `supabase_rpc` |
| `cloudflare` | REST | `Bearer` | cloudflare | `cloudflare_list_zones`, `cloudflare_list_dns`, `cloudflare_create_dns`, `cloudflare_list_workers`, `cloudflare_deploy_worker` |
| `browser` | WebSocket CDP | N/A | browser | `browser_navigate`, `browser_evaluate`, `browser_screenshot`, `browser_get_network`, `browser_get_console`, `browser_clear_cache` |
| `chrome` | WebSocket CDP | N/A | chrome | `chrome_navigate`, `chrome_evaluate`, `chrome_screenshot`, `chrome_get_network`, `chrome_get_console`, `chrome_clear_cache`, `chrome_set_viewport`, `chrome_click`, `chrome_type`, `chrome_pdf` |
| `firefox` | Playwright | N/A | firefox | `firefox_navigate`, `firefox_evaluate`, `firefox_screenshot`, `firefox_get_console`, `firefox_click`, `firefox_type`, `firefox_set_viewport`, `firefox_pdf` |
| `brave` | Playwright | N/A | brave | `brave_navigate`, `brave_evaluate`, `brave_screenshot`, `brave_click`, `brave_type`, `brave_set_viewport`, `brave_pdf`, `brave_check_shields` |
| `slack` | REST | `Bearer` | slack | `slack_post_message`, `slack_get_channel_history`, `slack_list_channels`, `slack_search_messages`, `slack_upload_file`, `slack_get_user_info` |
| `kubernetes` | HTTP / kubeconfig | Token | kubernetes | `k8s_list_pods`, `k8s_get_pod_logs`, `k8s_describe_pod`, `k8s_scale_deployment`, `k8s_restart_deployment`, `k8s_list_deployments`, `k8s_list_services`, `k8s_exec_command` |
| `datadog` | REST | `DD-API-Key` | datadog | `datadog_query_metrics`, `datadog_list_monitors`, `datadog_get_monitor`, `datadog_mute_monitor`, `datadog_list_incidents`, `datadog_search_logs`, `datadog_post_event` |
| `notion` | REST | `Bearer` | notion | `notion_search`, `notion_get_page`, `notion_create_page`, `notion_query_database`, `notion_update_page`, `notion_get_database` |
| `linear` | GraphQL | `Bearer` | linear | `linear_create_issue`, `linear_list_issues`, `linear_update_issue`, `linear_get_teams`, `linear_search_issues`, `linear_create_comment` |

---

## 6. Agent Templates

### 6.1 Sentinel — Self-Healing SRE
**Adapters:** dynatrace, elastic, postgres, gitlab, arize, fivetran  
**Phases:**
1. **Detect** — Fetch active problems from Dynatrace
2. **Investigate** — Hybrid search incidents + runbooks in Elastic
3. **Reason** — Recall pattern from Postgres; if unknown, generate diagnosis
4. **Act** — Create GitLab issue with auto-labels
5. **Verify** — Poll Dynatrace traces with exponential backoff until error rate < 1%
6. **Evaluate** — Gemini LLM-as-a-Judge scores diagnosis/action quality
7. **Learn** — Upsert pattern + log incident to Postgres; trigger Fivetran sync

### 6.2 DeployAgent — CI/CD Orchestrator
**Adapters:** github, vercel, aws, postgres  
**Phases:**
1. **Validate** — Verify latest commit on branch
2. **Build** — Trigger GitHub Actions workflow
3. **Deploy** — Vercel deployment + S3 artifact sync
4. **Verify** — Smoke test deployed URL via `httpx`
5. **Learn** — Log deployment outcome to Postgres

### 6.3 FinanceAgent — Payment Anomaly Detection
**Adapters:** stripe, supabase, postgres  
**Phases:**
1. **Detect** — Flag invoices > $1,000 or duplicate charges in 24h window
2. **Investigate** — Pull customer tier/history from Supabase
3. **Reason** — Tier-based decision: flag_for_review / partial_refund / notify
4. **Act** — Execute Stripe refund or insert review ticket
5. **Learn** — Store pattern + log incident

### 6.4 InfraAgent — Infrastructure Optimization
**Adapters:** dynatrace, cloudflare, aws, postgres  
**Phases:**
1. **Detect** — Dynatrace latency spikes on service
2. **Investigate** — DNS records (Cloudflare) + EC2 instances (AWS)
3. **Reason** — Under-provisioned? Deploy CF Worker cache? Scale EC2?
4. **Act** — Deploy Worker script or scale compute
5. **Verify** — Poll Dynatrace traces until error rate < 1%
6. **Learn** — Store remediation pattern

### 6.5 SecurityAgent — Vulnerability & Secret Scanning
**Adapters:** github, slack, postgres, cloudflare, datadog  
**Phases:**
1. **Scan** — Dependency checks + secret detection in GitHub repos
2. **Assess** — Severity scoring (critical/high/medium/low)
3. **Triage** — Slack alerts for critical findings
4. **Remediate** — Auto-fix low-severity, ticket rest
5. **Verify** — Re-scan to confirm remediation
6. **Learn** — Store scan patterns in Postgres

### 6.6 DataAgent — ETL Pipeline Orchestration
**Adapters:** postgres, supabase, fivetran, slack  
**Phases:**
1. **Extract** — Pull from Supabase tables
2. **Validate** — Quality scoring (nulls, duplicates)
3. **Transform** — Deduplicate, normalize
4. **Load** — Upsert into Postgres destination
5. **Monitor** — Slack notification on completion
6. **Learn** — Store pipeline patterns

### 6.7 OpsAgent — General DevOps Orchestration
**Adapters:** datadog, slack, kubernetes, github, linear, postgres  
**Phases:**
1. **Observe** — Datadog metrics + Kubernetes pod status
2. **Diagnose** — Crash loop? Memory pressure? Latency spike?
3. **Act** — Restart deployment, scale replicas, create Linear ticket
4. **Notify** — Slack #ops-alerts with diagnosis + actions
5. **Learn** — Store remediation patterns in Postgres

---

## 7. Deployment

### 7.1 Local Development

```bash
# 1. Clone
gh repo clone strawberr0/cybernetics
cd cybernetics

# 2. Create local secrets (never commit .env)
cp .env.example .env.local
# Edit .env.local with your keys

# 3. Install + run
pip install -e ".[dev]"
export $(cat .env.local | xargs)
python -m uvicorn cybernetics.broker.server:app --host 0.0.0.0 --port 8080
```

### 7.2 GCP Production (Cloud Run)

Prerequisites:
- GCP project with Cloud Run, Cloud SQL (Postgres 15+), Secret Manager enabled
- Service account with `roles/cloudsql.client`, `roles/secretmanager.secretAccessor`

```bash
# 1. Create secrets
gcloud secrets create broker-api-key --data-file=<(openssl rand -hex 32)
gcloud secrets create gemini-api-key --data-file=<(echo -n YOUR_GEMINI_KEY)
gcloud secrets create postgres-dsn --data-file=<(echo -n "postgresql+asyncpg://user@/sentinel?host=/cloudsql/PROJECT:REGION:INSTANCE")

# 2. Build & deploy
gcloud builds submit --config cloudbuild.yaml

# 3. Verify
gcloud run services describe cybernetics-broker --region=us-central1
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://<URL>/health
```

### 7.3 Cloud SQL Migration

```bash
# Apply schema
psql "host=/cloudsql/PROJECT:REGION:INSTANCE dbname=sentinel user=postgres" \
  -f migrations/001_init.sql
```

### 7.4 Hardening Checklist

- [ ] Cloud Run `--no-allow-unauthenticated` enforced
- [ ] Cloud Armor WAF configured in front of Cloud Run
- [ ] VPC-SC perimeter restricts egress to approved APIs only
- [ ] Cloud SQL private IP + IAM database authentication
- [ ] Secret Manager rotation policy (90 days)
- [ ] Cloud Audit Logs enabled for `data_access`, `admin_activity`
- [ ] `pip-audit` run in CI pipeline before container build
- [ ] Container scanning via Artifact Registry + Container Analysis
- [ ] DDoS protection via Cloud Armor rate limiting

---

## 8. Operations

### 8.1 Health & Readiness

```bash
# Liveness
curl -H "Authorization: Bearer $API_KEY" https://<URL>/health

# Tool discovery
curl -H "Authorization: Bearer $API_KEY" https://<URL>/mcp/tools

# Circuit breaker status
curl -H "Authorization: Bearer $API_KEY" https://<URL>/mcp/circuits

# SSE health stream
curl -H "Authorization: Bearer $API_KEY" https://<URL>/mcp/sse
```

### 8.2 Structured Logging

All logs are JSON, emitted to `stdout`, captured by Cloud Logging:

```json
{
  "timestamp": "2026-05-19T14:32:01Z",
  "level": "info",
  "event": "tool_executed",
  "adapter": "dynatrace",
  "tool": "dynatrace_get_problems",
  "latency_ms": 145,
  "session_id": "a1b2c3...",
  "correlation_id": "req-xyz"
}
```

### 8.3 Runbook: Adapter Circuit Open

```bash
# 1. Diagnose
curl -H "Authorization: Bearer $API_KEY" https://<URL>/mcp/circuits
# → {"circuits": {"dynatrace": "OPEN"}}

# 2. Inspect Cloud Logging for failure reason
gcloud logging read "jsonPayload.breaker=dynatrace AND severity>=ERROR" --limit=10

# 3. Manual reset (if operator-verified)
# Restart Cloud Run revision to reset breaker state
gcloud run services update cybernetics-broker --region=us-central1
```

---

## 9. Testing

```bash
# Unit tests
pytest tests/ -v

# Coverage gate
pytest tests/ --cov=cybernetics --cov-fail-under=80

# Security scan
pip-audit --requirement requirements.txt
bandit -r cybernetics/

# Container scan (after build)
gcloud artifacts docker images scan us-central1-docker.pkg.dev/PROJECT/cybernetics/broker:latest
```

---

## 10. Google ADK Integration

```python
from cybernetics.adk.bridge import cybernetics_adk_agent
from google.adk.runners import Runner

runner = Runner(agent=cybernetics_adk_agent)
for event in runner.run("Deploy my-app to production"):
    print(event)
```

---

## 11. Agent Composer

A React + TypeScript web UI and Go backend for composing and deploying custom agents.

```bash
# Start the composer backend
go run cmd/composer/main.go

# Start the frontend
cd frontend && npm install && npm run dev
```

**Workflow:**
1. **Pick Template** — Choose from 10 agent templates (Sentinel, Deploy, Finance, Infra, Security, Data, Ops, Content, Commerce, Analytics)
2. **Select Adapters** — Toggle any of the 20 MCP adapters
3. **Configure Keys** — Enter API keys for selected adapters
4. **Compose** — Gemini generates a custom Python agent class
5. **Deploy** — One-click deploy to Google Cloud Run

**API Endpoints:**

| Endpoint | Method | Description |
|---|---|---|
| `/api/templates` | GET | List all 10 templates + 20 adapters |
| `/api/compose` | POST | Generate agent code via Gemini |
| `/api/deploy` | POST | Return Cloud Run deployment command |

**Example compose request:**

```bash
curl -X POST http://localhost:3001/api/compose \
  -H "Content-Type: application/json" \
  -d '{
    "template": "sentinel",
    "adapters": ["dynatrace", "slack", "datadog"],
    "env_vars": {"DYNATRACE_API_TOKEN": "xxx", "SLACK_BOT_TOKEN": "xoxb-xxx"},
    "prompt": "Add a custom phase that posts a daily digest to Slack"
  }'
```

---

## 12. Google ADK A2A, A2P & ERC-8004 Integration

Cybernetics agents implement Google's **Agent-to-Agent (A2A)** and **Agent-to-Protocol (A2P)** patterns for cross-agent interoperability.

### 12.1 A2A — Agent-to-Agent

Agents register capabilities in a shared `A2ARegistry`. Other agents can discover and invoke those capabilities dynamically.

```python
from cybernetics.a2a.hooks import A2ACapability, get_a2a_registry

cap = A2ACapability(
    id="sentinel_detect",
    name="Sentinel Problem Detection",
    description="Fetch active Dynatrace problems for a service",
    input_schema={"service": {"type": "string"}},
    output_schema={"problems": {"type": "array"}},
)
get_a2a_registry().register_capability(cap)
```

### 12.2 A2P — Agent-to-Protocol

Agents can subscribe to or emit protocol events for decoupled coordination.

```python
from cybernetics.a2a.hooks import A2PProtocol, get_a2a_registry

proto = A2PProtocol(
    id="incident_v1",
    name="Incident Stream",
    version="1.0",
    schema_uri="https://cybernetics.dev/schemas/incident.json",
    event_types=["detected", "resolved", "escalated"],
)
get_a2a_registry().register_protocol(proto)
```

### 12.3 ERC-8004 (8004.org)

**ERC-8004** is an Ethereum standard for agent capability discovery and identity, authored by Google. Cybernetics implements the on-chain resolution contract via `ERC8004Resolver`.

```python
from cybernetics.a2a.hooks import get_erc8004_resolver

resolver = get_erc8004_resolver()

# Query which capabilities are available
resolver.resolve(["sentinel_detect", "deploy_trigger"])
# → {"sentinel_detect": {"available": true, ...}, ...}

# Negotiate intersecting capabilities with a remote agent
resolver.negotiate([{"id": "sentinel_detect"}, {"id": "unknown_cap"}])
# → ["sentinel_detect"]
```

**Reference:** [8004.org](https://8004.org)

---

## 13. License & Attribution

Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0+).
See `LICENSE` for the full text.

**Authors:** plasmaraygun, GoryGrey, royhodge812, sebuh-infsol

---

*For operational issues, contact the maintainers via GitHub Security Advisories. Do not open public issues for security-sensitive topics.*
