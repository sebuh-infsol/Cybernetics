"""Elastic MCP tools — hybrid search across logs, incidents, and runbooks."""

from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from src.config import Config

class ElasticClient:
    def __init__(self):
        self.client = Elasticsearch(
            cloud_id=Config.ELASTIC_CLOUD_ID,
            api_key=Config.ELASTIC_API_KEY,
        )

    async def search_incidents(self, query: str, index: str = "sentinel-incidents", size: int = 10) -> List[Dict[str, Any]]:
        """Hybrid search across incident history and resolution notes."""
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "description", "resolution", "tags"],
                    "type": "best_fields",
                }
            },
            "size": size,
        }
        resp = self.client.search(index=index, body=body)
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    async def search_runbooks(self, symptom: str, index: str = "sentinel-runbooks", size: int = 5) -> List[Dict[str, Any]]:
        """Find runbooks matching a symptom description."""
        body = {
            "query": {
                "match": {"symptoms": symptom},
            },
            "size": size,
        }
        resp = self.client.search(index=index, body=body)
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    async def write_insight(self, incident_id: str, insight: str, index: str = "sentinel-incidents") -> None:
        """Write an enriched insight back to Elastic for future retrieval."""
        self.client.update(
            index=index,
            id=incident_id,
            body={"doc": {"agent_insight": insight, "enriched": True}},
        )
