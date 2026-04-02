"""
Async MongoDB client for Nexus-Track.

Collections:
  • **campaigns**    – collection campaigns with metadata + calendar config
  • **participants** – participant records scoped to a campaign + date
  • **settings**     – user-configurable platform/model labels + admin config
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from motor.motor_asyncio import AsyncIOMotorClient

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

_client: AsyncIOMotorClient | None = None
_indexes_client_id: int | None = None

# Default label sets shipped with a fresh install.
DEFAULT_PLATFORMS = ["Orb", "Kiosk-v1", "Kiosk-v2", "Self-Serve", "Other"]
DEFAULT_MODEL_TAGS = ["v4.5", "v4.6", "v5.0", "beta"]
FIXED_PARTICIPANT_STATUSES = ("Booked", "Completed")
PIN_HASH_ALGO = "pbkdf2_sha256"
PIN_HASH_ITERATIONS = 390_000
DEFAULT_OPERATIONS_TIMEZONE = "UTC"


def utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def resolve_operations_timezone_name(timezone_name: str | None = None) -> str:
    """Return the configured operations-day timezone used for dashboard defaults."""
    raw = str(
        timezone_name
        or os.getenv("APP_DAY_TIMEZONE")
        or os.getenv("TZ")
        or DEFAULT_OPERATIONS_TIMEZONE
        or "",
    ).strip()
    if not raw:
        return DEFAULT_OPERATIONS_TIMEZONE
    try:
        ZoneInfo(raw)
        return raw
    except ZoneInfoNotFoundError:
        return DEFAULT_OPERATIONS_TIMEZONE


def operational_now() -> datetime:
    """Return the current datetime in the configured operations timezone."""
    return datetime.now(ZoneInfo(resolve_operations_timezone_name()))


def operational_today_str() -> str:
    """Return today's ISO date in the configured operations timezone."""
    return operational_now().strftime("%Y-%m-%d")


def build_progress_key(email: str, event_id: str) -> str:
    """Return the canonical participant identity used for campaign progress."""
    normalized_email = str(email or "").strip().lower()
    if normalized_email:
        return f"email:{normalized_email}"
    return f"event:{str(event_id or '').strip()}"


def _normalize_appointment_time(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return raw


def _normalize_appointment_date(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return raw


def _build_appointment_sort_key(
    appointment_date: str,
    appointment_time: str,
) -> str:
    cleaned_date = _normalize_appointment_date(appointment_date)
    cleaned_time = _normalize_appointment_time(appointment_time) or "00:00"
    if cleaned_date:
        return f"{cleaned_date}T{cleaned_time}:00"
    return ""


def build_appointment_fields(
    *,
    appointment_date: str,
    appointment_time: str = "",
    appointment_start_raw: str = "",
    appointment_start_utc: str = "",
    appointment_timezone: str = "",
    appointment_has_time: bool | None = None,
) -> dict[str, Any]:
    """Build the normalized appointment fields stored on participant docs."""
    cleaned_date = _normalize_appointment_date(appointment_date)
    cleaned_time = _normalize_appointment_time(appointment_time)
    has_time = bool(cleaned_time) if appointment_has_time is None else bool(appointment_has_time)
    raw_start = str(appointment_start_raw or "").strip()
    if not raw_start:
        if cleaned_date and cleaned_time:
            raw_start = f"{cleaned_date}T{cleaned_time}:00"
        elif cleaned_date:
            raw_start = cleaned_date

    return {
        "appointment_date": cleaned_date,
        "appointment_time": cleaned_time,
        "appointment_start_raw": raw_start,
        "appointment_start_utc": str(appointment_start_utc or "").strip(),
        "appointment_timezone": str(appointment_timezone or "").strip(),
        "appointment_has_time": has_time,
        "appointment_sort_key": _build_appointment_sort_key(cleaned_date, cleaned_time),
    }


def build_participant_model_fields(
    *,
    event_id: str,
    email: str,
    appointment_date: str,
    appointment_time: str = "",
    appointment_start_raw: str = "",
    appointment_start_utc: str = "",
    appointment_timezone: str = "",
    appointment_has_time: bool | None = None,
) -> dict[str, Any]:
    """Build the normalized model-layer fields for a participant record."""
    return {
        **build_appointment_fields(
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            appointment_start_raw=appointment_start_raw,
            appointment_start_utc=appointment_start_utc,
            appointment_timezone=appointment_timezone,
            appointment_has_time=appointment_has_time,
        ),
        "progress_key": build_progress_key(email, event_id),
    }


def _participant_sort_key(doc: dict) -> tuple[str, str]:
    return (
        str(doc.get("appointment_sort_key", "") or ""),
        str(doc.get("google_event_id", "") or ""),
    )


def _backfill_participant_doc(doc: dict) -> dict:
    """Ensure legacy participants expose the richer appointment model."""
    doc.setdefault("notes", "")
    doc.setdefault("issue_comment", "")
    derived = build_participant_model_fields(
        event_id=doc.get("google_event_id", ""),
        email=doc.get("email", ""),
        appointment_date=doc.get("appointment_date", ""),
        appointment_time=doc.get("appointment_time", ""),
        appointment_start_raw=doc.get("appointment_start_raw", ""),
        appointment_start_utc=doc.get("appointment_start_utc", ""),
        appointment_timezone=doc.get("appointment_timezone", ""),
        appointment_has_time=doc.get("appointment_has_time"),
    )
    doc["progress_key"] = derived["progress_key"]
    doc["appointment_sort_key"] = derived["appointment_sort_key"]
    doc["appointment_has_time"] = derived["appointment_has_time"]
    for key in (
        "appointment_start_raw",
        "appointment_start_utc",
        "appointment_timezone",
    ):
        if not str(doc.get(key, "") or "").strip():
            doc[key] = derived[key]
    return doc


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


def _audit_log():
    return _db()["audit_log"]


# ---------------------------------------------------------------------------
# Indexes (idempotent)
# ---------------------------------------------------------------------------

async def ensure_indexes() -> None:
    global _indexes_client_id
    client_id = id(_get_client())
    if _indexes_client_id == client_id:
        return

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
        [("campaign_id", 1), ("appointment_sort_key", 1)],
    )
    await _participants().create_index(
        [("campaign_id", 1), ("progress_key", 1)],
    )
    await _participants().create_index(
        [("campaign_id", 1), ("status", 1)],
    )
    await _participants().create_index("email")
    await _audit_log().create_index([("created_at", -1)])

    # Migrate legacy statuses to new model
    await _participants().update_many(
        {"status": {"$in": ["Pending", "In-Progress"]}},
        {"$set": {"status": "Booked"}},
    )

    # Migrate legacy "archived" campaigns to "completed"
    await _campaigns().update_many(
        {"status": "archived"},
        {"$set": {"status": "completed"}},
    )
    _indexes_client_id = client_id


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
        "admin_pin_hash": "",
        "platform_model_tags": {},
    }
    await _settings().insert_one(defaults)
    defaults["_id"] = str(defaults.get("_id", ""))
    return defaults


async def update_label_list(label_type: str, values: list[str]) -> None:
    """Update one of the supported label lists: platforms or model_tags."""
    if label_type not in ("platforms", "model_tags"):
        raise ValueError(f"Unknown label type: {label_type}")
    await _settings().update_one(
        {"_key": "labels"},
        {"$set": {label_type: values}},
        upsert=True,
    )


async def update_platform_model_tags(data: dict) -> None:
    """Persist the platform_model_tags mapping {platform: [model_tag, ...]}."""
    await _settings().update_one(
        {"_key": "labels"},
        {"$set": {"platform_model_tags": data}},
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


def hash_admin_pin(pin: str, *, iterations: int = PIN_HASH_ITERATIONS) -> str:
    """Return a PBKDF2-based hash string for storing the admin PIN."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), salt, iterations,
    )
    return f"{PIN_HASH_ALGO}${iterations}${salt.hex()}${digest.hex()}"


def verify_admin_pin(pin: str, stored_hash: str) -> tuple[bool, bool]:
    """Verify an admin PIN against the stored hash.

    Returns ``(is_valid, needs_upgrade)``.
    Legacy unsalted SHA-256 hashes still verify so existing installations
    keep working, but they are marked for upgrade on the next successful login.
    """
    if not stored_hash:
        return False, False

    if stored_hash.startswith(f"{PIN_HASH_ALGO}$"):
        try:
            _, iterations_raw, salt_hex, digest_hex = stored_hash.split("$", 3)
            iterations = int(iterations_raw)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except (ValueError, TypeError):
            return False, False

        candidate = hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), salt, iterations,
        )
        is_valid = hmac.compare_digest(candidate, expected)
        needs_upgrade = iterations != PIN_HASH_ITERATIONS
        return is_valid, (is_valid and needs_upgrade)

    legacy_digest = hashlib.sha256(pin.encode("utf-8")).hexdigest()
    is_valid = hmac.compare_digest(legacy_digest, stored_hash)
    return is_valid, is_valid


async def record_audit_event(
    *,
    action: str,
    summary: str,
    resource_type: str = "",
    resource_id: str = "",
    resource_label: str = "",
    metadata: dict | None = None,
) -> None:
    """Persist a lightweight admin audit event."""
    now = utc_now_iso()
    await _audit_log().insert_one({
        "created_at": now,
        "actor_role": "admin",
        "action": action,
        "summary": summary,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_label": resource_label,
        "metadata": metadata or {},
    })


async def get_recent_audit_events(limit: int = 10) -> list[dict]:
    """Return the most recent admin audit events, newest first."""
    cursor = _audit_log().find().sort("created_at", -1).limit(limit)
    out: list[dict] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


async def get_platform_usage(label: str) -> dict[str, int]:
    """Return usage counts that make removing a platform unsafe."""
    return {
        "campaign_device_type_count": await _campaigns().count_documents(
            {"device_types": label},
        ),
        "campaign_default_count": await _campaigns().count_documents(
            {"default_platform": label},
        ),
        "participant_count": await _participants().count_documents(
            {"platform": label},
        ),
    }


async def get_platform_model_tag_usage(
    platform: str,
    tag: str,
) -> dict[str, int]:
    """Return usage counts that make removing a platform/model mapping unsafe."""
    return {
        "participant_count": await _participants().count_documents(
            {"platform": platform, "model_tag": tag},
        ),
        "campaign_default_count": await _campaigns().count_documents(
            {"default_platform": platform, "default_model_tag": tag},
        ),
        "campaign_shared_default_count": await _campaigns().count_documents(
            {
                "default_platform": "",
                "default_model_tag": tag,
                "device_types": platform,
            },
        ),
    }


# =========================================================================
# Campaign CRUD
# =========================================================================

async def create_campaign(data: dict) -> str:
    """Create a campaign and return its short ID."""
    cid = secrets.token_hex(4)
    now = utc_now_iso()

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
        "device_types": data.get("device_types", []),
        "device_quota": device_quota,
        "default_platform": data.get("default_platform", ""),
        "default_model_tag": data.get("default_model_tag", ""),
        # calendar_ids is a list of {calendar_id, filter} objects
        "calendar_ids": data.get("calendar_ids", []),
        # legacy single-calendar fields kept for backward compat
        "calendar_id": data.get("calendar_id", "primary") or "primary",
        "calendar_filter": data.get("calendar_filter", ""),
        "status": "active",
        "last_sync_at": None,
        "last_sync_attempt_at": None,
        "last_sync_success_at": None,
        "last_sync_error_code": "",
        "last_sync_error": "",
        "last_sync_error_detail": "",
        "created_at": now,
        "updated_at": now,
    })
    return cid


async def update_campaign(campaign_id: str, data: dict) -> None:
    """Bulk-update writable campaign fields."""
    now = utc_now_iso()
    allowed = {
        "name", "description", "booking_url",
        "notion_url", "linear_url", "deadline",
        "calendar_id", "calendar_filter", "calendar_ids", "status",
        "goal", "device_types", "device_quota",
        "default_platform", "default_model_tag",
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
    legacy_last_sync = doc.get("last_sync_at")
    doc.setdefault("last_sync_success_at", legacy_last_sync)
    doc.setdefault(
        "last_sync_attempt_at",
        doc.get("last_sync_success_at") or legacy_last_sync,
    )
    doc.setdefault("last_sync_error_code", "")
    doc.setdefault("last_sync_error", "")
    doc.setdefault("last_sync_error_detail", "")
    # Backfill: migrate legacy device_type (str) to device_types (list)
    if "device_types" not in doc:
        legacy = doc.pop("device_type", "")
        if legacy and legacy != "Multi-device":
            doc["device_types"] = [legacy]
        else:
            doc["device_types"] = []
    doc.setdefault("device_quota", {})
    doc.setdefault("default_platform", "")
    doc.setdefault("default_model_tag", "")
    # Pre-compute display string for the card badge
    doc["device_types_display"] = ", ".join(doc.get("device_types", []))
    return doc


async def get_all_campaigns() -> list[dict]:
    cursor = _campaigns().find().sort("created_at", -1)
    out: list[dict] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        _backfill_campaign(doc)
        out.append(doc)
    return out


async def count_all_campaigns() -> dict:
    """Return total, active, and completed campaign counts (includes archived)."""
    cursor = _campaigns().aggregate([
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "active": {
                    "$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]},
                },
                "completed": {
                    "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]},
                },
            },
        },
    ])
    rows = await cursor.to_list(length=1)
    if not rows:
        return {"total": 0, "active": 0, "completed": 0}
    row = rows[0]
    return {
        "total": int(row.get("total", 0) or 0),
        "active": int(row.get("active", 0) or 0),
        "completed": int(row.get("completed", 0) or 0),
    }


async def get_campaign(campaign_id: str) -> dict | None:
    doc = await _campaigns().find_one({"campaign_id": campaign_id})
    if doc:
        doc["_id"] = str(doc["_id"])
        _backfill_campaign(doc)
    return doc


async def update_campaign_field(campaign_id: str, field: str, value: Any) -> None:
    now = utc_now_iso()
    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": {field: value, "updated_at": now}},
    )


async def update_campaign_sync_state(
    campaign_id: str,
    *,
    attempt_at: str | None = None,
    success_at: str | None = None,
    error_code: str | None = None,
    error_summary: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Persist sync attempt/success metadata without losing the last good sync."""
    now = utc_now_iso()
    sets: dict[str, Any] = {"updated_at": now}

    if attempt_at is not None:
        sets["last_sync_attempt_at"] = attempt_at
    if success_at is not None:
        sets["last_sync_success_at"] = success_at
        # Keep the legacy field aligned with the last successful sync.
        sets["last_sync_at"] = success_at
    if error_code is not None:
        sets["last_sync_error_code"] = error_code
    if error_summary is not None:
        sets["last_sync_error"] = error_summary
    if error_detail is not None:
        sets["last_sync_error_detail"] = error_detail

    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": sets},
    )


async def delete_campaign(campaign_id: str) -> None:
    await _campaigns().delete_one({"campaign_id": campaign_id})
    await _participants().delete_many({"campaign_id": campaign_id})


async def archive_campaign(campaign_id: str) -> None:
    """Soft-delete: set status to 'archived'."""
    now = utc_now_iso()
    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": {"status": "archived", "updated_at": now}},
    )


async def unarchive_campaign(campaign_id: str) -> None:
    """Restore an archived campaign to 'active'."""
    now = utc_now_iso()
    await _campaigns().update_one(
        {"campaign_id": campaign_id},
        {"$set": {"status": "active", "updated_at": now}},
    )


# =========================================================================
# Campaign + date stats (for the dashboard cards)
# =========================================================================

async def get_campaign_progress(campaign_id: str) -> dict:
    """Return unique-participant progress stats across ALL dates for a campaign.

    Campaign goals track unique participants, not raw appointment rows.
    Participants are deduplicated by normalized email when available; rows
    without an email fall back to their event ID so we never merge unrelated
    bookings just because the email is blank.
    """
    cursor = _participants().find(
        {"campaign_id": campaign_id},
        {"email": 1, "status": 1, "google_event_id": 1, "progress_key": 1},
    )

    seen: dict[str, bool] = {}
    async for doc in cursor:
        progress_key = str(doc.get("progress_key", "") or "").strip() or build_progress_key(
            doc.get("email", ""),
            doc.get("google_event_id", ""),
        )
        seen.setdefault(progress_key, False)
        if doc.get("status") == "Completed":
            seen[progress_key] = True

    return {
        "booked": len(seen),
        "completed": sum(1 for completed in seen.values() if completed),
    }


async def _aggregate_daily_campaign_stats(
    campaign_ids: list[str],
    date: str,
) -> dict[str, dict[str, int]]:
    if not campaign_ids:
        return {}

    cursor = _participants().aggregate([
        {
            "$match": {
                "campaign_id": {"$in": campaign_ids},
                "appointment_date": date,
            },
        },
        {
            "$group": {
                "_id": "$campaign_id",
                "today_total": {"$sum": 1},
                "today_completed": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]},
                },
            },
        },
    ])

    stats: dict[str, dict[str, int]] = {}
    async for row in cursor:
        total = int(row.get("today_total", 0) or 0)
        completed = int(row.get("today_completed", 0) or 0)
        stats[str(row.get("_id", "") or "")] = {
            "today_total": total,
            "today_completed": completed,
            "today_booked": max(0, total - completed),
            "today_progress": int(completed / total * 100) if total else 0,
        }
    return stats


async def _aggregate_campaign_progress_stats(
    campaign_ids: list[str],
) -> dict[str, dict[str, int]]:
    if not campaign_ids:
        return {}

    cursor = _participants().find(
        {"campaign_id": {"$in": campaign_ids}},
        {
            "campaign_id": 1,
            "progress_key": 1,
            "email": 1,
            "google_event_id": 1,
            "status": 1,
        },
    )

    seen_by_campaign: dict[str, dict[str, bool]] = {}
    async for row in cursor:
        campaign_id = str(row.get("campaign_id", "") or "")
        progress_key = str(row.get("progress_key", "") or "").strip() or build_progress_key(
            row.get("email", ""),
            row.get("google_event_id", ""),
        )
        campaign_seen = seen_by_campaign.setdefault(campaign_id, {})
        campaign_seen.setdefault(progress_key, False)
        if row.get("status") == "Completed":
            campaign_seen[progress_key] = True

    return {
        campaign_id: {
            "booked": len(progress_rows),
            "completed": sum(1 for completed in progress_rows.values() if completed),
        }
        for campaign_id, progress_rows in seen_by_campaign.items()
    }


async def get_dashboard_snapshot(
    date: str | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Return the dashboard's campaign rows plus global campaign counts."""
    if date is None:
        date = operational_today_str()

    campaign_query: dict[str, Any] = {}
    if not include_archived:
        campaign_query["status"] = {"$ne": "completed"}

    cursor = _campaigns().find(campaign_query).sort("created_at", -1)
    campaigns: list[dict[str, Any]] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        _backfill_campaign(doc)
        campaigns.append(doc)

    campaign_ids = [str(campaign.get("campaign_id", "") or "") for campaign in campaigns]
    daily_stats = await _aggregate_daily_campaign_stats(campaign_ids, date)
    progress_stats = await _aggregate_campaign_progress_stats(campaign_ids)
    counts = await count_all_campaigns()

    for campaign in campaigns:
        campaign_id = str(campaign.get("campaign_id", "") or "")
        today = daily_stats.get(campaign_id, {})
        progress = progress_stats.get(campaign_id, {})
        campaign["today_total"] = int(today.get("today_total", 0) or 0)
        campaign["today_completed"] = int(today.get("today_completed", 0) or 0)
        campaign["today_booked"] = int(today.get("today_booked", 0) or 0)
        campaign["today_progress"] = int(today.get("today_progress", 0) or 0)
        campaign["booked"] = int(progress.get("booked", 0) or 0)
        campaign["completed_all"] = int(progress.get("completed", 0) or 0)

    return {
        "campaigns": campaigns,
        "counts": counts,
        "date": date,
    }


async def get_all_campaigns_with_stats(
    date: str | None = None,
    include_archived: bool = False,
) -> list[dict]:
    """Return every campaign enriched with participant counts for *date*
    AND overall progress (booked/completed across all dates).

    By default archived campaigns are excluded from the list. When *date*
    is omitted, the dashboard uses the configured operations-day timezone
    instead of inheriting the host machine's local timezone.
    """
    snapshot = await get_dashboard_snapshot(
        date=date,
        include_archived=include_archived,
    )
    return list(snapshot["campaigns"])


# =========================================================================
# Participant CRUD (campaign-scoped)
# =========================================================================

async def upsert_participant(
    campaign_id: str, event_id: str, name: str, email: str,
    appointment_time: str, appointment_date: str,
    default_platform: str = "", default_model_tag: str = "",
    appointment_start_raw: str = "",
    appointment_start_utc: str = "",
    appointment_timezone: str = "",
    appointment_has_time: bool | None = None,
) -> None:
    now = utc_now_iso()
    model_fields = build_participant_model_fields(
        event_id=event_id,
        email=email,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        appointment_start_raw=appointment_start_raw,
        appointment_start_utc=appointment_start_utc,
        appointment_timezone=appointment_timezone,
        appointment_has_time=appointment_has_time,
    )
    await _participants().update_one(
        {"campaign_id": campaign_id, "google_event_id": event_id},
        {
            "$set": {
                "name": name, "email": email,
                **model_fields,
                "updated_at": now,
            },
            "$setOnInsert": {
                "campaign_id": campaign_id,
                "google_event_id": event_id,
                "platform": default_platform, "model_tag": default_model_tag,
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
    cursor = _participants().find(query)
    out: list[dict] = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(_backfill_participant_doc(doc))
    return sorted(out, key=_participant_sort_key)


async def update_participant_field(
    campaign_id: str, event_id: str, field: str, value: Any,
) -> None:
    now = utc_now_iso()
    if field in {"email", "appointment_date", "appointment_time"}:
        doc = await _participants().find_one(
            {"campaign_id": campaign_id, "google_event_id": event_id},
            {
                "email": 1,
                "appointment_date": 1,
                "appointment_time": 1,
            },
        )
        if doc is not None:
            email = value if field == "email" else doc.get("email", "")
            appointment_date = value if field == "appointment_date" else doc.get("appointment_date", "")
            appointment_time = value if field == "appointment_time" else doc.get("appointment_time", "")
            related_fields = build_participant_model_fields(
                event_id=event_id,
                email=str(email or ""),
                appointment_date=str(appointment_date or ""),
                appointment_time=str(appointment_time or ""),
            )
            await _participants().update_one(
                {"campaign_id": campaign_id, "google_event_id": event_id},
                {"$set": {field: value, **related_fields, "updated_at": now}},
            )
            return
    await _participants().update_one(
        {"campaign_id": campaign_id, "google_event_id": event_id},
        {"$set": {field: value, "updated_at": now}},
    )


async def update_participant_identity_and_schedule(
    campaign_id: str,
    event_id: str,
    *,
    name: str,
    email: str,
    appointment_date: str,
    appointment_time: str,
) -> None:
    """Persist participant name/email/date/time together with normalized fields."""
    now = utc_now_iso()
    model_fields = build_participant_model_fields(
        event_id=event_id,
        email=email,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
    )
    await _participants().update_one(
        {"campaign_id": campaign_id, "google_event_id": event_id},
        {
            "$set": {
                "name": name,
                "email": email,
                **model_fields,
                "updated_at": now,
            },
        },
    )


async def update_participant_status(
    campaign_id: str, event_id: str, new_status: str,
) -> None:
    if new_status not in FIXED_PARTICIPANT_STATUSES:
        raise ValueError(
            f"Unsupported participant status: {new_status!r}. "
            f"Expected one of {FIXED_PARTICIPANT_STATUSES}."
        )
    now = utc_now_iso()
    update: dict[str, Any] = {"status": new_status, "updated_at": now}
    if new_status == "Completed":
        update["end_time"] = now
    elif new_status == "Booked":
        update["start_time"] = None
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
    default_platform: str = "",
    default_model_tag: str = "",
) -> str:
    """Insert a participant manually (not from calendar).

    Returns the generated event_id.
    """
    event_id = f"manual-{secrets.token_hex(6)}"
    now = utc_now_iso()
    model_fields = build_participant_model_fields(
        event_id=event_id,
        email=email,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
    )
    await _participants().insert_one({
        "campaign_id": campaign_id,
        "google_event_id": event_id,
        "name": name,
        "email": email,
        **model_fields,
        "platform": default_platform,
        "model_tag": default_model_tag,
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
    now = utc_now_iso()
    result = await _participants().update_many(
        {"campaign_id": campaign_id, "google_event_id": {"$in": event_ids}},
        {"$set": {field: value, "updated_at": now}},
    )
    return result.modified_count


async def bulk_update_participant_status(
    campaign_id: str,
    event_ids: list[str],
    new_status: str,
) -> int:
    """Update participant statuses in bulk using the fixed two-status workflow."""
    if new_status not in FIXED_PARTICIPANT_STATUSES:
        raise ValueError(
            f"Unsupported participant status: {new_status!r}. "
            f"Expected one of {FIXED_PARTICIPANT_STATUSES}."
        )

    now = utc_now_iso()
    update: dict[str, Any] = {"status": new_status, "updated_at": now}
    if new_status == "Completed":
        update["end_time"] = now
    else:
        update["start_time"] = None
        update["end_time"] = None

    result = await _participants().update_many(
        {"campaign_id": campaign_id, "google_event_id": {"$in": event_ids}},
        {"$set": update},
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
    cursor = _participants().find(query)
    participants: list[dict] = []
    async for doc in cursor:
        participants.append(_backfill_participant_doc(doc))
    participants = sorted(participants, key=_participant_sort_key)
    out: list[dict] = []
    for doc in participants:
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


async def get_platform_model_breakdown(campaign_id: str) -> dict:
    """Return per-platform, per-model participant counts.

    Returns ``{platform: {model_tag: {total: N, completed: N}}}``.
    Only includes participants that have a non-empty platform field.
    """
    pipeline = [
        {"$match": {"campaign_id": campaign_id, "platform": {"$ne": ""}}},
        {"$group": {
            "_id": {"platform": "$platform", "model_tag": "$model_tag"},
            "total": {"$sum": 1},
            "completed": {
                "$sum": {"$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]},
            },
        }},
    ]
    result: dict[str, dict[str, dict]] = {}
    async for doc in _participants().aggregate(pipeline):
        platform = doc["_id"]["platform"]
        model = doc["_id"].get("model_tag") or ""
        if platform not in result:
            result[platform] = {}
        result[platform][model] = {
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
        "device_types": source.get("device_types", []),
        "device_quota": source.get("device_quota", {}),
        "default_platform": source.get("default_platform", ""),
        "default_model_tag": source.get("default_model_tag", ""),
        "calendar_id": source.get("calendar_id", "primary"),
        "calendar_filter": source.get("calendar_filter", ""),
        "calendar_ids": source.get("calendar_ids", []),
    })
