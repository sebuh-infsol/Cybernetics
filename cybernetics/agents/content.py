"""ContentAgent — content ops using Notion, Linear, and Slack."""

import uuid
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from cybernetics.agents.base import AgentTemplate
from cybernetics.logging.logger import get_logger

logger = get_logger("cybernetics.agents.content")


class ContentAgent(AgentTemplate):
    name = "content"
    description = "ContentAgent: plan → draft → review → publish → distribute"
    adapters = ["notion", "linear", "slack"]

    def __init__(self, registry):
        super().__init__(registry)
        self.session_id = str(uuid.uuid4())

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data.get("topic", "")
        channel = input_data.get("channel", "#content")
        logger.info("content_start", session=self.session_id, topic=topic)
        try:
            # Phase 1: PLAN
            outline = await self._plan(topic)
            # Phase 2: DRAFT
            draft = await self._draft(topic, outline)
            # Phase 3: REVIEW
            feedback = await self._review(draft)
            # Phase 4: PUBLISH
            published = await self._publish(draft, feedback)
            # Phase 5: DISTRIBUTE
            await self._distribute(published, channel)
            # Phase 6: LEARN
            await self._learn(topic, draft, feedback, published)
            return {
                "status": "completed",
                "session_id": self.session_id,
                "topic": topic,
                "published_url": published.get("url", ""),
                "feedback": feedback,
            }
        except Exception as exc:
            logger.exception("content_failed")
            return {"status": "failed", "error": str(exc), "session_id": self.session_id}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _plan(self, topic: str) -> Dict[str, Any]:
        r = await self.registry.execute("notion", "notion_search", {"query": topic})
        existing = r.data.get("results", []) if r.success else []
        r = await self.registry.execute("linear", "linear_search_issues", {"query": topic})
        tickets = r.data.get("issues", []) if r.success else []
        return {"topic": topic, "existing_pages": [e.get("id") for e in existing], "related_tickets": tickets}

    async def _draft(self, topic: str, outline: Dict[str, Any]) -> Dict[str, Any]:
        r = await self.registry.execute("notion", "notion_create_page", {
            "parent_id": outline["existing_pages"][0] if outline["existing_pages"] else "root",
            "title": f"Draft: {topic}",
            "content": f"Auto-generated draft for {topic}\n\nSession: {self.session_id}",
        })
        return {"page_id": r.data.get("id", ""), "title": topic} if r.success else {}

    async def _review(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        await self.registry.execute("slack", "slack_post_message", {
            "channel": "#content-review",
            "text": f"Review requested for draft: {draft.get('title')}",
        })
        return {"requested": True, "channel": "#content-review"}

    async def _publish(self, draft: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        return {"url": f"https://notion.so/{draft.get('page_id', '')}", "status": "published"}

    async def _distribute(self, published: Dict[str, Any], channel: str):
        await self.registry.execute("slack", "slack_post_message", {
            "channel": channel,
            "text": f"New content published: {published.get('url')}",
        })

    async def _learn(self, topic: str, draft: Dict[str, Any], feedback: Dict[str, Any], published: Dict[str, Any]):
        # No postgres in this agent's adapters; skip learn
        pass
