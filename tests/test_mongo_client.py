"""
Tests for mongo_client.py — campaign CRUD, participant CRUD, progress aggregation.

Uses mongomock_motor to provide an in-memory MongoDB for deterministic testing.
"""

import os
import pytest

# Force test DB name before any import of mongo_client.
os.environ["MONGO_DB_NAME"] = "nexus_track_test"

# We use mongomock-motor to avoid needing a real MongoDB instance.
try:
    from mongomock_motor import AsyncMongoMockClient
except ImportError:
    AsyncMongoMockClient = None

from nexus_track.backend import mongo_client as mc

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_mongo(monkeypatch):
    """Replace the motor client with a FRESH mongomock for every test."""
    if AsyncMongoMockClient is None:
        pytest.skip("mongomock-motor not installed")
    fresh_client = AsyncMongoMockClient()
    monkeypatch.setattr(mc, "_client", fresh_client)
    monkeypatch.setattr(mc, "_get_client", lambda: fresh_client)


# ---------------------------------------------------------------------------
# Campaign CRUD
# ---------------------------------------------------------------------------

class TestCreateCampaign:
    @pytest.mark.asyncio
    async def test_basic_create(self):
        cid = await mc.create_campaign({"name": "Test Campaign"})
        assert isinstance(cid, str) and len(cid) == 8  # token_hex(4)

        doc = await mc.get_campaign(cid)
        assert doc is not None
        assert doc["name"] == "Test Campaign"
        assert doc["goal"] == 100  # default
        assert doc["status"] == "active"
        assert doc["last_sync_at"] is None

    @pytest.mark.asyncio
    async def test_goal_coercion(self):
        cid = await mc.create_campaign({"name": "G1", "goal": "200"})
        doc = await mc.get_campaign(cid)
        assert doc["goal"] == 200

    @pytest.mark.asyncio
    async def test_goal_negative_clamps_to_1(self):
        cid = await mc.create_campaign({"name": "G2", "goal": -5})
        doc = await mc.get_campaign(cid)
        assert doc["goal"] == 1

    @pytest.mark.asyncio
    async def test_goal_invalid_string_defaults(self):
        cid = await mc.create_campaign({"name": "G3", "goal": "abc"})
        doc = await mc.get_campaign(cid)
        assert doc["goal"] == 100

    @pytest.mark.asyncio
    async def test_notion_and_linear_default_empty(self):
        """Notion/Linear fields should default to empty strings."""
        cid = await mc.create_campaign({"name": "NL"})
        doc = await mc.get_campaign(cid)
        assert doc["notion_url"] == ""
        assert doc["linear_url"] == ""


class TestUpdateCampaign:
    @pytest.mark.asyncio
    async def test_update_name(self):
        cid = await mc.create_campaign({"name": "Old"})
        await mc.update_campaign(cid, {"name": "New"})
        doc = await mc.get_campaign(cid)
        assert doc["name"] == "New"

    @pytest.mark.asyncio
    async def test_update_goal(self):
        cid = await mc.create_campaign({"name": "U1", "goal": 50})
        await mc.update_campaign(cid, {"goal": "300"})
        doc = await mc.get_campaign(cid)
        assert doc["goal"] == 300

    @pytest.mark.asyncio
    async def test_update_goal_invalid_ignored(self):
        cid = await mc.create_campaign({"name": "U2", "goal": 80})
        await mc.update_campaign(cid, {"goal": "oops"})
        doc = await mc.get_campaign(cid)
        assert doc["goal"] == 80  # unchanged

    @pytest.mark.asyncio
    async def test_disallowed_field_ignored(self):
        cid = await mc.create_campaign({"name": "U3"})
        await mc.update_campaign(cid, {"status": "paused", "evil": "hack"})
        doc = await mc.get_campaign(cid)
        assert doc["status"] == "paused"
        assert "evil" not in doc


class TestGetCampaigns:
    @pytest.mark.asyncio
    async def test_backfill_goal(self):
        """Old campaigns without a 'goal' field get backfilled to 100."""
        # Insert directly without goal field
        await mc._campaigns().insert_one({
            "campaign_id": "old1",
            "name": "Legacy",
            "status": "active",
            "created_at": "2024-01-01",
        })
        campaigns = await mc.get_all_campaigns()
        assert campaigns[0]["goal"] == 100

    @pytest.mark.asyncio
    async def test_get_campaign_also_backfills(self):
        await mc._campaigns().insert_one({
            "campaign_id": "old2",
            "name": "Legacy2",
            "status": "active",
        })
        doc = await mc.get_campaign("old2")
        assert doc["goal"] == 100


# ---------------------------------------------------------------------------
# Participant CRUD
# ---------------------------------------------------------------------------

class TestParticipantCRUD:
    @pytest.mark.asyncio
    async def test_upsert_and_fetch(self):
        cid = await mc.create_campaign({"name": "P1"})
        await mc.upsert_participant(
            cid, "evt-1", "Alice", "alice@test.com", "10:00", "2024-06-15",
        )
        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert len(parts) == 1
        assert parts[0]["name"] == "Alice"
        assert parts[0]["issue_comment"] == ""  # default from setOnInsert

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self):
        cid = await mc.create_campaign({"name": "P2"})
        await mc.upsert_participant(
            cid, "evt-2", "Bob", "bob@test.com", "11:00", "2024-06-15",
        )
        await mc.upsert_participant(
            cid, "evt-2", "Robert", "bob@test.com", "11:30", "2024-06-15",
        )
        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert len(parts) == 1
        assert parts[0]["name"] == "Robert"
        assert parts[0]["appointment_time"] == "11:30"

    @pytest.mark.asyncio
    async def test_issue_comment_in_setOnInsert(self):
        cid = await mc.create_campaign({"name": "P3"})
        await mc.upsert_participant(
            cid, "evt-3", "Eve", "eve@test.com", "09:00", "2024-06-15",
        )
        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert "issue_comment" in parts[0]
        assert parts[0]["issue_comment"] == ""

    @pytest.mark.asyncio
    async def test_update_participant_field(self):
        cid = await mc.create_campaign({"name": "P4"})
        await mc.upsert_participant(
            cid, "evt-4", "Dan", "dan@t.com", "12:00", "2024-06-15",
        )
        await mc.update_participant_field(cid, "evt-4", "issue_comment", "Late arrival")
        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert parts[0]["issue_comment"] == "Late arrival"

    @pytest.mark.asyncio
    async def test_status_transitions(self):
        cid = await mc.create_campaign({"name": "P5"})
        await mc.upsert_participant(
            cid, "evt-5", "Frank", "f@t.com", "14:00", "2024-06-15",
        )
        await mc.update_participant_status(cid, "evt-5", "In-Progress")
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["status"] == "In-Progress"
        assert p["start_time"] is not None

        await mc.update_participant_status(cid, "evt-5", "Completed")
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["status"] == "Completed"
        assert p["end_time"] is not None


class TestManualParticipant:
    @pytest.mark.asyncio
    async def test_add_manual(self):
        cid = await mc.create_campaign({"name": "M1"})
        eid = await mc.add_manual_participant(cid, "Grace", "g@t.com", "2024-06-15", "15:00")
        assert eid.startswith("manual-")

        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert len(parts) == 1
        assert parts[0]["issue_comment"] == ""
        assert parts[0]["status"] == "Pending"


# ---------------------------------------------------------------------------
# Progress aggregation
# ---------------------------------------------------------------------------

class TestCampaignProgress:
    @pytest.mark.asyncio
    async def test_empty_campaign(self):
        cid = await mc.create_campaign({"name": "Prog1"})
        result = await mc.get_campaign_progress(cid)
        assert result == {"booked": 0, "completed": 0}

    @pytest.mark.asyncio
    async def test_booked_and_completed(self):
        cid = await mc.create_campaign({"name": "Prog2"})
        # 3 participants over 2 dates
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e2", "B", "b@t.com", "11:00", "2024-06-15")
        await mc.upsert_participant(cid, "e3", "C", "c@t.com", "09:00", "2024-06-16")
        # Mark 2 completed
        await mc.update_participant_status(cid, "e1", "Completed")
        await mc.update_participant_status(cid, "e3", "Completed")

        result = await mc.get_campaign_progress(cid)
        assert result["booked"] == 3
        assert result["completed"] == 2

    @pytest.mark.asyncio
    async def test_deduplication_by_email(self):
        """Same email across two dates should count as 1 unique participant."""
        cid = await mc.create_campaign({"name": "Prog3"})
        await mc.upsert_participant(cid, "e-d1", "X", "x@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e-d2", "X", "x@t.com", "10:00", "2024-06-16")

        result = await mc.get_campaign_progress(cid)
        assert result["booked"] == 1  # deduplicated by email


class TestExportCSV:
    @pytest.mark.asyncio
    async def test_issue_comment_in_export(self):
        cid = await mc.create_campaign({"name": "Export1"})
        await mc.upsert_participant(cid, "ex-1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.update_participant_field(cid, "ex-1", "issue_comment", "Had issue")

        rows = await mc.get_participants_for_export(cid)
        assert len(rows) == 1
        assert rows[0]["issue_comment"] == "Had issue"


class TestSyncedDates:
    @pytest.mark.asyncio
    async def test_get_synced_dates(self):
        cid = await mc.create_campaign({"name": "Sync1"})
        await mc.upsert_participant(cid, "s-1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "s-2", "B", "b@t.com", "11:00", "2024-06-16")
        await mc.upsert_participant(cid, "s-3", "C", "c@t.com", "12:00", "2024-06-15")

        dates = await mc.get_synced_dates_for_campaign(cid)
        assert sorted(dates) == ["2024-06-15", "2024-06-16"]
