"""
Tests for state.py computed-var logic.

These test the pure-Python logic extracted from NexusState computed vars
without needing the Reflex runtime. We instantiate a minimal mock that
mirrors the state vars, then call the property bodies directly.
"""

import pytest
from datetime import datetime


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
        d = self.selected_date
        today = datetime.now().date()
        if not d:
            label = today.strftime("%A, %B %d")
            return f"{label} · Today"
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return d
        label = dt.strftime("%A, %B %d")
        return f"{label} · Today" if dt == today else label

    @property
    def campaign_last_sync(self) -> str:
        raw = self.current_campaign.get("last_sync_at", "")
        if not raw:
            return ""
        try:
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%b %d, %H:%M")
        except Exception:
            return raw


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
        assert s.campaign_last_sync == ""

    def test_iso_format(self):
        s = _MockState({"last_sync_at": "2024-06-15T14:30:00+00:00"})
        label = s.campaign_last_sync
        assert "Jun 15" in label
        assert "14:30" in label

    def test_invalid_returns_raw(self):
        s = _MockState({"last_sync_at": "bad-date"})
        assert s.campaign_last_sync == "bad-date"
