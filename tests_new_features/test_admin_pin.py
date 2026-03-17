"""Tests for admin PIN authentication (Phase 1.1)."""

import hashlib

import pytest

from nexus_track.backend.mongo_client import (
    get_admin_pin_hash,
    get_settings,
    set_admin_pin,
)


class TestAdminPin:
    """Verify admin PIN storage and retrieval."""

    @pytest.mark.asyncio
    async def test_no_pin_by_default(self, mongo):
        pin_hash = await get_admin_pin_hash()
        assert pin_hash == ""

    @pytest.mark.asyncio
    async def test_set_and_get_pin(self, mongo):
        pin = "1234"
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        await set_admin_pin(pin_hash)
        stored = await get_admin_pin_hash()
        assert stored == pin_hash

    @pytest.mark.asyncio
    async def test_pin_persists_after_settings_read(self, mongo):
        pin_hash = hashlib.sha256("secret".encode()).hexdigest()
        # First init settings
        await get_settings()
        # Then set PIN
        await set_admin_pin(pin_hash)
        # Read settings again
        stored = await get_admin_pin_hash()
        assert stored == pin_hash

    @pytest.mark.asyncio
    async def test_pin_is_in_settings_doc(self, mongo):
        pin_hash = hashlib.sha256("4567".encode()).hexdigest()
        await get_settings()  # ensure settings exist
        await set_admin_pin(pin_hash)
        doc = await get_settings()
        assert doc.get("admin_pin_hash") == pin_hash

    @pytest.mark.asyncio
    async def test_update_pin(self, mongo):
        hash1 = hashlib.sha256("old".encode()).hexdigest()
        hash2 = hashlib.sha256("new".encode()).hexdigest()
        await get_settings()
        await set_admin_pin(hash1)
        assert await get_admin_pin_hash() == hash1
        await set_admin_pin(hash2)
        assert await get_admin_pin_hash() == hash2
