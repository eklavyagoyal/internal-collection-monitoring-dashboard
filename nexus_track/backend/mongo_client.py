"""
Async MongoDB client for Nexus-Track.

Collections:
  • **campaigns**    – collection campaigns with metadata + calendar config
  • **participants** – participant records scoped to a campaign + date
  • **settings**     – user-configurable labels (platforms, model_tags, statuses)
"""

import os
import secrets
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_client: AsyncIOMotorClient | None = None

# Default label sets shipped with a fresh install.
DEFAULT_PLATFORMS = ["Orb", "Kiosk-v1", "Kiosk-v2", "Self-Serve", "Other"]
DEFAULT_MODEL_TAGS = ["v4.5", "v4.6", "v5.0", "beta"]
DEFAULT_STATUSES = ["Booked", "Completed"]
DEFAULT_DEVICE_TYPES = ["iOS", "Android", "Orb", "Multi-device"]


def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _client = AsyncIOMotorClient(
            uri, maxPoolSize=20, minPoolSize=2,
            serverSelectionTimeoutMS=5_000, connectTimeoutMS=5_000,
        )
    return _client


def _db():
    return _get_client()[os.getenv("MONGO_DB_NAME", "nexus_track")]


def _campaigns():
    return _db()["campaigns"]


def _participants():
    return _db()["participants"]


def _settings():
    return _db()["settings"]


# ---------------------------------------------------------------------------
# Indexes (idempotent)
# ---------------------------------------------------------------------------

async def ensure_indexes() -> None:
    try:
        await _participants().drop_index("google_event_id_1")
    except Exception:
        pass

    await _campaigns().create_index("campaign_id", unique=True)
    await _participants().create_index(
        [("campaign_id", 1), ("google_event_id", 1)], unique=True,
    )
    await _participants().create_index(
        [("campaign_id", 1), ("appointment_date", 1)],
    )
    await _participants().create_index(
        [("campaign_id", 1), ("status", 1)],
    )
    await _participants().create_index("email")

    # Migrate legacy statuses to new model
    await _participants().update_many(
        {"status": {"$in": ["Pending", "In-Progress"]}},
        {"$set": {"status": "Booked"}},
    )


# =========================================================================
# Settings CRUD (label management)
# =========================================================================

async def get_settings() -> dict:
    """Return the global settings doc, seeding defaults if empty."""
    doc = await _settings().find_one({"_key": "labels"})
    if doc:
        doc["_id"] = str(doc["_id"])
        return doc
    # Seed defaults
    defaults = {
        "_key": "labels",
        "platforms": DEFAULT_PLATFORMS,
        "model_tags": DEFAULT_MODEL_TAGS,
        "statuses": DEFAULT_STATUSES,
        "admin_pin_hash": "",
    }
    await _settings().insert_one(defaults)
    defaults["_id"] = str(defaults.get("_id", ""))
    return defaults


async def update_label_list(label_type: str, values: list[str]) -> None:
    """Update one of the label lists: platforms, model_tags, or statuses."""
    if label_type not in ("platforms", "model_tags", "statuses"):
        raise ValueError(f"Unknown label type: {label_type}")
    await _settings().update_one(
        {"_key": "labels"},
        {"$set": {label_type: values}},
        upsert=True,
    )


async def set_admin_pin(pin_hash: str) -> None:
    """Store the hashed admin PIN in settings."""
    await _settings().update_one(
        {"_key": "labels"},
        {"$set": {"admin_pin_hash": pin_hash}},
        upsert=True,
    )


async def get_admin_pin_hash() -> str:
    """Return the stored admin PIN hash, or empty string if not set."""
    doc = await _settings().find_one({"_key": "labels"})
    if doc:
        return doc.get("admin_pin_hash", "")
    return ""


# =========================================================================
# Campaign CRUD
# =========================================================================

async def create_campaign(data: dict) -> str:
    """Create a campaign and return its short ID."""
    cid = secrets.token_hex(4)
    now = datetime.now(timezone.utc).isoformat()

    # Validate and coerce goal to a positive integer (default 100).
    raw_goal = data.get("goal", 100)
    try:
        goal = max(1, int(raw_goal))
    except (ValueError, TypeError):
        goal = 100

    # Validate device_quota: must be dict[str, int]
    raw_quota = data.get("device_quota", {})
    if not isinstance(raw_quota, dict):
        raw_quota = {}
    device_quota = {}
    for k, v in raw_quota.items():
        try:
            device_quota[str(k)] = max(0, int(v))
        except (ValueError, TypeError):
            pass

    await _campaigns().insert_one({
        "campaign_id": cid,
        "name": data["name"],
        "description": data.get("description", ""),
        "booking_url": data.get("booking_url", ""),
        "notion_url": data.get("notion_url", ""),
        "linear_url": data.get("linear_url", ""),
        "deadline": data.get("deadline", ""),
        "goal": goal,
        "device_type": data.get("device_type", "Multi-device"),
        "device_quota": device_quota,
        # calendar_ids is a list of {calendar_id, filter} objects
        "calendar_ids": data.get("calendar_ids", []),
        # legacy single-calendar fields kept for backward compat
        "calendar_id": data.get("calendar_id", "primary") or "primary",
        "calendar_filter": data.get("calendar_filter", ""),
        "status": "active",
        "last_sync_at": None,
        "created_at": now,
        "updated_at": now,
    })
    return cid


async def update_campaign(campaign_id: str, data: dict) -> None:
    """Bulk-update writable campaign fields."""
    now = datetime.now(timezone.utc).isoformat()
    allowed = {
        "name", "description", "booking_url",
        "notion_url", "linear_url", "deadline",
        "calendar_id", "calendar_filter", "calendar_ids", "status",
        "goal", "device_type", "device_quota",
    }
    sets = {k: v for k, v in data.items() if k in allowed}

    # Coerce goal if present
    if "goal" in sets:
        try:
            sets["goal"] = max(1, int(sets["goal"]))
        except (ValueError, TypeError):
            del sets["goal"]

    sets["updated_at"] = now
    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": sets},
    )


def _backfill_campaign(doc: dict) -> dict:
    """Ensure all expected fields exist on a campaign document."""
    doc.setdefault("goal", 100)
    doc.setdefault("notion_url", "")
    doc.setdefault("linear_url", "")
    doc.setdefault("deadline", "")
    doc.setdefault("device_type", "Multi-device")
    doc.setdefault("device_quota", {})
    return doc


async def get_all_campaigns() -> list[dict]:
    cursor = _campaigns().find().sort("created_at", -1)
    out: list[dict] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        _backfill_campaign(doc)
        out.append(doc)
    return out


async def get_campaign(campaign_id: str) -> dict | None:
    doc = await _campaigns().find_one({"campaign_id": campaign_id})
    if doc:
        doc["_id"] = str(doc["_id"])
        _backfill_campaign(doc)
    return doc


async def update_campaign_field(campaign_id: str, field: str, value: Any) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": {field: value, "updated_at": now}},
    )


async def delete_campaign(campaign_id: str) -> None:
    await _campaigns().delete_one({"campaign_id": campaign_id})
    await _participants().delete_many({"campaign_id": campaign_id})


async def archive_campaign(campaign_id: str) -> None:
    """Soft-delete: set status to 'archived'."""
    now = datetime.now(timezone.utc).isoformat()
    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": {"status": "archived", "updated_at": now}},
    )


async def unarchive_campaign(campaign_id: str) -> None:
    """Restore an archived campaign to 'active'."""
    now = datetime.now(timezone.utc).isoformat()
    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": {"status": "active", "updated_at": now}},
    )


# =========================================================================
# Campaign + date stats (for the dashboard cards)
# =========================================================================

async def get_campaign_progress(campaign_id: str) -> dict:
    """Return aggregated progress stats across ALL dates for a campaign.

    Returns {booked, completed} where:
      - booked   = total participant entries (matches the bookings table)
      - completed = entries whose status is 'Completed'
    """
    pipeline = [
        {"$match": {"campaign_id": campaign_id}},
        {"$group": {
            "_id": None,
            "booked": {"$sum": 1},
            "completed": {
                "$sum": {
                    "$cond": [
                        {"$eq": ["$status", "Completed"]},
                        1, 0,
                    ]
                }
            },
        }},
    ]
    cursor = _participants().aggregate(pipeline)
    result = await cursor.to_list(length=1)
    if result:
        return {"booked": result[0]["booked"], "completed": result[0]["completed"]}
    return {"booked": 0, "completed": 0}


async def get_all_campaigns_with_stats(
    date: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Return every campaign enriched with participant counts for *date*
    AND overall progress (booked/completed across all dates).

    By default archived campaigns are excluded from the list.
    """
    campaigns = await get_all_campaigns()
    if not include_archived:
        campaigns = [c for c in campaigns if c.get("status") != "archived"]
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    for c in campaigns:
        cid = c["campaign_id"]

        # Per-date stats (for the daily view)
        parts = await get_participants_for_campaign(cid, date)
        total = len(parts)
        completed = sum(1 for p in parts if p.get("status") == "Completed")
        c["today_total"] = total
        c["today_completed"] = completed
        c["today_booked"] = total - completed
        c["today_progress"] = int(completed / total * 100) if total else 0

        # Overall progress across all dates
        progress = await get_campaign_progress(cid)
        c["booked"] = progress["booked"]
        c["completed_all"] = progress["completed"]
    return campaigns


# =========================================================================
# Participant CRUD (campaign-scoped)
# =========================================================================

async def upsert_participant(
    campaign_id: str, event_id: str, name: str, email: str,
    appointment_time: str, appointment_date: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await _participants().update_one(
        {"campaign_id": campaign_id, "google_event_id": event_id},
        {
            "$set": {
                "name": name, "email": email,
                "appointment_time": appointment_time,
                "appointment_date": appointment_date,
                "updated_at": now,
            },
            "$setOnInsert": {
                "campaign_id": campaign_id,
                "google_event_id": event_id,
                "platform": "", "model_tag": "",
                "status": "Booked", "notes": "",
                "issue_comment": "",
                "start_time": None, "end_time": None,
                "created_at": now,
            },
        },
        upsert=True,
    )


async def get_participants_for_campaign(
    campaign_id: str, date: str | None = None,
) -> list[dict]:
    """Fetch participants for a campaign.

    If *date* is given, return only that day's participants.
    If *date* is ``None``, return **all** participants across every date,
    sorted by appointment_date then appointment_time.
    """
    query: dict = {"campaign_id": campaign_id}
    if date is not None:
        query["appointment_date"] = date
    sort_key = [("appointment_date", 1), ("appointment_time", 1)] if date is None else [("appointment_time", 1)]
    cursor = _participants().find(query).sort(sort_key)
    out: list[dict] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        # ensure fields exist for older documents
        doc.setdefault("notes", "")
        doc.setdefault("issue_comment", "")
        out.append(doc)
    return out


async def update_participant_field(
    campaign_id: str, event_id: str, field: str, value: Any,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    await _participants().update_one(
        {"campaign_id": campaign_id, "google_event_id": event_id},
        {"$set": {field: value, "updated_at": now}},
    )


async def update_participant_status(
    campaign_id: str, event_id: str, new_status: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    update: dict[str, Any] = {"status": new_status, "updated_at": now}
    if new_status == "Completed":
        update["end_time"] = now
    elif new_status == "Booked":
        update["end_time"] = None
    await _participants().update_one(
        {"campaign_id": campaign_id, "google_event_id": event_id},
        {"$set": update},
    )


# =========================================================================
# Manual participant (no calendar — user-entered)
# =========================================================================

async def add_manual_participant(
    campaign_id: str,
    name: str,
    email: str,
    appointment_date: str,
    appointment_time: str = "",
) -> str:
    """Insert a participant manually (not from calendar).

    Returns the generated event_id.
    """
    event_id = f"manual-{secrets.token_hex(6)}"
    now = datetime.now(timezone.utc).isoformat()
    await _participants().insert_one({
        "campaign_id": campaign_id,
        "google_event_id": event_id,
        "name": name,
        "email": email,
        "appointment_time": appointment_time or "",
        "appointment_date": appointment_date,
        "platform": "",
        "model_tag": "",
        "status": "Booked",
        "notes": "",
        "issue_comment": "",
        "start_time": None,
        "end_time": None,
        "created_at": now,
        "updated_at": now,
    })
    return event_id


# =========================================================================
# Bulk status update
# =========================================================================

async def delete_participant(campaign_id: str, event_id: str) -> None:
    """Delete a single participant by campaign_id + google_event_id."""
    await _participants().delete_one(
        {"campaign_id": campaign_id, "google_event_id": event_id},
    )


async def bulk_delete_participants(
    campaign_id: str, event_ids: list[str],
) -> int:
    """Delete multiple participants at once. Returns deleted count."""
    result = await _participants().delete_many(
        {"campaign_id": campaign_id, "google_event_id": {"$in": event_ids}},
    )
    return result.deleted_count


async def bulk_update_participant_field(
    campaign_id: str,
    event_ids: list[str],
    field: str,
    value: Any,
) -> int:
    """Update a single field for multiple participants at once."""
    now = datetime.now(timezone.utc).isoformat()
    result = await _participants().update_many(
        {"campaign_id": campaign_id, "google_event_id": {"$in": event_ids}},
        {"$set": {field: value, "updated_at": now}},
    )
    return result.modified_count


# =========================================================================
# CSV export data
# =========================================================================

async def get_participants_for_export(
    campaign_id: str,
    date: str | None = None,
) -> list[dict]:
    """Return participants for CSV export. If date is None, return ALL."""
    query: dict = {"campaign_id": campaign_id}
    if date:
        query["appointment_date"] = date
    cursor = _participants().find(query).sort("appointment_date", 1)
    out: list[dict] = []
    async for doc in cursor:
        out.append({
            "name": doc.get("name", ""),
            "email": doc.get("email", ""),
            "date": doc.get("appointment_date", ""),
            "time": doc.get("appointment_time", ""),
            "platform": doc.get("platform", ""),
            "model_tag": doc.get("model_tag", ""),
            "status": doc.get("status", ""),
            "notes": doc.get("notes", ""),
            "issue_comment": doc.get("issue_comment", ""),
        })
    return out


# =========================================================================
# Multi-day sync helpers
# =========================================================================

async def get_synced_dates_for_campaign(campaign_id: str) -> list[str]:
    """Return distinct appointment_date values already in the DB."""
    return await _participants().distinct(
        "appointment_date", {"campaign_id": campaign_id},
    )


# =========================================================================
# Per-device progress (for device quota tracking)
# =========================================================================

async def get_per_device_progress(campaign_id: str) -> dict[str, dict]:
    """Return per-platform participant counts for a campaign.

    Returns ``{platform: {total: N, completed: N}}`` for each platform
    that has at least one participant.
    """
    pipeline = [
        {"$match": {"campaign_id": campaign_id, "platform": {"$ne": ""}}},
        {"$group": {
            "_id": "$platform",
            "total": {"$sum": 1},
            "completed": {
                "$sum": {"$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]},
            },
        }},
    ]
    cursor = _participants().aggregate(pipeline)
    result: dict[str, dict] = {}
    async for doc in cursor:
        result[doc["_id"]] = {
            "total": doc["total"],
            "completed": doc["completed"],
        }
    return result


# =========================================================================
# Campaign cloning
# =========================================================================

async def clone_campaign(campaign_id: str) -> str | None:
    """Clone a campaign's settings (no participants). Returns new ID."""
    source = await get_campaign(campaign_id)
    if not source:
        return None
    return await create_campaign({
        "name": source["name"] + " (Copy)",
        "description": source.get("description", ""),
        "booking_url": source.get("booking_url", ""),
        "notion_url": source.get("notion_url", ""),
        "linear_url": source.get("linear_url", ""),
        "deadline": source.get("deadline", ""),
        "goal": source.get("goal", 100),
        "device_type": source.get("device_type", "Multi-device"),
        "device_quota": source.get("device_quota", {}),
        "calendar_id": source.get("calendar_id", "primary"),
        "calendar_filter": source.get("calendar_filter", ""),
        "calendar_ids": source.get("calendar_ids", []),
    })
