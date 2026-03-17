"""Tests for device type field on campaigns (Phase 1.2)."""

import pytest

from nexus_track.backend.mongo_client import (
    create_campaign,
    get_campaign,
    get_all_campaigns,
    update_campaign,
)


class TestDeviceTypeOnCampaigns:
    """Verify device_type and device_quota are stored and retrieved."""

    @pytest.mark.asyncio
    async def test_create_campaign_default_device_type(self, mongo):
        cid = await create_campaign({"name": "Test Campaign"})
        doc = await get_campaign(cid)
        assert doc["device_type"] == "Multi-device"
        assert doc["device_quota"] == {}

    @pytest.mark.asyncio
    async def test_create_campaign_with_device_type(self, mongo):
        cid = await create_campaign({
            "name": "iOS Campaign",
            "device_type": "iOS",
        })
        doc = await get_campaign(cid)
        assert doc["device_type"] == "iOS"

    @pytest.mark.asyncio
    async def test_create_campaign_with_device_quota(self, mongo):
        cid = await create_campaign({
            "name": "Quota Campaign",
            "device_type": "Multi-device",
            "device_quota": {"Orb": 20, "iOS": 10},
        })
        doc = await get_campaign(cid)
        assert doc["device_quota"]["Orb"] == 20
        assert doc["device_quota"]["iOS"] == 10

    @pytest.mark.asyncio
    async def test_device_quota_coerces_to_int(self, mongo):
        cid = await create_campaign({
            "name": "Coerce",
            "device_quota": {"Orb": "15", "iOS": "bad"},
        })
        doc = await get_campaign(cid)
        assert doc["device_quota"]["Orb"] == 15
        assert "iOS" not in doc["device_quota"]

    @pytest.mark.asyncio
    async def test_device_quota_negative_clamped_to_zero(self, mongo):
        cid = await create_campaign({
            "name": "Neg",
            "device_quota": {"Orb": -5},
        })
        doc = await get_campaign(cid)
        assert doc["device_quota"]["Orb"] == 0

    @pytest.mark.asyncio
    async def test_update_campaign_device_type(self, mongo):
        cid = await create_campaign({"name": "Update"})
        await update_campaign(cid, {"device_type": "Android"})
        doc = await get_campaign(cid)
        assert doc["device_type"] == "Android"

    @pytest.mark.asyncio
    async def test_update_campaign_device_quota(self, mongo):
        cid = await create_campaign({"name": "Update Quota"})
        await update_campaign(cid, {"device_quota": {"Orb": 50}})
        doc = await get_campaign(cid)
        assert doc["device_quota"]["Orb"] == 50

    @pytest.mark.asyncio
    async def test_backfill_legacy_campaign(self, mongo):
        """Campaigns created before device_type should get defaults."""
        cid = await create_campaign({"name": "Legacy"})
        # Simulate legacy: remove device_type field from DB
        from nexus_track.backend.mongo_client import _campaigns
        await _campaigns().update_one(
            {"campaign_id": cid},
            {"$unset": {"device_type": "", "device_quota": ""}},
        )
        doc = await get_campaign(cid)
        assert doc["device_type"] == "Multi-device"
        assert doc["device_quota"] == {}

    @pytest.mark.asyncio
    async def test_get_all_campaigns_includes_device_type(self, mongo):
        await create_campaign({"name": "A", "device_type": "Orb"})
        await create_campaign({"name": "B", "device_type": "iOS"})
        all_c = await get_all_campaigns()
        types = {c["device_type"] for c in all_c}
        assert "Orb" in types
        assert "iOS" in types
