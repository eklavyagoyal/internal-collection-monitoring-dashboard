"""Pure helper tests for timezone-safe Google Calendar normalization."""

import pytest

from nexus_track.backend import gcal_sync
from nexus_track.backend.gcal_sync import (
    _calendar_day_bounds,
    _normalize_google_event_start,
    _resolve_timezone_name,
)


class TestCalendarTimezoneHelpers:
    def test_resolve_timezone_name_falls_back_to_utc_for_unknown_timezones(self):
        assert _resolve_timezone_name("Mars/Olympus") == "UTC"

    def test_calendar_day_bounds_use_calendar_timezone_not_server_timezone(self):
        start, end, target_date = _calendar_day_bounds(
            "2026-03-23",
            "America/Los_Angeles",
        )

        assert target_date == "2026-03-23"
        assert start.isoformat() == "2026-03-23T00:00:00-07:00"
        assert end.isoformat() == "2026-03-24T00:00:00-07:00"


class TestGoogleEventStartNormalization:
    def test_timed_event_is_normalized_into_calendar_timezone_fields(self):
        normalized = _normalize_google_event_start(
            {"dateTime": "2026-03-23T16:15:00-07:00"},
            calendar_timezone="America/Los_Angeles",
        )

        assert normalized == {
            "appointment_date": "2026-03-23",
            "appointment_time": "16:15",
            "appointment_start_raw": "2026-03-23T16:15:00-07:00",
            "appointment_start_utc": "2026-03-23T23:15:00+00:00",
            "appointment_timezone": "America/Los_Angeles",
            "appointment_has_time": True,
        }

    def test_timed_event_with_zulu_offset_keeps_same_moment_in_utc(self):
        normalized = _normalize_google_event_start(
            {"dateTime": "2026-03-23T23:30:00Z"},
            calendar_timezone="UTC",
        )

        assert normalized["appointment_date"] == "2026-03-23"
        assert normalized["appointment_time"] == "23:30"
        assert normalized["appointment_start_utc"] == "2026-03-23T23:30:00+00:00"
        assert normalized["appointment_timezone"] == "UTC"

    def test_all_day_event_keeps_date_and_explicitly_has_no_time(self):
        normalized = _normalize_google_event_start(
            {"date": "2026-03-23"},
            calendar_timezone="Europe/Berlin",
        )

        assert normalized == {
            "appointment_date": "2026-03-23",
            "appointment_time": "",
            "appointment_start_raw": "2026-03-23",
            "appointment_start_utc": "",
            "appointment_timezone": "Europe/Berlin",
            "appointment_has_time": False,
        }


class TestCampaignSync:
    @pytest.mark.asyncio
    async def test_sync_calendar_for_campaign_uses_requested_date(self, monkeypatch):
        seen: dict[str, str | None] = {}

        async def fake_ensure_indexes():
            return None

        def fake_fetch_events_for_date(calendar_id: str = "primary", date_str: str | None = None):
            seen["calendar_id"] = calendar_id
            seen["date_str"] = date_str
            return []

        async def fake_upsert_participant(**kwargs):
            raise AssertionError("upsert_participant should not be called when there are no events")

        monkeypatch.setattr(gcal_sync, "ensure_indexes", fake_ensure_indexes)
        monkeypatch.setattr(gcal_sync, "_fetch_events_for_date", fake_fetch_events_for_date)
        monkeypatch.setattr(gcal_sync, "upsert_participant", fake_upsert_participant)

        synced = await gcal_sync.sync_calendar_for_campaign(
            {
                "campaign_id": "camp-123",
                "calendar_id": "team-calendar@group.calendar.google.com",
            },
            "2026-04-02",
        )

        assert synced == 0
        assert seen == {
            "calendar_id": "team-calendar@group.calendar.google.com",
            "date_str": "2026-04-02",
        }
