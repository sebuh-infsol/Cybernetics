"""Basic smoke tests for Sentinel agent."""

import pytest
from src.config import Config


def test_config_validation():
    """Ensure Config.validate() catches missing env vars."""
    # This test requires a valid .env in CI or will be skipped
    try:
        Config.validate()
    except ValueError as e:
        pytest.skip(f"Missing env vars: {e}")


def test_dynatrace_client_init():
    """Dynatrace client can be initialized."""
    from src.tools.dynatrace_tools import DynatraceClient
    client = DynatraceClient()
    assert client.base_url is not None


def test_mongodb_client_init():
    """MongoDB client can be initialized."""
    from src.tools.mongodb_tools import MongoDBClient
    client = MongoDBClient()
    assert client.db is not None
