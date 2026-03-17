"""Shared fixtures for new feature tests."""

import asyncio

import mongomock_motor
import pytest


@pytest.fixture()
def mongo(monkeypatch):
    """Swap the real Motor client for mongomock-motor."""
    import nexus_track.backend.mongo_client as mc

    mock_client = mongomock_motor.AsyncMongoMockClient()
    monkeypatch.setattr(mc, "_client", mock_client)
    yield mock_client
    # Drop the database after each test
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        mock_client.drop_database(mc._db().name)
    )
