"""
Tests for mongo_client.py — campaign CRUD, participant CRUD, progress aggregation.

Uses mongomock_motor to provide an in-memory MongoDB for deterministic testing.
"""

import hashlib
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
        assert doc["last_sync_attempt_at"] is None
        assert doc["last_sync_success_at"] is None
        assert doc["last_sync_error_code"] == ""
        assert doc["last_sync_error"] == ""
        assert doc["last_sync_error_detail"] == ""

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
    async def test_external_link_fields_default_to_empty_strings(self):
        """Campaigns keep external-link fields even when they are unset."""
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

    @pytest.mark.asyncio
    async def test_backfills_legacy_last_sync_into_success_and_attempt(self):
        await mc._campaigns().insert_one({
            "campaign_id": "old3",
            "name": "Legacy3",
            "status": "active",
            "last_sync_at": "2026-03-23T10:15:00",
        })

        doc = await mc.get_campaign("old3")

        assert doc["last_sync_success_at"] == "2026-03-23T10:15:00"
        assert doc["last_sync_attempt_at"] == "2026-03-23T10:15:00"
        assert doc["last_sync_error_code"] == ""
        assert doc["last_sync_error"] == ""
        assert doc["last_sync_error_detail"] == ""


class TestOperationalDayTimezone:
    async def test_resolve_operations_timezone_name_prefers_app_day_timezone(self, monkeypatch):
        monkeypatch.setenv("APP_DAY_TIMEZONE", "America/Los_Angeles")
        monkeypatch.delenv("TZ", raising=False)

        assert mc.resolve_operations_timezone_name() == "America/Los_Angeles"

    async def test_resolve_operations_timezone_name_falls_back_to_tz_env(self, monkeypatch):
        monkeypatch.delenv("APP_DAY_TIMEZONE", raising=False)
        monkeypatch.setenv("TZ", "Europe/Berlin")

        assert mc.resolve_operations_timezone_name() == "Europe/Berlin"

    async def test_resolve_operations_timezone_name_falls_back_to_utc_for_invalid_values(
        self,
        monkeypatch,
    ):
        monkeypatch.setenv("APP_DAY_TIMEZONE", "Mars/Olympus")
        monkeypatch.delenv("TZ", raising=False)

        assert mc.resolve_operations_timezone_name() == "UTC"

    @pytest.mark.asyncio
    async def test_dashboard_stats_default_to_operational_day(self, monkeypatch):
        monkeypatch.setattr(mc, "operational_today_str", lambda: "2026-03-23")

        cid = await mc.create_campaign({"name": "OpsDay"})
        await mc.upsert_participant(
            cid, "ops-1", "Alice", "alice@test.com", "09:00", "2026-03-23",
        )
        await mc.upsert_participant(
            cid, "ops-2", "Bob", "bob@test.com", "11:00", "2026-03-24",
        )

        campaigns = await mc.get_all_campaigns_with_stats()

        assert campaigns[0]["today_total"] == 1
        assert campaigns[0]["today_booked"] == 1
        assert campaigns[0]["today_completed"] == 0


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
        assert parts[0]["progress_key"] == "email:alice@test.com"
        assert parts[0]["appointment_sort_key"] == "2024-06-15T10:00:00"

    @pytest.mark.asyncio
    async def test_upsert_can_store_richer_calendar_datetime_fields(self):
        cid = await mc.create_campaign({"name": "P1b"})
        await mc.upsert_participant(
            cid,
            "evt-1b",
            "Alice",
            "alice@test.com",
            "09:15",
            "2026-03-23",
            appointment_start_raw="2026-03-23T09:15:00-07:00",
            appointment_start_utc="2026-03-23T16:15:00+00:00",
            appointment_timezone="America/Los_Angeles",
            appointment_has_time=True,
        )

        parts = await mc.get_participants_for_campaign(cid, "2026-03-23")

        assert parts[0]["appointment_start_raw"] == "2026-03-23T09:15:00-07:00"
        assert parts[0]["appointment_start_utc"] == "2026-03-23T16:15:00+00:00"
        assert parts[0]["appointment_timezone"] == "America/Los_Angeles"
        assert parts[0]["appointment_has_time"] is True

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
        await mc.update_participant_status(cid, "evt-5", "Completed")
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["status"] == "Completed"
        assert p["end_time"] is not None

        await mc.update_participant_status(cid, "evt-5", "Booked")
        p = (await mc.get_participants_for_campaign(cid, "2024-06-15"))[0]
        assert p["status"] == "Booked"
        assert p["start_time"] is None
        assert p["end_time"] is None

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self):
        cid = await mc.create_campaign({"name": "P6"})
        await mc.upsert_participant(
            cid, "evt-6", "Nina", "n@t.com", "15:00", "2024-06-15",
        )

        with pytest.raises(ValueError):
            await mc.update_participant_status(cid, "evt-6", "In-Progress")

    @pytest.mark.asyncio
    async def test_bulk_status_transitions_follow_same_contract(self):
        cid = await mc.create_campaign({"name": "P7"})
        await mc.upsert_participant(
            cid, "evt-7a", "Amy", "amy@test.com", "10:00", "2024-06-15",
        )
        await mc.upsert_participant(
            cid, "evt-7b", "Ben", "ben@test.com", "11:00", "2024-06-15",
        )

        modified = await mc.bulk_update_participant_status(
            cid, ["evt-7a", "evt-7b"], "Completed",
        )
        assert modified == 2

        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert all(p["status"] == "Completed" for p in parts)
        assert all(p["end_time"] is not None for p in parts)


class TestManualParticipant:
    @pytest.mark.asyncio
    async def test_add_manual(self):
        cid = await mc.create_campaign({"name": "M1"})
        eid = await mc.add_manual_participant(cid, "Grace", "g@t.com", "2024-06-15", "15:00")
        assert eid.startswith("manual-")

        parts = await mc.get_participants_for_campaign(cid, "2024-06-15")
        assert len(parts) == 1
        assert parts[0]["issue_comment"] == ""
        assert parts[0]["status"] == "Booked" # removed pending status, so manual starts as Booked 
        assert parts[0]["appointment_start_raw"] == "2024-06-15T15:00:00"
        assert parts[0]["appointment_start_utc"] == ""


class TestParticipantNormalization:
    @pytest.mark.asyncio
    async def test_update_participant_email_recomputes_progress_key(self):
        cid = await mc.create_campaign({"name": "Norm1"})
        await mc.upsert_participant(
            cid, "norm-1", "Alice", "alice@test.com", "10:00", "2026-03-23",
        )

        await mc.update_participant_field(
            cid,
            "norm-1",
            "email",
            "alice+updated@test.com",
        )

        participant = (await mc.get_participants_for_campaign(cid, "2026-03-23"))[0]
        assert participant["progress_key"] == "email:alice+updated@test.com"

    @pytest.mark.asyncio
    async def test_update_participant_identity_and_schedule_resets_manualized_schedule_fields(self):
        cid = await mc.create_campaign({"name": "Norm2"})
        await mc.upsert_participant(
            cid,
            "norm-2",
            "Alice",
            "alice@test.com",
            "09:15",
            "2026-03-23",
            appointment_start_raw="2026-03-23T09:15:00-07:00",
            appointment_start_utc="2026-03-23T16:15:00+00:00",
            appointment_timezone="America/Los_Angeles",
            appointment_has_time=True,
        )

        await mc.update_participant_identity_and_schedule(
            cid,
            "norm-2",
            name="Alice Updated",
            email="alice.updated@test.com",
            appointment_date="2026-03-24",
            appointment_time="11:45",
        )

        participant = (await mc.get_participants_for_campaign(cid, "2026-03-24"))[0]
        assert participant["name"] == "Alice Updated"
        assert participant["progress_key"] == "email:alice.updated@test.com"
        assert participant["appointment_start_raw"] == "2026-03-24T11:45:00"
        assert participant["appointment_start_utc"] == ""
        assert participant["appointment_timezone"] == ""
        assert participant["appointment_sort_key"] == "2026-03-24T11:45:00"

    @pytest.mark.asyncio
    async def test_legacy_rows_get_derived_fields_when_loaded(self):
        cid = await mc.create_campaign({"name": "Norm3"})
        await mc._participants().insert_one({
            "campaign_id": cid,
            "google_event_id": "norm-3",
            "name": "Legacy",
            "email": "legacy@test.com",
            "appointment_date": "2026-03-23",
            "appointment_time": "08:30",
            "status": "Booked",
        })

        participant = (await mc.get_participants_for_campaign(cid, "2026-03-23"))[0]

        assert participant["progress_key"] == "email:legacy@test.com"
        assert participant["appointment_start_raw"] == "2026-03-23T08:30:00"
        assert participant["appointment_sort_key"] == "2026-03-23T08:30:00"


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
        # 3 unique participants over 2 dates
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
        """Same email across two dates counts as 1 unique campaign participant."""
        cid = await mc.create_campaign({"name": "Prog3"})
        await mc.upsert_participant(cid, "e-d1", "X", "x@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e-d2", "X", "x@t.com", "10:00", "2024-06-16")

        result = await mc.get_campaign_progress(cid)
        assert result["booked"] == 1  # deduplicated by email

    @pytest.mark.asyncio
    async def test_completed_is_deduplicated_by_email(self):
        cid = await mc.create_campaign({"name": "Prog4"})
        await mc.upsert_participant(cid, "e4-1", "Y", "y@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e4-2", "Y", "y@t.com", "10:00", "2024-06-16")
        await mc.update_participant_status(cid, "e4-2", "Completed")

        result = await mc.get_campaign_progress(cid)
        assert result == {"booked": 1, "completed": 1}

    @pytest.mark.asyncio
    async def test_blank_email_rows_do_not_deduplicate(self):
        cid = await mc.create_campaign({"name": "Prog5"})
        await mc.upsert_participant(cid, "e5-1", "Z", "", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e5-2", "Z", "", "10:00", "2024-06-16")

        result = await mc.get_campaign_progress(cid)
        assert result == {"booked": 2, "completed": 0}


class TestExportCSV:
    @pytest.mark.asyncio
    async def test_issue_comment_in_export(self):
        cid = await mc.create_campaign({"name": "Export1"})
        await mc.upsert_participant(cid, "ex-1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.update_participant_field(cid, "ex-1", "issue_comment", "Had issue")

        rows = await mc.get_participants_for_export(cid)
        assert len(rows) == 1
        assert rows[0]["issue_comment"] == "Had issue"

    @pytest.mark.asyncio
    async def test_export_can_be_limited_to_selected_date(self):
        cid = await mc.create_campaign({"name": "Export2"})
        await mc.upsert_participant(cid, "ex-2a", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "ex-2b", "B", "b@t.com", "11:00", "2024-06-16")

        rows = await mc.get_participants_for_export(cid, "2024-06-15")

        assert len(rows) == 1
        assert rows[0]["date"] == "2024-06-15"
        assert rows[0]["name"] == "A"

    @pytest.mark.asyncio
    async def test_export_rows_are_sorted_by_date_then_time(self):
        cid = await mc.create_campaign({"name": "Export3"})
        await mc.upsert_participant(cid, "ex-3b", "Later", "later@t.com", "12:00", "2024-06-15")
        await mc.upsert_participant(cid, "ex-3a", "Earlier", "earlier@t.com", "09:00", "2024-06-15")
        await mc.upsert_participant(cid, "ex-3c", "NextDay", "next@t.com", "08:00", "2024-06-16")

        rows = await mc.get_participants_for_export(cid)

        assert [row["name"] for row in rows] == ["Earlier", "Later", "NextDay"]


class TestAdminPinSecurity:
    @pytest.mark.asyncio
    async def test_hash_and_verify_admin_pin(self):
        stored = mc.hash_admin_pin("2468")

        assert stored.startswith(f"{mc.PIN_HASH_ALGO}$")
        assert stored != mc.hash_admin_pin("2468")

        is_valid, needs_upgrade = mc.verify_admin_pin("2468", stored)
        assert is_valid is True
        assert needs_upgrade is False

    @pytest.mark.asyncio
    async def test_verify_admin_pin_marks_old_iterations_for_upgrade(self):
        stored = mc.hash_admin_pin("2468", iterations=10_000)

        is_valid, needs_upgrade = mc.verify_admin_pin("2468", stored)
        assert is_valid is True
        assert needs_upgrade is True

    @pytest.mark.asyncio
    async def test_verify_admin_pin_accepts_legacy_sha256_and_requests_upgrade(self):
        legacy = hashlib.sha256("2468".encode("utf-8")).hexdigest()

        is_valid, needs_upgrade = mc.verify_admin_pin("2468", legacy)
        assert is_valid is True
        assert needs_upgrade is True


class TestAdminAuditLog:
    @pytest.mark.asyncio
    async def test_record_audit_event_roundtrip(self):
        await mc.record_audit_event(
            action="delete_campaign",
            summary="Deleted campaign 'Alpha'.",
            resource_type="campaign",
            resource_id="camp-1",
            resource_label="Alpha",
            metadata={"participant_count": 12},
        )

        events = await mc.get_recent_audit_events(limit=5)
        assert len(events) == 1
        assert events[0]["action"] == "delete_campaign"
        assert events[0]["summary"] == "Deleted campaign 'Alpha'."
        assert events[0]["resource_type"] == "campaign"
        assert events[0]["resource_id"] == "camp-1"
        assert events[0]["resource_label"] == "Alpha"
        assert events[0]["metadata"] == {"participant_count": 12}
        assert events[0]["actor_role"] == "admin"

    @pytest.mark.asyncio
    async def test_recent_audit_events_are_sorted_newest_first(self):
        await mc.record_audit_event(
            action="older",
            summary="Older event.",
        )
        await mc.record_audit_event(
            action="newer",
            summary="Newer event.",
        )

        events = await mc.get_recent_audit_events(limit=2)
        assert [event["action"] for event in events] == ["newer", "older"]


class TestSettingsUsageGuards:
    @pytest.mark.asyncio
    async def test_get_platform_usage_counts_campaigns_and_participants(self):
        cid = await mc.create_campaign({
            "name": "Usage1",
            "device_types": ["Orb", "Kiosk-v2"],
            "default_platform": "Orb",
        })
        await mc.upsert_participant(
            cid, "usage-p1", "Alex", "alex@test.com", "10:00", "2026-03-23",
        )
        await mc.update_participant_field(cid, "usage-p1", "platform", "Orb")

        usage = await mc.get_platform_usage("Orb")

        assert usage == {
            "campaign_device_type_count": 1,
            "campaign_default_count": 1,
            "participant_count": 1,
        }

    @pytest.mark.asyncio
    async def test_get_platform_model_tag_usage_counts_exact_and_shared_defaults(self):
        exact_cid = await mc.create_campaign({
            "name": "Usage2",
            "device_types": ["Orb"],
            "default_platform": "Orb",
            "default_model_tag": "beta",
        })
        shared_cid = await mc.create_campaign({
            "name": "Usage3",
            "device_types": ["Orb", "Kiosk-v2"],
            "default_platform": "",
            "default_model_tag": "beta",
        })
        await mc.upsert_participant(
            exact_cid, "usage-p2", "Blake", "blake@test.com", "11:00", "2026-03-23",
        )
        await mc.update_participant_field(exact_cid, "usage-p2", "platform", "Orb")
        await mc.update_participant_field(exact_cid, "usage-p2", "model_tag", "beta")

        usage = await mc.get_platform_model_tag_usage("Orb", "beta")

        assert usage == {
            "participant_count": 1,
            "campaign_default_count": 1,
            "campaign_shared_default_count": 1,
        }
        assert shared_cid != exact_cid


class TestSyncedDates:
    @pytest.mark.asyncio
    async def test_get_synced_dates(self):
        cid = await mc.create_campaign({"name": "Sync1"})
        await mc.upsert_participant(cid, "s-1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "s-2", "B", "b@t.com", "11:00", "2024-06-16")
        await mc.upsert_participant(cid, "s-3", "C", "c@t.com", "12:00", "2024-06-15")

        dates = await mc.get_synced_dates_for_campaign(cid)
        assert sorted(dates) == ["2024-06-15", "2024-06-16"]


class TestCampaignSyncMetadata:
    @pytest.mark.asyncio
    async def test_update_campaign_sync_state_records_attempt_and_failure(self):
        cid = await mc.create_campaign({"name": "SyncMeta1"})

        await mc.update_campaign_sync_state(
            cid,
            attempt_at="2026-03-23T08:00:00",
            error_code="missing_token",
            error_summary="Google token is missing for this environment.",
            error_detail="No valid token.json - cannot open browser in Docker.",
        )

        doc = await mc.get_campaign(cid)
        assert doc["last_sync_attempt_at"] == "2026-03-23T08:00:00"
        assert doc["last_sync_success_at"] is None
        assert doc["last_sync_at"] is None
        assert doc["last_sync_error_code"] == "missing_token"
        assert doc["last_sync_error"] == "Google token is missing for this environment."
        assert doc["last_sync_error_detail"] == "No valid token.json - cannot open browser in Docker."

    @pytest.mark.asyncio
    async def test_update_campaign_sync_state_success_clears_error_and_sets_legacy_field(self):
        cid = await mc.create_campaign({"name": "SyncMeta2"})
        await mc.update_campaign_sync_state(
            cid,
            attempt_at="2026-03-23T08:00:00",
            error_code="missing_token",
            error_summary="Google token is missing for this environment.",
            error_detail="No valid token.json - cannot open browser in Docker.",
        )

        await mc.update_campaign_sync_state(
            cid,
            attempt_at="2026-03-23T08:15:00",
            success_at="2026-03-23T08:16:00",
            error_code="",
            error_summary="",
            error_detail="",
        )

        doc = await mc.get_campaign(cid)
        assert doc["last_sync_attempt_at"] == "2026-03-23T08:15:00"
        assert doc["last_sync_success_at"] == "2026-03-23T08:16:00"
        assert doc["last_sync_at"] == "2026-03-23T08:16:00"
        assert doc["last_sync_error_code"] == ""
        assert doc["last_sync_error"] == ""
        assert doc["last_sync_error_detail"] == ""
