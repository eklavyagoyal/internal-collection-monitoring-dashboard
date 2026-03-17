"""
Tests for Issue #7: Simplified participant indicators.

Verifies:
- issue_comment field is preserved in data (amber border depends on it)
- status field works correctly (status dot depends on it)
- participant fields required for display are all present after upsert
"""

import pytest

from nexus_track.backend import mongo_client as mc

pytestmark = pytest.mark.asyncio


class TestParticipantIndicatorData:
    """#7 — data backing the simplified indicator set."""

    async def test_issue_flag_data_available(self):
        """issue_comment field is populated and retrievable (drives amber border)."""
        cid = await mc.create_campaign({"name": "Indicators"})
        await mc.upsert_participant(cid, "e1", "Alice", "a@t.com", "10:00", "2024-06-15")

        # Initially no issue
        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert parts[0]["issue_comment"] == ""

        # Flag an issue
        await mc.update_participant_field(cid, "e1", "issue_comment", "Device error")
        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert parts[0]["issue_comment"] == "Device error"

    async def test_status_dot_data_available(self):
        """Status transitions produce correct values for the status dot."""
        cid = await mc.create_campaign({"name": "Status-dot"})
        await mc.upsert_participant(cid, "e1", "Bob", "b@t.com", "11:00", "2024-06-15")

        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["status"] == "Pending"

        await mc.update_participant_status(cid, "e1", "In-Progress")
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["status"] == "In-Progress"

        await mc.update_participant_status(cid, "e1", "Completed")
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["status"] == "Completed"

    async def test_all_display_fields_present(self):
        """After upsert, all fields needed for participant row rendering exist."""
        cid = await mc.create_campaign({"name": "Fields-check"})
        await mc.upsert_participant(cid, "e1", "Carol", "c@t.com", "12:00", "2024-06-15")

        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        required_fields = [
            "google_event_id", "name", "email",
            "appointment_time", "appointment_date",
            "platform", "model_tag", "status",
            "notes", "issue_comment",
        ]
        for field in required_fields:
            assert field in p, f"Missing field: {field}"

    async def test_clear_issue_comment(self):
        """Clearing issue_comment removes the danger indicator data."""
        cid = await mc.create_campaign({"name": "Clear-issue"})
        await mc.upsert_participant(cid, "e1", "Dan", "d@t.com", "13:00", "2024-06-15")
        await mc.update_participant_field(cid, "e1", "issue_comment", "Flagged")

        # Verify flagged
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["issue_comment"] == "Flagged"

        # Clear
        await mc.update_participant_field(cid, "e1", "issue_comment", "")
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["issue_comment"] == ""
