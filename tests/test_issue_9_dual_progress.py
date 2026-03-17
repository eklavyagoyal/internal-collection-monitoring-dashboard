"""
Tests for Issue #9: Dual-color progress bar (completed vs booked).

Verifies:
- Completed and booked derived separately
- Segment widths scale correctly
- Combined fill clamps at 100%
- Over-goal values handled
- Missing/zero denominator handled
- Campaigns with only completed or only booked
"""

import pytest

from nexus_track.backend import mongo_client as mc

pytestmark = pytest.mark.asyncio


def _compute_dual_pcts(booked: int, completed: int, goal: int) -> dict:
    """Mirror the state.py percent calculations for the dual bar."""
    if goal <= 0:
        return {"booked_pct": 0, "completed_pct": 0}
    return {
        "booked_pct": min(100, int(booked / goal * 100)),
        "completed_pct": min(100, int(completed / goal * 100)),
    }


class TestDualProgressSegments:
    """#9 — completed and booked segments."""

    async def test_segments_separate_correctly(self):
        """Booked includes completed; the visible booked-only zone is the gap."""
        cid = await mc.create_campaign({"name": "Dual", "goal": "10"})
        for i in range(6):
            await mc.upsert_participant(
                cid, f"e{i}", f"P{i}", f"p{i}@t.com", "10:00", "2024-06-15",
            )
        # Complete 4 of the 6 booked
        for i in range(4):
            await mc.update_participant_status(cid, f"e{i}", "Completed")

        progress = await mc.get_campaign_progress(cid)
        assert progress["booked"] == 6
        assert progress["completed"] == 4

        pcts = _compute_dual_pcts(progress["booked"], progress["completed"], 10)
        assert pcts["booked_pct"] == 60
        assert pcts["completed_pct"] == 40
        # Visual: booked bar covers 60%, completed overlays 40%,
        # so the "booked-only" visible segment is 20% wide.

    async def test_only_completed_no_pending(self):
        """All booked are completed — booked == completed segments."""
        cid = await mc.create_campaign({"name": "All-done", "goal": "5"})
        for i in range(5):
            await mc.upsert_participant(
                cid, f"e{i}", f"P{i}", f"p{i}@t.com", "10:00", "2024-06-15",
            )
            await mc.update_participant_status(cid, f"e{i}", "Completed")

        progress = await mc.get_campaign_progress(cid)
        assert progress["booked"] == 5
        assert progress["completed"] == 5

        pcts = _compute_dual_pcts(5, 5, 5)
        assert pcts["booked_pct"] == 100
        assert pcts["completed_pct"] == 100

    async def test_only_booked_none_completed(self):
        """All pending — completed segment is 0."""
        cid = await mc.create_campaign({"name": "All-pending", "goal": "10"})
        for i in range(3):
            await mc.upsert_participant(
                cid, f"e{i}", f"P{i}", f"p{i}@t.com", "10:00", "2024-06-15",
            )

        progress = await mc.get_campaign_progress(cid)
        assert progress["booked"] == 3
        assert progress["completed"] == 0

        pcts = _compute_dual_pcts(3, 0, 10)
        assert pcts["booked_pct"] == 30
        assert pcts["completed_pct"] == 0

    async def test_combined_clamps_at_100(self):
        """Over-goal: visual segments clamp at 100%."""
        pcts = _compute_dual_pcts(booked=120, completed=90, goal=100)
        assert pcts["booked_pct"] == 100
        assert pcts["completed_pct"] == 90

    async def test_completed_exceeds_goal(self):
        """Completed > goal still clamps at 100%."""
        pcts = _compute_dual_pcts(booked=150, completed=150, goal=100)
        assert pcts["booked_pct"] == 100
        assert pcts["completed_pct"] == 100

    async def test_zero_goal_graceful(self):
        """Zero goal doesn't crash — both segments 0."""
        pcts = _compute_dual_pcts(booked=10, completed=5, goal=0)
        assert pcts["booked_pct"] == 0
        assert pcts["completed_pct"] == 0

    async def test_no_participants_at_all(self):
        """Empty campaign: both segments 0."""
        cid = await mc.create_campaign({"name": "Empty", "goal": "50"})
        progress = await mc.get_campaign_progress(cid)
        pcts = _compute_dual_pcts(progress["booked"], progress["completed"], 50)
        assert pcts == {"booked_pct": 0, "completed_pct": 0}

    async def test_truthful_counts_when_over_goal(self):
        """Text shows true counts even when bar clamps."""
        cid = await mc.create_campaign({"name": "Over-goal", "goal": "2"})
        for i in range(5):
            await mc.upsert_participant(
                cid, f"e{i}", f"P{i}", f"p{i}@t.com", "10:00", "2024-06-15",
            )
            await mc.update_participant_status(cid, f"e{i}", "Completed")

        progress = await mc.get_campaign_progress(cid)
        # True counts preserved (text can display them)
        assert progress["booked"] == 5
        assert progress["completed"] == 5
        # Visual clamped
        pcts = _compute_dual_pcts(progress["booked"], progress["completed"], 2)
        assert pcts["booked_pct"] == 100
        assert pcts["completed_pct"] == 100

    async def test_dedup_counts_unique_participants(self):
        """Same email across dates counts as 1 participant for progress."""
        cid = await mc.create_campaign({"name": "Dedup", "goal": "10"})
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e2", "A", "a@t.com", "10:00", "2024-06-16")
        await mc.update_participant_status(cid, "e1", "Completed")

        progress = await mc.get_campaign_progress(cid)
        assert progress["booked"] == 1  # deduplicated
        assert progress["completed"] == 1
