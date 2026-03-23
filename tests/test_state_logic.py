"""
Tests for state.py computed-var logic.

These test the pure-Python logic extracted from NexusState computed vars
without needing the Reflex runtime. We instantiate a minimal mock that
mirrors the state vars, then call the property bodies directly.
"""

import pytest
from datetime import datetime

from nexus_track.state import (
    _build_app_refresh_health,
    _build_campaign_sync_health,
    _build_export_filename,
    _build_range_sync_result_message,
    _build_sync_result_message,
    _compute_campaign_progress_from_participants,
    _compute_per_device_progress_from_participants,
    _compute_platform_model_breakdown_from_participants,
    _count_issue_participants,
    _dashboard_day_metric_label,
    _display_date_label,
    _filter_selection_to_visible,
    _issue_filter_label,
    _issue_preview_text,
    _issue_summary_label,
    _participant_empty_state,
    _participants_for_scope,
    _resolve_sync_error,
)


# ---------------------------------------------------------------------------
# Lightweight mock replicating NexusState computed logic
# ---------------------------------------------------------------------------

class _MockState:
    """
    Replicate the computed-var logic from NexusState so we can test
    percentage calculations and milestones without Reflex overhead.
    """

    def __init__(
        self,
        current_campaign: dict | None = None,
        selected_date: str = "",
    ):
        self.current_campaign = current_campaign or {}
        self.selected_date = selected_date

    # -- Extracted from state.py @rx.var properties --

    @property
    def campaign_goal(self) -> int:
        return self.current_campaign.get("goal", 100)

    @property
    def campaign_booked(self) -> int:
        return self.current_campaign.get("booked", 0)

    @property
    def campaign_completed_all(self) -> int:
        return self.current_campaign.get("completed_all", 0)

    @property
    def booked_pct(self) -> int:
        g = self.campaign_goal
        return min(100, int(self.campaign_booked / g * 100)) if g else 0

    @property
    def completed_pct(self) -> int:
        g = self.campaign_goal
        return min(100, int(self.campaign_completed_all / g * 100)) if g else 0

    @property
    def milestone_quarter(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal * 0.25

    @property
    def milestone_half(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal * 0.5

    @property
    def milestone_three_quarter(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal * 0.75

    @property
    def milestone_complete(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal

    @property
    def display_date_label(self) -> str:
        return _display_date_label(self.selected_date or datetime.now().strftime("%Y-%m-%d"))

    @property
    def campaign_last_sync(self) -> str:
        return str(
            _build_campaign_sync_health(self.current_campaign).get(
                "sync_last_success_display",
                "Never",
            ),
        )


# ---------------------------------------------------------------------------
# Progress percentage tests
# ---------------------------------------------------------------------------

class TestProgressPercentages:
    def test_zero_goal(self):
        s = _MockState({"goal": 0, "booked": 10, "completed_all": 5})
        assert s.booked_pct == 0
        assert s.completed_pct == 0

    def test_basic_pct(self):
        s = _MockState({"goal": 100, "booked": 80, "completed_all": 50})
        assert s.booked_pct == 80
        assert s.completed_pct == 50

    def test_clamped_at_100(self):
        s = _MockState({"goal": 50, "booked": 200, "completed_all": 60})
        assert s.booked_pct == 100  # min(100, 400) => 100
        assert s.completed_pct == 100

    def test_fractional_truncated(self):
        s = _MockState({"goal": 3, "booked": 1, "completed_all": 1})
        assert s.booked_pct == 33  # int(1/3*100) = 33
        assert s.completed_pct == 33

    def test_default_goal_100(self):
        s = _MockState({})  # no goal key
        assert s.campaign_goal == 100


# ---------------------------------------------------------------------------
# Milestone tests
# ---------------------------------------------------------------------------

class TestMilestones:
    def test_no_milestones(self):
        s = _MockState({"goal": 100, "completed_all": 0})
        assert not s.milestone_quarter
        assert not s.milestone_half
        assert not s.milestone_three_quarter
        assert not s.milestone_complete

    def test_quarter_reached(self):
        s = _MockState({"goal": 100, "completed_all": 25})
        assert s.milestone_quarter
        assert not s.milestone_half

    def test_half_reached(self):
        s = _MockState({"goal": 100, "completed_all": 50})
        assert s.milestone_quarter
        assert s.milestone_half
        assert not s.milestone_three_quarter

    def test_three_quarter_reached(self):
        s = _MockState({"goal": 100, "completed_all": 75})
        assert s.milestone_quarter
        assert s.milestone_half
        assert s.milestone_three_quarter
        assert not s.milestone_complete

    def test_complete(self):
        s = _MockState({"goal": 100, "completed_all": 100})
        assert s.milestone_quarter
        assert s.milestone_half
        assert s.milestone_three_quarter
        assert s.milestone_complete

    def test_over_complete(self):
        """Exceeding goal still registers all milestones."""
        s = _MockState({"goal": 50, "completed_all": 80})
        assert s.milestone_complete

    def test_edge_just_below_quarter(self):
        s = _MockState({"goal": 100, "completed_all": 24})
        assert not s.milestone_quarter

    def test_non_round_goal(self):
        s = _MockState({"goal": 7, "completed_all": 2})
        # 0.25*7=1.75, so 2 >= 1.75 => True
        assert s.milestone_quarter
        # 0.5*7=3.5, so 2 < 3.5 => False
        assert not s.milestone_half


# ---------------------------------------------------------------------------
# Date label fix tests
# ---------------------------------------------------------------------------

class TestDisplayDateLabel:
    def test_empty_date_shows_today(self):
        s = _MockState(selected_date="")
        label = s.display_date_label
        assert "Today" in label

    def test_today_date_shows_today(self):
        today_str = datetime.now().strftime("%Y-%m-%d")
        s = _MockState(selected_date=today_str)
        label = s.display_date_label
        assert "Today" in label

    def test_past_date_no_today(self):
        s = _MockState(selected_date="2024-01-15")
        label = s.display_date_label
        assert "Today" not in label
        assert "January 15" in label

    def test_invalid_date_returned_as_is(self):
        s = _MockState(selected_date="not-a-date")
        assert s.display_date_label == "not-a-date"


# ---------------------------------------------------------------------------
# Last sync label
# ---------------------------------------------------------------------------

class TestLastSync:
    def test_empty(self):
        s = _MockState({})
        assert s.campaign_last_sync == "Never"

    def test_iso_format(self):
        s = _MockState({"last_sync_at": "2024-06-15T14:30:00+00:00"})
        label = s.campaign_last_sync
        assert "Jun 15" in label
        assert "14:30" in label

    def test_invalid_returns_raw(self):
        s = _MockState({"last_sync_at": "bad-date"})
        assert s.campaign_last_sync == "bad-date"


class TestCampaignSyncHealthHelpers:
    def test_never_synced_campaign_needs_attention(self):
        sync = _build_campaign_sync_health({}, now=datetime(2026, 3, 23, 12, 0, 0))

        assert sync["sync_health_state"] == "never"
        assert sync["sync_health_label"] == "Never synced"
        assert sync["sync_needs_attention"] is True
        assert sync["sync_last_success_display"] == "Never"

    def test_recent_success_is_fresh(self):
        sync = _build_campaign_sync_health(
            {"last_sync_success_at": "2026-03-23T11:30:00"},
            now=datetime(2026, 3, 23, 12, 0, 0),
        )

        assert sync["sync_health_state"] == "fresh"
        assert sync["sync_health_label"] == "Fresh"
        assert sync["sync_needs_attention"] is False
        assert "11:30" in str(sync["sync_last_success_display"])

    def test_old_success_is_stale(self):
        sync = _build_campaign_sync_health(
            {"last_sync_success_at": "2026-03-23T09:30:00"},
            now=datetime(2026, 3, 23, 12, 0, 0),
        )

        assert sync["sync_health_state"] == "stale"
        assert sync["sync_health_label"] == "Stale"
        assert sync["sync_needs_attention"] is True
        assert "Refresh this campaign" in str(sync["sync_secondary_message"])

    def test_failed_attempt_stays_red_until_a_new_success(self):
        sync = _build_campaign_sync_health(
            {
                "last_sync_success_at": "2026-03-23T10:00:00",
                "last_sync_attempt_at": "2026-03-23T11:45:00",
                "last_sync_error_code": "missing_token",
                "last_sync_error": "Google token is missing for this environment.",
                "last_sync_error_detail": "No valid token.json - cannot open browser in Docker.",
            },
            now=datetime(2026, 3, 23, 12, 0, 0),
        )

        assert sync["sync_health_state"] == "failed"
        assert sync["sync_health_label"] == "Sync failed"
        assert sync["sync_needs_attention"] is True
        assert sync["sync_show_last_attempt"] is True
        assert "Google token is missing" in str(sync["sync_primary_message"])
        assert "Last successful sync" in str(sync["sync_last_success_primary"])


class TestSyncErrorGuidance:
    def test_missing_token_error_maps_to_actionable_guidance(self):
        guidance = _resolve_sync_error(
            "No valid token.json - cannot open browser in Docker.",
        )

        assert guidance["code"] == "missing_token"
        assert "Google token is missing" in guidance["summary"]
        assert "generate_token.py" in guidance["action"]

    def test_missing_credentials_error_maps_to_project_root_action(self):
        guidance = _resolve_sync_error(
            "credentials.json not found. Download OAuth 2.0 Desktop credentials from Google Cloud Console.",
        )

        assert guidance["code"] == "missing_credentials"
        assert "credentials are missing" in guidance["summary"]
        assert "project root" in guidance["action"]


class TestAppRefreshHealth:
    def test_live_refresh_requires_recent_success(self):
        health = _build_app_refresh_health(
            "2026-03-23T11:59:45",
            "",
            "",
            now=datetime(2026, 3, 23, 12, 0, 0),
        )

        assert health["state"] == "live"
        assert health["label"] == "Live data"

    def test_old_refresh_is_delayed(self):
        health = _build_app_refresh_health(
            "2026-03-23T11:57:00",
            "",
            "",
            now=datetime(2026, 3, 23, 12, 0, 0),
        )

        assert health["state"] == "delayed"
        assert health["label"] == "Refresh delayed"

    def test_newer_error_than_refresh_stays_red(self):
        health = _build_app_refresh_health(
            "2026-03-23T11:55:00",
            "2026-03-23T11:59:30",
            "Mongo refresh failed",
            now=datetime(2026, 3, 23, 12, 2, 0),
        )

        assert health["state"] == "error"
        assert health["label"] == "Refresh error"
        assert "Mongo refresh failed" in health["title"]

    def test_recent_error_does_not_flip_back_to_live_without_new_success(self):
        health = _build_app_refresh_health(
            "2026-03-23T11:59:55",
            "2026-03-23T12:00:05",
            "Mongo refresh failed",
            now=datetime(2026, 3, 23, 12, 0, 10),
        )

        assert health["state"] == "error"
        assert health["label"] == "Refresh error"


class TestParticipantAggregationHelpers:
    def test_campaign_progress_deduplicates_by_email(self):
        participants = [
            {"google_event_id": "e1", "email": "same@test.com", "status": "Booked"},
            {"google_event_id": "e2", "email": "same@test.com", "status": "Completed"},
            {"google_event_id": "e3", "email": "other@test.com", "status": "Booked"},
        ]

        assert _compute_campaign_progress_from_participants(participants) == {
            "booked": 2,
            "completed": 1,
        }

    def test_campaign_progress_uses_event_id_when_email_is_blank(self):
        participants = [
            {"google_event_id": "e1", "email": "", "status": "Completed"},
            {"google_event_id": "e2", "email": "", "status": "Booked"},
        ]

        assert _compute_campaign_progress_from_participants(participants) == {
            "booked": 2,
            "completed": 1,
        }

    def test_per_device_progress_counts_totals_and_completed(self):
        participants = [
            {"platform": "Orb", "status": "Booked"},
            {"platform": "Orb", "status": "Completed"},
            {"platform": "Kiosk-v2", "status": "Completed"},
            {"platform": "", "status": "Completed"},
        ]

        assert _compute_per_device_progress_from_participants(participants) == {
            "Orb": {"total": 2, "completed": 1},
            "Kiosk-v2": {"total": 1, "completed": 1},
        }

    def test_platform_model_breakdown_groups_by_platform_and_model(self):
        participants = [
            {"platform": "Orb", "model_tag": "v5.0", "status": "Booked"},
            {"platform": "Orb", "model_tag": "v5.0", "status": "Completed"},
            {"platform": "Orb", "model_tag": "", "status": "Completed"},
            {"platform": "Kiosk-v2", "model_tag": "beta", "status": "Completed"},
        ]

        assert _compute_platform_model_breakdown_from_participants(participants) == {
            "Orb": {
                "v5.0": {"total": 2, "completed": 1},
                "": {"total": 1, "completed": 1},
            },
            "Kiosk-v2": {
                "beta": {"total": 1, "completed": 1},
            },
        }


class TestSelectionScopeHelpers:
    def test_filter_selection_to_visible_drops_hidden_ids(self):
        selected_ids = ["evt-1", "evt-2", "evt-3"]
        visible_ids = ["evt-2", "evt-4"]

        assert _filter_selection_to_visible(selected_ids, visible_ids) == ["evt-2"]

    def test_filter_selection_to_visible_preserves_selected_order(self):
        selected_ids = ["evt-3", "evt-1", "evt-2"]
        visible_ids = ["evt-1", "evt-2", "evt-3"]

        assert _filter_selection_to_visible(selected_ids, visible_ids) == [
            "evt-3",
            "evt-1",
            "evt-2",
        ]

    def test_participants_for_scope_limits_selected_day_only(self):
        participants = [
            {"google_event_id": "evt-1", "appointment_date": "2026-03-23"},
            {"google_event_id": "evt-2", "appointment_date": "2026-03-24"},
        ]

        scoped = _participants_for_scope(
            participants,
            "selected_day",
            "2026-03-23",
        )

        assert scoped == [{"google_event_id": "evt-1", "appointment_date": "2026-03-23"}]

    def test_participants_for_scope_keeps_all_dates_mode(self):
        participants = [
            {"google_event_id": "evt-1", "appointment_date": "2026-03-23"},
            {"google_event_id": "evt-2", "appointment_date": "2026-03-24"},
        ]

        scoped = _participants_for_scope(
            participants,
            "all_dates",
            "2026-03-23",
        )

        assert scoped == participants


class TestIssueHelpers:
    def test_count_issue_participants_ignores_blank_comments(self):
        participants = [
            {"issue_comment": "Late arrival"},
            {"issue_comment": "   "},
            {"issue_comment": ""},
            {"issue_comment": "Device mismatch"},
        ]

        assert _count_issue_participants(participants) == 2

    def test_issue_preview_text_collapses_whitespace(self):
        preview = _issue_preview_text("  Device   failed\nwhile   scanning   ")

        assert preview == "Device failed while scanning"

    def test_issue_preview_text_truncates_long_comments(self):
        long_comment = (
            "Participant had a device swap, then a second verification mismatch, "
            "and needed manual follow-up before completion."
        )

        preview = _issue_preview_text(long_comment, limit=50)

        assert preview.endswith("…")
        assert len(preview) == 50

    def test_issue_filter_label_uses_visible_and_total_counts(self):
        label = _issue_filter_label(
            4,
            2,
            participant_view_is_filtered=True,
        )

        assert label == "Issues only (2/4)"

    def test_issue_summary_label_uses_singular_when_needed(self):
        label = _issue_summary_label(
            1,
            1,
            participant_view_is_filtered=False,
        )

        assert label == "1 issue in view"

    def test_participant_empty_state_distinguishes_issue_filters(self):
        title, description = _participant_empty_state(
            total_participants=8,
            visible_participants=0,
            total_issues=3,
            filter_has_issue=True,
            participant_scope_mode="all_dates",
        )

        assert title == "No issues match the current view"
        assert "bring flagged participants back into view" in description

    def test_participant_empty_state_handles_no_issues_yet(self):
        title, description = _participant_empty_state(
            total_participants=8,
            visible_participants=0,
            total_issues=0,
            filter_has_issue=True,
            participant_scope_mode="all_dates",
        )

        assert title == "No flagged issues yet"
        assert "Flag an issue" in description

    def test_participant_empty_state_handles_selected_day_scope(self):
        title, description = _participant_empty_state(
            total_participants=8,
            visible_participants=0,
            total_issues=0,
            filter_has_issue=False,
            participant_scope_mode="selected_day",
        )

        assert title == "No participants on the selected day"
        assert "switch to All dates" in description or "Switch to All dates" in description


class TestScopeMessagingHelpers:
    def test_dashboard_day_metric_label_uses_day_for_non_today(self):
        assert _dashboard_day_metric_label("1999-01-01") == "Day"

    def test_build_sync_result_message_includes_absolute_date(self):
        message = _build_sync_result_message(3, "2026-03-23")

        assert message == "Synced 3 events for Monday, March 23, 2026."

    def test_build_range_sync_result_message_includes_range(self):
        message = _build_range_sync_result_message(
            5,
            2,
            "2026-03-23",
            "2026-03-24",
        )

        assert "Monday, March 23, 2026" in message
        assert "Tuesday, March 24, 2026" in message
        assert "5 events" in message

    def test_build_export_filename_includes_scope_and_date_when_needed(self):
        filename = _build_export_filename(
            "Internal Collection Dashboard",
            "current_filters_selected_day",
            "2026-03-23",
        )

        assert filename == "internal_collection_dashboard_current_filters_selected_day_2026-03-23.csv"
