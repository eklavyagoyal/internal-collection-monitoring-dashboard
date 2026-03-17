"""
Shared fixtures for tests_issue_5_9/.

Uses mongomock-motor to provide an in-memory MongoDB for deterministic testing.
"""

import os
import pytest

# Force test DB name before any import of mongo_client.
os.environ["MONGO_DB_NAME"] = "nexus_track_test"

try:
    from mongomock_motor import AsyncMongoMockClient
except ImportError:
    AsyncMongoMockClient = None

from nexus_track.backend import mongo_client as mc


@pytest.fixture(autouse=True)
def _patch_mongo(monkeypatch):
    """Replace the motor client with a FRESH mongomock for every test."""
    if AsyncMongoMockClient is None:
        pytest.skip("mongomock-motor not installed")
    fresh_client = AsyncMongoMockClient()
    monkeypatch.setattr(mc, "_client", fresh_client)
    monkeypatch.setattr(mc, "_get_client", lambda: fresh_client)
