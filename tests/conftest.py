"""Shared pytest fixtures for all nexus_track tests."""

import os

import pytest
from mongomock_motor import AsyncMongoMockClient

# Force test DB name before any import of mongo_client.
os.environ["MONGO_DB_NAME"] = "nexus_track_test"

from nexus_track.backend import mongo_client as mc  # noqa: E402


@pytest.fixture(autouse=True)
def _patch_mongo(monkeypatch):
    """Replace the motor client with a fresh mongomock for every test."""
    fresh_client = AsyncMongoMockClient()
    monkeypatch.setattr(mc, "_client", fresh_client)
    monkeypatch.setattr(mc, "_get_client", lambda: fresh_client)


@pytest.fixture()
def mongo(monkeypatch):
    """Named fixture alias for tests that declare `mongo` explicitly."""
    return mc._get_client()
