"""Integration tests for adapters with mocked HTTP responses."""

import pytest
import respx
import httpx
from cybernetics.adapters.github import GitHubAdapter
from cybernetics.adapters.dynatrace import DynatraceAdapter
from cybernetics.adapters.slack import SlackAdapter
from cybernetics.adapters.stripe import StripeAdapter
from cybernetics.config.settings import settings
...
@pytest.mark.asyncio
@respx.mock
async def test_stripe_create_customer():
    adapter = StripeAdapter()
    
    route = respx.post("https://api.stripe.com/v1/customers").mock(
        return_value=httpx.Response(200, json={"id": "cus_123", "email": "test@example.com"})
    )
    
    result = await adapter.execute("stripe_create_customer", {"email": "test@example.com", "name": "Test User"})
    
    assert result.success is True
    assert result.data["id"] == "cus_123"
    assert route.called

@pytest.fixture(autouse=True)
def mock_settings():
    """Ensure we have some keys set for testing."""
    settings.github_token = "test-github-token"
    settings.dynatrace_api_token = "test-dt-token"
    settings.dynatrace_base_url = "https://tenant.live.dynatrace.com"
    settings.slack_bot_token = "xoxb-test"
    settings.sentinels_enabled = ["audit", "guard"]

@pytest.mark.asyncio
async def test_guard_blocks_sensitive_keys():
    adapter = SlackAdapter()
    
    # This should be blocked by the Guard sentinel because 'password' is a blocked keyword
    result = await adapter.execute("slack_post_message", {"channel": "general", "text": "secret password: 123"})
    # Wait, the Guard sentinel checks keys in arguments, not the content of the text itself.
    # class Guard(Sentinel):
    #     BLOCKED = {"password", "secret", "token", "key", "private_key"}
    #     async def before(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
    #         args = tool_call.get("arguments", {})
    #         for k in args:
    #             if any(b in k.lower() for b in self.BLOCKED):
    
    # So I should pass a blocked key.
    result = await adapter.execute("slack_post_message", {"channel": "general", "text": "hi", "api_token": "leak"})
    
    assert result.success is False
    assert "Guard blocked sensitive key" in result.error

@pytest.mark.asyncio
@respx.mock
async def test_github_create_issue():
    adapter = GitHubAdapter()
    
    # Mock the GitHub API call
    route = respx.post("https://api.github.com/repos/owner/repo/issues").mock(
        return_value=httpx.Response(201, json={"id": 123, "number": 1, "title": "Test Issue"})
    )
    
    result = await adapter.execute("github_create_issue", {
        "owner": "owner",
        "repo": "repo",
        "title": "Test Issue",
        "body": "Test Body"
    })
    
    assert result.success is True
    assert result.data["id"] == 123
    assert route.called

@pytest.mark.asyncio
@respx.mock
async def test_dynatrace_get_problems():
    adapter = DynatraceAdapter()
    
    route = respx.get("https://tenant.live.dynatrace.com/api/v2/problems").mock(
        return_value=httpx.Response(200, json={"problems": [{"problemId": "P-1", "title": "Test Problem"}]})
    )
    
    result = await adapter.execute("dynatrace_get_problems", {"from": "now-5m"})
    
    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["problemId"] == "P-1"
    assert route.called

@pytest.mark.asyncio
@respx.mock
async def test_slack_post_message():
    adapter = SlackAdapter()
    
    route = respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "channel": "C123", "message": {"ts": "123.456"}})
    )
    
    result = await adapter.execute("slack_post_message", {"channel": "general", "text": "Hello"})
    
    assert result.success is True
    assert result.data["ts"] == "123.456"
    assert route.called

@pytest.mark.asyncio
@respx.mock
async def test_adapter_error_handling():
    adapter = GitHubAdapter()
    
    # Mock a 404 error
    respx.post("https://api.github.com/repos/owner/repo/issues").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    
    result = await adapter.execute("github_create_issue", {
        "owner": "owner",
        "repo": "repo",
        "title": "Fail",
    })
    
    assert result.success is False
    assert "404" in result.error
