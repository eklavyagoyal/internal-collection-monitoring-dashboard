"""Tests for dashboard campaign filtering and sorting (Phase 2.4).

Mirrors NexusState.filtered_campaigns logic as standalone functions.
"""

import pytest


def _filter_campaigns(
    items: list[dict],
    campaign_search_query: str = "",
    campaign_device_filter: str = "",
    campaign_sort_field: str = "created_at",
) -> list[dict]:
    """Mirror of NexusState.filtered_campaigns logic."""
    if campaign_search_query:
        q = campaign_search_query.lower()
        items = [
            c for c in items
            if q in c.get("name", "").lower()
            or q in c.get("description", "").lower()
        ]

    if campaign_device_filter:
        items = [
            c for c in items
            if c.get("device_type", "Multi-device") == campaign_device_filter
        ]

    sf = campaign_sort_field
    if sf == "name":
        items = sorted(items, key=lambda c: c.get("name", "").lower())
    elif sf == "device_type":
        items = sorted(items, key=lambda c: c.get("device_type", ""))
    elif sf == "progress":
        items = sorted(
            items,
            key=lambda c: c.get("completed_all", 0) / max(c.get("goal", 1), 1),
            reverse=True,
        )
    # default: created_at — preserve original order
    return items


CAMPAIGNS = [
    {"name": "Alpha iOS", "description": "iOS collection", "device_type": "iOS",
     "goal": 100, "completed_all": 50, "created_at": "2025-01-01"},
    {"name": "Beta Android", "description": "Android collection", "device_type": "Android",
     "goal": 200, "completed_all": 180, "created_at": "2025-01-02"},
    {"name": "Gamma Multi", "description": "Multi-device run", "device_type": "Multi-device",
     "goal": 50, "completed_all": 50, "created_at": "2025-01-03"},
    {"name": "Delta Orb", "description": "Orb campaign", "device_type": "Orb",
     "goal": 100, "completed_all": 10, "created_at": "2025-01-04"},
]


class TestDeviceTypeFilter:
    def test_filter_ios(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_device_filter="iOS")
        assert len(result) == 1
        assert result[0]["name"] == "Alpha iOS"

    def test_filter_android(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_device_filter="Android")
        assert len(result) == 1
        assert result[0]["name"] == "Beta Android"

    def test_filter_multi_device(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_device_filter="Multi-device")
        assert len(result) == 1

    def test_no_filter_returns_all(self):
        result = _filter_campaigns(CAMPAIGNS)
        assert len(result) == 4


class TestCampaignSearch:
    def test_search_by_name(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_search_query="alpha")
        assert len(result) == 1

    def test_search_by_description(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_search_query="multi-device")
        assert len(result) == 1
        assert result[0]["name"] == "Gamma Multi"

    def test_search_no_match(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_search_query="zzzzz")
        assert len(result) == 0


class TestCampaignSort:
    def test_sort_by_name(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_sort_field="name")
        names = [c["name"] for c in result]
        assert names == ["Alpha iOS", "Beta Android", "Delta Orb", "Gamma Multi"]

    def test_sort_by_device_type(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_sort_field="device_type")
        types = [c["device_type"] for c in result]
        assert types == sorted(types)

    def test_sort_by_progress_desc(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_sort_field="progress")
        # Gamma: 50/50=1.0, Beta: 180/200=0.9, Alpha: 50/100=0.5, Delta: 10/100=0.1
        names = [c["name"] for c in result]
        assert names == ["Gamma Multi", "Beta Android", "Alpha iOS", "Delta Orb"]

    def test_sort_default_preserves_order(self):
        result = _filter_campaigns(CAMPAIGNS, campaign_sort_field="created_at")
        assert result == CAMPAIGNS


class TestCombinedFilterSort:
    def test_filter_then_sort(self):
        # Two iOS campaigns for this test
        campaigns = CAMPAIGNS + [
            {"name": "Epsilon iOS", "description": "", "device_type": "iOS",
             "goal": 100, "completed_all": 80, "created_at": "2025-01-05"},
        ]
        result = _filter_campaigns(
            campaigns,
            campaign_device_filter="iOS",
            campaign_sort_field="progress",
        )
        assert len(result) == 2
        # Epsilon: 80/100=0.8 > Alpha: 50/100=0.5
        assert result[0]["name"] == "Epsilon iOS"
        assert result[1]["name"] == "Alpha iOS"

    def test_search_and_device_filter(self):
        result = _filter_campaigns(
            CAMPAIGNS,
            campaign_search_query="collection",
            campaign_device_filter="iOS",
        )
        assert len(result) == 1
        assert result[0]["name"] == "Alpha iOS"
