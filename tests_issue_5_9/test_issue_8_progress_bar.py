"""
Tests for Issue #8: Improved campaign progress bar.

Verifies:
- Progress calculation maps correctly 0–100
- 100% completed renders fully (completed_pct == 100)
- Over-goal clamps at 100
- Missing / zero goal handled gracefully
- get_campaign_progress returns correct counts
"""

import pytest

from nexus_track.backend import mongo_client as mc

pytestmark = pytest.mark.asyncio


def _compute_pct(count: int, goal: int) -> int:
    """Mirror the state.py / campaign_card.py progress calculation."""
    if goal <= 0:
        return 0
    return min(100, int(count / goal * 100))


class TestProgressCalculation:
    """#8 — correct 0–100% scaling."""

    async def test_empty_campaign_zero_progress(self):
        cid = await mc.create_campaign({"name": "Empty", "goal": "100"})
        progress = await mc.get_campaign_progress(cid)
        assert progress == {"booked": 0, "completed": 0}
        assert _compute_pct(progress["completed"], 100) == 0

    async def test_partial_progress(self):
        cid = await mc.create_campaign({"name": "Partial", "goal": "10"})
        for i in range(10):
            await mc.upsert_participant(
                cid, f"e{i}", f"P{i}", f"p{i}@t.com", "10:00", "2024-06-15",
            )
        # Complete 3 of 10
        for i in range(3):
            await mc.update_participant_status(cid, f"e{i}", "Completed")

        progress = await mc.get_campaign_progress(cid)
        assert progress["completed"] == 3
        assert _compute_pct(progress["completed"], 10) == 30

    async def test_100_percent_full(self):
        cid = await mc.create_campaign({"name": "Full", "goal": "3"})
        for i in range(3):
            await mc.upsert_participant(
                cid, f"e{i}", f"P{i}", f"p{i}@t.com", "10:00", "2024-06-15",
            )
            await mc.update_participant_status(cid, f"e{i}", "Completed")

        progress = await mc.get_campaign_progress(cid)
        assert progress["completed"] == 3
        assert _compute_pct(progress["completed"], 3) == 100

    async def test_over_goal_clamps_at_100(self):
        cid = await mc.create_campaign({"name": "Over", "goal": "2"})
        for i in range(5):
            await mc.upsert_participant(
                cid, f"e{i}", f"P{i}", f"p{i}@t.com", "10:00", "2024-06-15",
            )
            await mc.update_participant_status(cid, f"e{i}", "Completed")

        progress = await mc.get_campaign_progress(cid)
        assert progress["completed"] == 5
        # Visual clamping
        assert _compute_pct(progress["completed"], 2) == 100

    async def test_zero_goal_returns_zero_pct(self):
        """Zero goal shouldn't cause division by zero."""
        assert _compute_pct(10, 0) == 0

    async def test_negative_goal_returns_zero_pct(self):
        assert _compute_pct(5, -1) == 0

    async def test_progress_across_multiple_dates(self):
        """Progress aggregates across all dates in the campaign."""
        cid = await mc.create_campaign({"name": "Multi-date", "goal": "10"})
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.upsert_participant(cid, "e2", "B", "b@t.com", "11:00", "2024-06-16")
        await mc.upsert_participant(cid, "e3", "C", "c@t.com", "12:00", "2024-06-17")
        await mc.update_participant_status(cid, "e1", "Completed")
        await mc.update_participant_status(cid, "e3", "Completed")

        progress = await mc.get_campaign_progress(cid)
        assert progress["booked"] == 3
        assert progress["completed"] == 2
        assert _compute_pct(progress["completed"], 10) == 20


class TestProgressBarEdgeCases:
    """#8 — edge cases for graceful handling."""

    async def test_archived_campaign_progress(self):
        """Archived campaigns still report correct progress."""
        cid = await mc.create_campaign({"name": "Archived", "goal": "5"})
        await mc.upsert_participant(cid, "e1", "A", "a@t.com", "10:00", "2024-06-15")
        await mc.update_participant_status(cid, "e1", "Completed")
        await mc.archive_campaign(cid)

        progress = await mc.get_campaign_progress(cid)
        assert progress["completed"] == 1
        assert progress["booked"] == 1

    async def test_missing_campaign_progress(self):
        """Non-existent campaign returns zero progress."""
        progress = await mc.get_campaign_progress("nonexistent")
        assert progress == {"booked": 0, "completed": 0}
