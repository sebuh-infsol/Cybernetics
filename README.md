# Cybernetics Composable Meta-MCP for Google Cloud Agents

**Classification:** UNCLASSIFIED / OPEN SOURCE  
**Authors:** plasmaraygun, GoryGrey, royhodge812, sebuh-infsol  (strawberr0)  
**Version:** 2026.5.2  
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

## 4. MCP Server — Cybernetics as an MCP Peer

Cybernetics is not just a broker; it is a **first-class MCP server** that any MCP client (Claude Desktop, Cursor, Windsurf, etc.) can connect to via stdio transport.

### 4.1 Connecting from Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cybernetics": {
      "command": "cybernetics-mcp",
      "env": {
        "BROKER_API_KEY": "your-key",
        "POSTGRES_DSN": "postgresql+asyncpg://...",
        "DYNATRACE_API_TOKEN": "..."
      }
    }
  }
}
```

### 4.2 Protocol

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

## 11. License & Attribution

Licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0+).
See `LICENSE` for the full text.

**Authors:** plasmaraygun, GoryGrey, royhodge812, sebuh-infsol

---

*For operational issues, contact the maintainers via GitHub Security Advisories. Do not open public issues for security-sensitive topics.*
