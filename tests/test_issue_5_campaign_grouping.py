"""
Tests for Issue #5: Campaign-based sorting replaces date-based grouping.

Verifies:
- get_participants_for_campaign(cid) returns ALL participants across dates
- get_participants_for_campaign(cid, date) still works for date-filtered queries
- Participants sort by (date, time) when fetching all
- CSV export helper returns all participants without date filter
- Missing campaign gracefully returns empty
"""

import pytest

from nexus_track.backend import mongo_client as mc

pytestmark = pytest.mark.asyncio


class TestCampaignGroupingReplacesDateGrouping:
    """#5 — campaign is now the top-level organizational unit."""

    async def test_all_participants_across_dates(self):
        """Fetching without date returns every participant for the campaign."""
        cid = await mc.create_campaign({"name": "All-dates"})
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e2", "B", "b@t.com", "09:00", "2024-06-16")
        await mc.upsert_participant(cid, "e3", "C", "c@t.com", "14:00", "2024-06-14")

        all_parts = await mc.get_participants_for_campaign(cid)
        assert len(all_parts) == 3

    async def test_all_participants_sorted_by_date_then_time(self):
        """All-participants query sorts by appointment_date ASC, then time ASC."""
        cid = await mc.create_campaign({"name": "Sort-check"})
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "14:00", "2024-06-16")
        await mc.upsert_participant(cid, "e2", "B", "b@t.com", "09:00", "2024-06-15")
        await mc.upsert_participant(cid, "e3", "C", "c@t.com", "11:00", "2024-06-15")

        parts = await mc.get_participants_for_campaign(cid)
        dates_times = [(p["appointment_date"], p["appointment_time"]) for p in parts]
        assert dates_times == [
            ("2024-06-15", "09:00"),
            ("2024-06-15", "11:00"),
            ("2024-06-16", "14:00"),
        ]

    async def test_date_filter_still_works(self):
        """Passing an explicit date still returns only that day."""
        cid = await mc.create_campaign({"name": "Date-filter"})
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e2", "B", "b@t.com", "11:00", "2024-06-16")

        day15 = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert len(day15) == 1
        assert day15[0]["name"] == "A"

    async def test_no_date_section_rendering(self):
        """All results belong to the campaign — no date-bucketing artifacts."""
        cid = await mc.create_campaign({"name": "No-date-sections"})
        await mc.upsert_participant(cid, "e1", "X", "x@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e2", "Y", "y@t.com", "10:00", "2024-06-16")

        parts = await mc.get_participants_for_campaign(cid)
        # Every row has campaign_id — no separate "date section" objects
        assert all(p["campaign_id"] == cid for p in parts)

    async def test_missing_campaign_returns_empty(self):
        """Querying a non-existent campaign returns an empty list."""
        parts = await mc.get_participants_for_campaign("nonexistent")
        assert parts == []

    async def test_export_all_no_date_filter(self):
        """CSV export returns all participants when date=None."""
        cid = await mc.create_campaign({"name": "Export-all"})
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e2", "B", "b@t.com", "11:00", "2024-06-16")

        rows = await mc.get_participants_for_export(cid)
        assert len(rows) == 2

    async def test_booking_groups_by_campaign(self):
        """Participants from different campaigns don't mix."""
        c1 = await mc.create_campaign({"name": "Campaign-1"})
        c2 = await mc.create_campaign({"name": "Campaign-2"})
        await mc.upsert_participant(c1, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(c2, "e2", "B", "b@t.com", "11:00", "2024-06-15")

        parts_c1 = await mc.get_participants_for_campaign(c1)
        parts_c2 = await mc.get_participants_for_campaign(c2)
        assert len(parts_c1) == 1
        assert len(parts_c2) == 1
        assert parts_c1[0]["name"] == "A"
        assert parts_c2[0]["name"] == "B"
