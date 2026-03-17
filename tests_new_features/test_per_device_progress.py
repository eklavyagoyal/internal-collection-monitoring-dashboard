"""Tests for per-device progress aggregation (Phase 2.1)."""

import pytest

from nexus_track.backend.mongo_client import (
    create_campaign,
    get_per_device_progress,
    upsert_participant,
    update_participant_status,
)


class TestPerDeviceProgress:
    """Verify get_per_device_progress aggregation pipeline."""

    @pytest.mark.asyncio
    async def test_empty_campaign(self, mongo):
        cid = await create_campaign({"name": "Empty"})
        result = await get_per_device_progress(cid)
        assert result == {}

    @pytest.mark.asyncio
    async def test_single_platform(self, mongo):
        cid = await create_campaign({"name": "Single"})
        await upsert_participant(cid, "e1", "Alice", "a@t.co", "10:00", "2025-01-01")
        # Set platform via direct DB update
        from nexus_track.backend.mongo_client import update_participant_field
        await update_participant_field(cid, "e1", "platform", "iOS")
        result = await get_per_device_progress(cid)
        assert "iOS" in result
        assert result["iOS"]["total"] == 1
        assert result["iOS"]["completed"] == 0

    @pytest.mark.asyncio
    async def test_completed_count(self, mongo):
        cid = await create_campaign({"name": "Done"})
        await upsert_participant(cid, "e1", "A", "a@t.co", "10:00", "2025-01-01")
        await upsert_participant(cid, "e2", "B", "b@t.co", "11:00", "2025-01-01")
        from nexus_track.backend.mongo_client import update_participant_field
        await update_participant_field(cid, "e1", "platform", "Orb")
        await update_participant_field(cid, "e2", "platform", "Orb")
        await update_participant_status(cid, "e1", "Completed")
        result = await get_per_device_progress(cid)
        assert result["Orb"]["total"] == 2
        assert result["Orb"]["completed"] == 1

    @pytest.mark.asyncio
    async def test_multiple_platforms(self, mongo):
        cid = await create_campaign({"name": "Multi"})
        await upsert_participant(cid, "e1", "A", "a@t.co", "10:00", "2025-01-01")
        await upsert_participant(cid, "e2", "B", "b@t.co", "11:00", "2025-01-01")
        await upsert_participant(cid, "e3", "C", "c@t.co", "12:00", "2025-01-01")
        from nexus_track.backend.mongo_client import update_participant_field
        await update_participant_field(cid, "e1", "platform", "iOS")
        await update_participant_field(cid, "e2", "platform", "Android")
        await update_participant_field(cid, "e3", "platform", "iOS")
        await update_participant_status(cid, "e3", "Completed")
        result = await get_per_device_progress(cid)
        assert result["iOS"]["total"] == 2
        assert result["iOS"]["completed"] == 1
        assert result["Android"]["total"] == 1
        assert result["Android"]["completed"] == 0

    @pytest.mark.asyncio
    async def test_empty_platform_excluded(self, mongo):
        """Participants with no platform set should not appear."""
        cid = await create_campaign({"name": "NoPlatform"})
        await upsert_participant(cid, "e1", "A", "a@t.co", "10:00", "2025-01-01")
        # platform defaults to "" — should be excluded
        result = await get_per_device_progress(cid)
        assert result == {}
