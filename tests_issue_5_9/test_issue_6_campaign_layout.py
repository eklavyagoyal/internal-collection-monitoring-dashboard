"""
Tests for Issue #6: Campaign UI layout — view-model / data availability.

Since the UI is rendered by Reflex (server-side components), we test the
data layer that feeds the layout:
- campaign dict contains title, docs, links, booking, goal, deadline
- missing optional fields handled gracefully
- get_campaign backfills defaults
"""

import pytest

from nexus_track.backend import mongo_client as mc

pytestmark = pytest.mark.asyncio


class TestCampaignLayoutData:
    """#6 — data backing the left / center / right layout zones."""

    async def test_full_campaign_has_all_layout_fields(self):
        """A campaign with all fields populated provides data for every zone."""
        cid = await mc.create_campaign({
            "name": "Full Campaign",
            "description": "Test desc",
            "booking_url": "https://cal.example.com/book",
            "notion_url": "https://notion.so/docs",
            "linear_url": "https://linear.app/issue",
            "deadline": "2025-12-31",
            "goal": "200",
        })
        doc = await mc.get_campaign(cid)

        # Left zone
        assert doc["name"] == "Full Campaign"
        assert doc["booking_url"] == "https://cal.example.com/book"
        assert doc["notion_url"] == "https://notion.so/docs"
        assert doc["linear_url"] == "https://linear.app/issue"

        # Right zone
        assert doc["goal"] == 200
        assert doc["deadline"] == "2025-12-31"

        # Center zone
        assert doc["status"] == "active"

    async def test_missing_optional_fields_backfilled(self):
        """A minimal campaign gets safe defaults for optional layout fields."""
        cid = await mc.create_campaign({"name": "Minimal"})
        doc = await mc.get_campaign(cid)

        assert doc["name"] == "Minimal"
        assert doc.get("booking_url", "") == ""
        assert doc.get("notion_url", "") == ""
        assert doc.get("linear_url", "") == ""
        assert doc.get("deadline", "") == ""
        assert doc["goal"] == 100  # default
        assert doc["status"] == "active"

    async def test_goal_deadline_card_data(self):
        """Goal and deadline are available for the right-side card."""
        cid = await mc.create_campaign({
            "name": "With deadline",
            "goal": "50",
            "deadline": "2025-06-30",
        })
        doc = await mc.get_campaign(cid)
        assert doc["goal"] == 50
        assert doc["deadline"] == "2025-06-30"

    async def test_goal_only_no_deadline(self):
        """Campaign with goal but no deadline renders cleanly."""
        cid = await mc.create_campaign({"name": "Goal-only", "goal": "75"})
        doc = await mc.get_campaign(cid)
        assert doc["goal"] == 75
        assert doc["deadline"] == ""

    async def test_legacy_campaign_backfill(self):
        """Old campaigns without new fields get backfilled."""
        await mc._campaigns().insert_one({
            "campaign_id": "legacy1",
            "name": "Old Campaign",
            "status": "active",
            "created_at": "2024-01-01",
        })
        doc = await mc.get_campaign("legacy1")
        assert doc is not None
        assert doc["goal"] == 100
        assert doc["notion_url"] == ""
        assert doc["linear_url"] == ""
        assert doc["deadline"] == ""
