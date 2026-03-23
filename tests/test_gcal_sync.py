"""Pure helper tests for timezone-safe Google Calendar normalization."""

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
