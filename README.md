# aiwg-mcp-broker
## Composable MCP Server for Google Cloud Agents

A unified MCP Broker that connects Google Cloud Agents (Gemini 3) to a composable registry of partner MCP servers (GitLab, MongoDB, Elastic, Arize, Fivetran, Dynatrace) plus custom plugins.

### Features
- **Unified Namespace:** One MCP endpoint for Google Cloud Agent Builder.
- **Dynamic Registry:** Load/unload MCP servers on the fly.
- **Sentinel Layering:** Apply middleware templates (Audit, Guard, Cost, etc.) to tool calls.
- **Partner Tracks:** Pre-configured adapters for all 6 hackathon partner tracks.

### Architecture
1. **Broker:** Main server exposing the unified MCP interface.
2. **Registry:** Manages connections to backend MCP servers.
3. **Sentinels:** Middleware pipeline for tool call governance.
