"""MongoDB MCP tools — persistent memory for incident patterns and agent state."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo import MongoClient
from src.config import Config

class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(Config.MONGODB_URI)
        self.db = self.client.get_database("sentinel")

    def get_memory_collection(self):
        return self.db["memory"]

    def get_incidents_collection(self):
        return self.db["incidents"]

    async def recall_pattern(self, pattern_signature: str) -> Optional[Dict[str, Any]]:
        """Recall a previously learned remediation pattern."""
        coll = self.get_memory_collection()
        return coll.find_one({"pattern_signature": pattern_signature})

    async def store_pattern(self, pattern_signature: str, diagnosis: str, action: str, outcome: str) -> None:
        """Store a new learned pattern."""
        coll = self.get_memory_collection()
        coll.update_one(
            {"pattern_signature": pattern_signature},
            {
                "$set": {
                    "diagnosis": diagnosis,
                    "action": action,
                    "outcome": outcome,
                    "last_seen": datetime.utcnow(),
                },
                "$inc": {"occurrence_count": 1},
            },
            upsert=True,
        )

    async def log_incident(self, incident: Dict[str, Any]) -> str:
        """Log a new incident and return its ID."""
        coll = self.get_incidents_collection()
        incident["created_at"] = datetime.utcnow()
        result = coll.insert_one(incident)
        return str(result.inserted_id)

    async def get_recent_incidents(self, service: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent incidents for a service."""
        coll = self.get_incidents_collection()
        return list(
            coll.find({"service": service})
            .sort("created_at", -1)
            .limit(limit)
        )
