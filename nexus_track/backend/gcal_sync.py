"""
Google Calendar sync — campaign-aware, multi-calendar.

Each campaign can specify:
 • A *single* ``calendar_id`` + ``calendar_filter`` (legacy/simple), **or**
 • A list of ``calendar_ids`` entries, each with its own filter.

Appointment-booking tools (Calendly, Cal.com, Acuity, etc.) write straight
into Google Calendar, so syncing the relevant calendar already captures those
bookings — no extra integration needed.

Set the campaign's ``calendar_filter`` to a keyword present in the event
title so only matching bookings are imported.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .mongo_client import ensure_indexes, upsert_participant

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CREDENTIALS_PATH = os.path.join(_PROJECT_ROOT, "credentials.json")
TOKEN_PATH = os.path.join(_PROJECT_ROOT, "token.json")
_TOKEN_CACHE = os.path.join("/tmp", "nexus_token_cache.json")

_cached_creds: Credentials | None = None
_calendar_timezone_cache: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_headless() -> bool:
    no_display = (
        os.environ.get("DISPLAY") is None
        and os.environ.get("WAYLAND_DISPLAY") is None
        and os.environ.get("BROWSER") is None
    )
    return no_display or os.path.exists("/.dockerenv")


def _save_token(creds: Credentials) -> None:
    for path in (TOKEN_PATH, _TOKEN_CACHE):
        try:
            with open(path, "w") as f:
                f.write(creds.to_json())
            return
        except OSError:
            continue
    log.warning("Could not persist token to any writable path")


def _resolve_timezone_name(timezone_name: str | None) -> str:
    raw = str(timezone_name or "").strip()
    if not raw:
        return "UTC"
    try:
        ZoneInfo(raw)
        return raw
    except ZoneInfoNotFoundError:
        return "UTC"


def _zoneinfo_or_utc(timezone_name: str | None) -> ZoneInfo:
    return ZoneInfo(_resolve_timezone_name(timezone_name))


def _get_calendar_timezone(calendar_id: str) -> str:
    cached = _calendar_timezone_cache.get(calendar_id)
    if cached:
        return cached
    service = build("calendar", "v3", credentials=_get_credentials())
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    resolved = _resolve_timezone_name(calendar.get("timeZone"))
    _calendar_timezone_cache[calendar_id] = resolved
    return resolved


def _calendar_day_bounds(
    date_str: str | None,
    calendar_timezone: str,
) -> tuple[datetime, datetime, str]:
    zone = _zoneinfo_or_utc(calendar_timezone)
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        target_date = datetime.now(zone).date()
    start = datetime.combine(target_date, datetime.min.time(), tzinfo=zone)
    end = start + timedelta(days=1)
    return start, end, target_date.strftime("%Y-%m-%d")


def _normalize_google_event_start(
    start: dict,
    *,
    calendar_timezone: str,
) -> dict[str, object]:
    raw_datetime = str(start.get("dateTime", "") or "").strip()
    raw_date = str(start.get("date", "") or "").strip()
    timezone_name = _resolve_timezone_name(calendar_timezone)
    zone = _zoneinfo_or_utc(timezone_name)

    if raw_datetime:
        parsed = datetime.fromisoformat(raw_datetime.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=zone)
        local_dt = parsed.astimezone(zone)
        return {
            "appointment_date": local_dt.strftime("%Y-%m-%d"),
            "appointment_time": local_dt.strftime("%H:%M"),
            "appointment_start_raw": raw_datetime,
            "appointment_start_utc": parsed.astimezone(timezone.utc).isoformat(),
            "appointment_timezone": timezone_name,
            "appointment_has_time": True,
        }

    return {
        "appointment_date": raw_date,
        "appointment_time": "",
        "appointment_start_raw": raw_date,
        "appointment_start_utc": "",
        "appointment_timezone": timezone_name,
        "appointment_has_time": False,
    }


# ---------------------------------------------------------------------------
# Google Auth
# ---------------------------------------------------------------------------

def _get_credentials() -> Credentials:
    global _cached_creds
    if _cached_creds and _cached_creds.valid:
        return _cached_creds

    creds: Credentials | None = None
    for path in (_TOKEN_CACHE, TOKEN_PATH):
        if os.path.isfile(path):
            try:
                creds = Credentials.from_authorized_user_file(path, SCOPES)
                break
            except Exception:
                continue

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    "credentials.json not found. Download OAuth 2.0 Desktop "
                    "credentials from Google Cloud Console."
                )
            if _is_headless():
                raise RuntimeError(
                    "No valid token.json — cannot open browser in Docker. "
                    "Run  python3 generate_token.py  on your host first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            _save_token(creds)

    _cached_creds = creds
    return creds


def generate_token() -> None:
    """Run on a machine with a browser to create token.json."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(f"Put credentials.json at: {CREDENTIALS_PATH}")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"✅  Token saved → {TOKEN_PATH}")


# ---------------------------------------------------------------------------
# Fetch events for a specific date (synchronous — offloaded to thread)
# ---------------------------------------------------------------------------

def _fetch_events_for_date(
    calendar_id: str = "primary",
    date_str: str | None = None,
) -> list[dict]:
    """Fetch events for a given *date_str* (YYYY-MM-DD) or today."""
    service = build("calendar", "v3", credentials=_get_credentials())
    calendar_timezone = _get_calendar_timezone(calendar_id)
    sod, eod, _ = _calendar_day_bounds(date_str, calendar_timezone)

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=sod.isoformat(),
            timeMax=eod.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            timeZone=calendar_timezone,
        )
        .execute()
    )

    parsed: list[dict] = []
    for ev in result.get("items", []):
        summary = ev.get("summary", "No Title")
        name, email = summary, ""
        for att in ev.get("attendees", []):
            if not att.get("organizer", False):
                name = att.get("displayName", summary)
                email = att.get("email", "")
                break
        else:
            atts = ev.get("attendees", [])
            if atts:
                name = atts[0].get("displayName", summary)
                email = atts[0].get("email", "")

        start = ev.get("start", {})
        appointment = _normalize_google_event_start(
            start,
            calendar_timezone=calendar_timezone,
        )

        parsed.append({
            "event_id": ev["id"],
            "name": name,
            "email": email,
            "summary": summary,
            **appointment,
        })
    return parsed


# ---------------------------------------------------------------------------
# Multi-calendar: list all calendar IDs visible to the user
# ---------------------------------------------------------------------------

def _list_calendars() -> list[dict]:
    """Return [{id, summary, primary}] for all calendars the user can see."""
    service = build("calendar", "v3", credentials=_get_credentials())
    result = service.calendarList().list().execute()
    return [
        {
            "id": entry["id"],
            "summary": entry.get("summary", entry["id"]),
            "primary": entry.get("primary", False),
        }
        for entry in result.get("items", [])
    ]


async def list_calendars() -> list[dict]:
    """Async wrapper around _list_calendars."""
    return await asyncio.to_thread(_list_calendars)


# ---------------------------------------------------------------------------
# Public: campaign-aware sync (supports multi-calendar)
# ---------------------------------------------------------------------------

async def sync_calendar_for_campaign(
    campaign: dict,
    date_str: str | None = None,
) -> int:
    """Sync events for a single campaign across all its calendars.

    *date_str* defaults to today when ``None``.
    """
    await ensure_indexes()
    cid = campaign["campaign_id"]

    # Build list of (calendar_id, keyword) pairs ─ supports legacy + multi.
    cal_configs: list[tuple[str, str]] = []

    # New multi-calendar field
    for entry in campaign.get("calendar_ids", []):
        c_id = (entry.get("calendar_id") or "").strip()
        c_kw = (entry.get("filter") or "").strip().lower()
        if c_id:
            cal_configs.append((c_id, c_kw))

    # Legacy single-calendar fallback
    if not cal_configs:
        legacy_id = campaign.get("calendar_id") or "primary"
        legacy_kw = (campaign.get("calendar_filter") or "").strip().lower()
        cal_configs.append((legacy_id, legacy_kw))

    total_synced = 0
    for cal_id, keyword in cal_configs:
        events = await asyncio.to_thread(
            _fetch_events_for_date, cal_id, date_str,
        )

        if keyword:
            events = [
                e for e in events
                if keyword in e["summary"].lower()
                or keyword in e["name"].lower()
            ]

        for e in events:
            await upsert_participant(
                campaign_id=cid,
                event_id=e["event_id"],
                name=e["name"],
                email=e["email"],
                appointment_time=e["appointment_time"],
                appointment_date=e["appointment_date"],
                default_platform=campaign.get("default_platform", ""),
                default_model_tag=campaign.get("default_model_tag", ""),
                appointment_start_raw=str(e.get("appointment_start_raw", "") or ""),
                appointment_start_utc=str(e.get("appointment_start_utc", "") or ""),
                appointment_timezone=str(e.get("appointment_timezone", "") or ""),
                appointment_has_time=bool(e.get("appointment_has_time")),
            )
        total_synced += len(events)

    return total_synced


async def sync_campaign_date_range(
    campaign: dict,
    start_date: str,
    end_date: str,
) -> dict:
    """Sync events for a date range (inclusive).

    Returns ``{synced: int, days: int}`` with totals.
    """
    from datetime import datetime as _dt, timedelta as _td  # noqa: local import to keep top-level clean

    start = _dt.strptime(start_date, "%Y-%m-%d")
    end = _dt.strptime(end_date, "%Y-%m-%d")
    if end < start:
        start, end = end, start

    total_synced = 0
    days = 0
    current = start
    while current <= end:
        ds = current.strftime("%Y-%m-%d")
        count = await sync_calendar_for_campaign(campaign, ds)
        total_synced += count
        days += 1
        current += _td(days=1)

    return {"synced": total_synced, "days": days}
