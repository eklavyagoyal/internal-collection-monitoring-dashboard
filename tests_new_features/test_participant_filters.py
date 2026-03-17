"""Tests for participant filter logic (Phase 2.3).

The filters live in NexusState computed vars, which need the full Reflex
runtime. These tests verify the filter *logic* as standalone functions
extracted from the computed var implementation to ensure correctness.
"""

import pytest


def _filter_participants(
    items: list[dict],
    search_query: str = "",
    filter_platform: str = "",
    filter_status: str = "",
    filter_date: str = "",
    filter_has_issue: bool = False,
    sort_field: str = "appointment_time",
    sort_dir: str = "asc",
) -> list[dict]:
    """Mirror of NexusState.sorted_filtered_participants logic."""
    if search_query:
        q = search_query.lower()
        items = [
            p for p in items
            if q in p.get("name", "").lower()
            or q in p.get("email", "").lower()
            or q in p.get("platform", "").lower()
            or q in p.get("model_tag", "").lower()
            or q in p.get("notes", "").lower()
        ]
    if filter_platform:
        items = [p for p in items if p.get("platform", "") == filter_platform]
    if filter_status:
        items = [p for p in items if p.get("status", "") == filter_status]
    if filter_date:
        items = [p for p in items if p.get("appointment_date", "") == filter_date]
    if filter_has_issue:
        items = [p for p in items if p.get("issue_comment", "").strip()]
    field = sort_field or "appointment_time"
    reverse = sort_dir == "desc"
    try:
        items = sorted(items, key=lambda p: (p.get(field) or "").lower(), reverse=reverse)
    except Exception:
        pass
    return items


PARTICIPANTS = [
    {"name": "Alice", "email": "a@t.co", "platform": "iOS", "status": "Completed",
     "appointment_date": "2025-01-01", "appointment_time": "10:00",
     "model_tag": "v5.0", "notes": "", "issue_comment": ""},
    {"name": "Bob", "email": "b@t.co", "platform": "Android", "status": "Booked",
     "appointment_date": "2025-01-01", "appointment_time": "11:00",
     "model_tag": "v4.6", "notes": "test note", "issue_comment": "bug found"},
    {"name": "Charlie", "email": "c@t.co", "platform": "iOS", "status": "Booked",
     "appointment_date": "2025-01-02", "appointment_time": "09:00",
     "model_tag": "v5.0", "notes": "", "issue_comment": ""},
    {"name": "Diana", "email": "d@t.co", "platform": "Orb", "status": "Completed",
     "appointment_date": "2025-01-02", "appointment_time": "14:00",
     "model_tag": "beta", "notes": "", "issue_comment": "camera issue"},
]


class TestPlatformFilter:
    def test_filter_ios(self):
        result = _filter_participants(PARTICIPANTS, filter_platform="iOS")
        assert len(result) == 2
        assert all(p["platform"] == "iOS" for p in result)

    def test_filter_android(self):
        result = _filter_participants(PARTICIPANTS, filter_platform="Android")
        assert len(result) == 1
        assert result[0]["name"] == "Bob"

    def test_no_filter_returns_all(self):
        result = _filter_participants(PARTICIPANTS)
        assert len(result) == 4


class TestStatusFilter:
    def test_filter_completed(self):
        result = _filter_participants(PARTICIPANTS, filter_status="Completed")
        assert len(result) == 2
        assert all(p["status"] == "Completed" for p in result)

    def test_filter_booked(self):
        result = _filter_participants(PARTICIPANTS, filter_status="Booked")
        assert len(result) == 2


class TestDateFilter:
    def test_filter_specific_date(self):
        result = _filter_participants(PARTICIPANTS, filter_date="2025-01-01")
        assert len(result) == 2

    def test_filter_other_date(self):
        result = _filter_participants(PARTICIPANTS, filter_date="2025-01-02")
        assert len(result) == 2


class TestIssueFilter:
    def test_filter_has_issue(self):
        result = _filter_participants(PARTICIPANTS, filter_has_issue=True)
        assert len(result) == 2
        names = {p["name"] for p in result}
        assert names == {"Bob", "Diana"}

    def test_no_issue_filter(self):
        result = _filter_participants(PARTICIPANTS, filter_has_issue=False)
        assert len(result) == 4


class TestSearchFilter:
    def test_search_by_name(self):
        result = _filter_participants(PARTICIPANTS, search_query="alice")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_search_by_email(self):
        result = _filter_participants(PARTICIPANTS, search_query="b@t")
        assert len(result) == 1
        assert result[0]["name"] == "Bob"

    def test_search_by_notes(self):
        result = _filter_participants(PARTICIPANTS, search_query="test note")
        assert len(result) == 1

    def test_search_by_model_tag(self):
        result = _filter_participants(PARTICIPANTS, search_query="beta")
        assert len(result) == 1
        assert result[0]["name"] == "Diana"


class TestStackedFilters:
    def test_platform_and_status(self):
        result = _filter_participants(
            PARTICIPANTS, filter_platform="iOS", filter_status="Completed"
        )
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_date_and_issue(self):
        result = _filter_participants(
            PARTICIPANTS, filter_date="2025-01-02", filter_has_issue=True
        )
        assert len(result) == 1
        assert result[0]["name"] == "Diana"

    def test_all_filters_no_match(self):
        result = _filter_participants(
            PARTICIPANTS,
            filter_platform="Orb",
            filter_status="Booked",
        )
        assert len(result) == 0


class TestSorting:
    def test_sort_by_name_asc(self):
        result = _filter_participants(PARTICIPANTS, sort_field="name", sort_dir="asc")
        names = [p["name"] for p in result]
        assert names == ["Alice", "Bob", "Charlie", "Diana"]

    def test_sort_by_name_desc(self):
        result = _filter_participants(PARTICIPANTS, sort_field="name", sort_dir="desc")
        names = [p["name"] for p in result]
        assert names == ["Diana", "Charlie", "Bob", "Alice"]

    def test_sort_by_time_default(self):
        result = _filter_participants(PARTICIPANTS)
        times = [p["appointment_time"] for p in result]
        assert times == sorted(times)
