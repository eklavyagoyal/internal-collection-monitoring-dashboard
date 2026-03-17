"""Tests for campaign cloning (Phase 2.2)."""

import pytest

from nexus_track.backend.mongo_client import (
    clone_campaign,
    create_campaign,
    get_campaign,
    upsert_participant,
    get_participants_for_campaign,
)


class TestCampaignClone:
    """Verify clone_campaign copies settings but not participants."""

    @pytest.mark.asyncio
    async def test_clone_copies_name_with_suffix(self, mongo):
        cid = await create_campaign({"name": "Original"})
        new_cid = await clone_campaign(cid)
        assert new_cid is not None
        doc = await get_campaign(new_cid)
        assert doc["name"] == "Original (Copy)"

    @pytest.mark.asyncio
    async def test_clone_generates_new_id(self, mongo):
        cid = await create_campaign({"name": "Source"})
        new_cid = await clone_campaign(cid)
        assert new_cid != cid

    @pytest.mark.asyncio
    async def test_clone_copies_settings(self, mongo):
        cid = await create_campaign({
            "name": "Config",
            "description": "desc",
            "device_type": "iOS",
            "device_quota": {"iOS": 50},
            "goal": 200,
            "booking_url": "https://example.com",
        })
        new_cid = await clone_campaign(cid)
        doc = await get_campaign(new_cid)
        assert doc["description"] == "desc"
        assert doc["device_type"] == "iOS"
        assert doc["device_quota"] == {"iOS": 50}
        assert doc["goal"] == 200
        assert doc["booking_url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_clone_has_no_participants(self, mongo):
        cid = await create_campaign({"name": "WithParts"})
        await upsert_participant(cid, "e1", "A", "a@t.co", "10:00", "2025-01-01")
        await upsert_participant(cid, "e2", "B", "b@t.co", "11:00", "2025-01-01")
        new_cid = await clone_campaign(cid)
        parts = await get_participants_for_campaign(new_cid)
        assert len(parts) == 0

    @pytest.mark.asyncio
    async def test_clone_nonexistent_returns_none(self, mongo):
        result = await clone_campaign("nonexistent_id")
        assert result is None
