"""
Nexus-Track \u2014 global application state.

Manages campaigns, participants, calendar sync, auto-refresh,
settings / labels, date navigation, campaign editing, inline notes,
multi-calendar support, sorting, bulk actions, search, archive,
manual participant add, and CSV export.
"""

import asyncio
import csv
import io
import logging
from datetime import datetime, timedelta

import reflex as rx

from .backend.gcal_sync import list_calendars, sync_calendar_for_campaign, sync_campaign_date_range
from .backend.mongo_client import (
    add_manual_participant,
    count_all_campaigns,
    bulk_delete_participants as db_bulk_delete,
    bulk_update_participant_field as db_bulk_update,
    bulk_update_participant_status as db_bulk_update_status,
    clone_campaign as db_clone_campaign,
    create_campaign as db_create_campaign,
    delete_campaign as db_delete_campaign,
    delete_participant as db_delete_participant,
    ensure_indexes,
    get_admin_pin_hash,
    get_all_campaigns_with_stats,
    get_recent_audit_events,
    get_campaign,
    get_participants_for_campaign,
    get_participants_for_export,
    get_settings,
    hash_admin_pin as db_hash_admin_pin,
    record_audit_event as db_record_audit_event,
    set_admin_pin as db_set_admin_pin,
    update_campaign as db_update_campaign,
    update_campaign_field as db_update_campaign_field,
    update_label_list,
    update_participant_field as db_update_field,
    update_participant_status as db_update_status,
    update_platform_model_tags as db_update_platform_model_tags,
    verify_admin_pin as db_verify_admin_pin,
)

log = logging.getLogger(__name__)

_auto_refresh_running = False


def _to_plain_python(obj):
    """Recursively convert MutableProxy and other Reflex proxies to plain Python objects."""
    if obj is None:
        return None
    # Check if it's a MutableProxy or similar Reflex proxy type
    obj_type_name = type(obj).__name__
    if "Proxy" in obj_type_name or "ImmutableProxy" in obj_type_name:
        # Convert to the underlying type
        if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            try:
                if isinstance(obj, dict):
                    return {k: _to_plain_python(v) for k, v in obj.items()}
                else:
                    return [_to_plain_python(item) for item in obj]
            except (TypeError, AttributeError):
                return obj
        return obj
    elif isinstance(obj, dict):
        return {k: _to_plain_python(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_to_plain_python(item) for item in obj]
    return obj


def _participant_identity_key(participant: dict) -> str:
    email = str(participant.get("email", "") or "").strip().lower()
    if email:
        return f"email:{email}"
    return f"event:{participant.get('google_event_id', '')}"


def _compute_campaign_progress_from_participants(
    participants: list[dict],
) -> dict[str, int]:
    booked: set[str] = set()
    completed: set[str] = set()
    for participant in participants:
        key = _participant_identity_key(participant)
        booked.add(key)
        if participant.get("status") == "Completed":
            completed.add(key)
    return {"booked": len(booked), "completed": len(completed)}


def _compute_per_device_progress_from_participants(
    participants: list[dict],
) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for participant in participants:
        platform = str(participant.get("platform", "") or "").strip()
        if not platform:
            continue
        row = result.setdefault(platform, {"total": 0, "completed": 0})
        row["total"] += 1
        if participant.get("status") == "Completed":
            row["completed"] += 1
    return result


def _compute_platform_model_breakdown_from_participants(
    participants: list[dict],
) -> dict[str, dict[str, dict]]:
    result: dict[str, dict[str, dict]] = {}
    for participant in participants:
        platform = str(participant.get("platform", "") or "").strip()
        if not platform:
            continue
        model_tag = str(participant.get("model_tag", "") or "")
        platform_rows = result.setdefault(platform, {})
        row = platform_rows.setdefault(model_tag, {"total": 0, "completed": 0})
        row["total"] += 1
        if participant.get("status") == "Completed":
            row["completed"] += 1
    return result


def _filter_selection_to_visible(
    selected_ids: list[str],
    visible_ids: list[str],
) -> list[str]:
    visible = set(visible_ids)
    return [event_id for event_id in selected_ids if event_id in visible]


class BreakdownModel(rx.Base):
    model: str = ""
    total: int = 0
    completed: int = 0
    pct: int = 0


class BreakdownPlatform(rx.Base):
    platform: str = ""
    total: int = 0
    completed: int = 0
    pct: int = 0
    near_full: bool = False
    is_expanded: bool = False
    models: list[BreakdownModel] = []


class PlatformModelConfig(rx.Base):
    platform: str = ""
    tags: list[str] = []
    input_value: str = ""


class PlatformOption(rx.Base):
    name: str = ""
    selected: bool = False


class AuditEvent(rx.Base):
    timestamp: str = ""
    summary: str = ""
    action: str = ""
    resource_label: str = ""


class NexusState(rx.State):
    """Single state class for the entire multi-page app."""

    # SETTINGS / LABELS
    platforms: list[str] = ["Orb", "Kiosk-v1", "Kiosk-v2", "Self-Serve", "Other"]

    new_platform: str = ""
    new_model_tag: str = ""
    model_tag_add_platform: str = ""
    model_tag_inputs: dict = {}

    available_calendars: list[dict] = []
    calendars_loading: bool = False

    # ADMIN MODE
    admin_mode: bool = False
    admin_pin_input: str = ""
    admin_error: str = ""
    has_admin_pin: bool = False
    new_admin_pin: str = ""
    admin_login_attempts: int = 0
    admin_lockout_until: str = ""
    recent_admin_actions: list[AuditEvent] = []

    # LOADING STATE
    is_loading: bool = False

    # DASHBOARD
    campaigns: list[dict] = []
    all_campaigns_count: int = 0
    all_active_count: int = 0
    all_completed_count: int = 0
    campaign_search_query: str = ""
    show_archived: bool = False
    campaign_device_filter: str = ""
    campaign_sort_field: str = "created_at"

    # DATE NAVIGATION
    selected_date: str = ""

    # CAMPAIGN DETAIL
    current_campaign: dict = {}
    active_campaign_id: str = ""
    participants: list[dict] = []
    search_query: str = ""
    per_device_stats: dict = {}
    platform_model_breakdown: dict = {}
    platform_model_tags: dict = {}
    expanded_platform_panels: list[str] = []
    device_breakdown_open: bool = False

    # SORTING
    sort_field: str = "appointment_time"
    sort_dir: str = "asc"

    # SECTION COLLAPSE
    bookings_collapsed: bool = False
    completed_collapsed: bool = True

    # PARTICIPANT FILTERS
    filter_platform: str = ""
    filter_status: str = ""
    filter_date: str = ""
    filter_has_issue: bool = False

    # BULK SELECTION
    selected_ids: list[str] = []
    bulk_platform_value: str = ""
    bulk_model_value: str = ""

    # MANUAL ADD PARTICIPANT
    show_add_participant: bool = False
    add_name: str = ""
    add_email: str = ""
    add_date: str = ""
    add_time: str = ""

    # SYNC
    is_syncing: bool = False
    last_sync_time: str = ""
    sync_error: str = ""
    detail_error: str = ""

    # CAMPAIGN FORM
    form_name: str = ""
    form_description: str = ""
    form_booking_url: str = ""
    form_notion_url: str = ""
    form_linear_url: str = ""
    form_deadline: str = ""
    form_goal: str = "100"
    form_calendar_id: str = "primary"
    form_calendar_filter: str = ""
    form_error: str = ""
    form_is_edit: bool = False
    form_edit_campaign_id: str = ""
    form_device_types: list[str] = []
    form_device_quota: dict = {}
    form_default_platform: str = ""
    form_default_model_tag: str = ""

    # ISSUE TRACKING
    editing_issue_event_id: str = ""
    editing_issue_comment: str = ""

    # RANGE SYNC
    sync_start_date: str = ""
    sync_end_date: str = ""
    range_sync_result: str = ""

    # DELETE CONFIRMATION
    show_delete_dialog: bool = False

    # PARTICIPANT DELETE
    show_delete_participant_dialog: bool = False
    delete_participant_event_id: str = ""
    delete_participant_name: str = ""

    # EDIT PARTICIPANT
    show_edit_participant: bool = False
    edit_participant_eid: str = ""
    edit_participant_name: str = ""
    edit_participant_email: str = ""
    edit_participant_date: str = ""
    edit_participant_time: str = ""

    # BULK DELETE CONFIRMATION
    show_bulk_delete_dialog: bool = False

    def _get_date(self) -> str:
        return self.selected_date or datetime.now().strftime("%Y-%m-%d")

    # COMPUTED VARS

    @rx.var(cache=True)
    def total_count(self) -> int:
        return len(self.participants)

    @rx.var(cache=True)
    def completed_count(self) -> int:
        return sum(1 for p in self.participants if p.get("status") == "Completed")

    @rx.var(cache=True)
    def avg_session_minutes(self) -> int:
        """Mean duration (minutes) of completed sessions with timestamps."""
        durations = []
        for p in self.participants:
            st, et = p.get("start_time"), p.get("end_time")
            if st and et:
                try:
                    d = (datetime.fromisoformat(et) - datetime.fromisoformat(st)).total_seconds() / 60
                    if 0 < d < 480:
                        durations.append(d)
                except Exception:
                    pass
        if len(durations) < 3:
            return 0
        return int(sum(durations) / len(durations))

    @rx.var(cache=True)
    def eta_finish_today(self) -> str:
        """Estimated finish time based on avg session duration and remaining bookings."""
        avg = self.avg_session_minutes
        if avg <= 0:
            return ""
        remaining = self.booked_count
        if remaining <= 0:
            return ""
        eta = datetime.now() + timedelta(minutes=remaining * avg)
        return "~" + eta.strftime("%H:%M")

    @rx.var(cache=True)
    def booked_count(self) -> int:
        return sum(1 for p in self.participants if p.get("status") != "Completed")

    @rx.var(cache=True)
    def progress_pct(self) -> int:
        t = self.total_count
        return int(self.completed_count / t * 100) if t else 0

    @rx.var(cache=True)
    def sorted_filtered_participants(self) -> list[dict]:
        items = self.participants

        # Text search
        if self.search_query:
            q = self.search_query.lower()
            items = [
                p for p in items
                if q in p.get("name", "").lower()
                or q in p.get("email", "").lower()
                or q in p.get("platform", "").lower()
                or q in p.get("model_tag", "").lower()
                or q in p.get("notes", "").lower()
            ]

        # Platform filter
        if self.filter_platform:
            items = [p for p in items if p.get("platform", "") == self.filter_platform]

        # Status filter
        if self.filter_status:
            items = [p for p in items if p.get("status", "") == self.filter_status]

        # Date filter
        if self.filter_date:
            items = [p for p in items if p.get("appointment_date", "") == self.filter_date]

        # Issue filter
        if self.filter_has_issue:
            items = [p for p in items if p.get("issue_comment", "").strip()]

        # Sort
        field = self.sort_field or "appointment_time"
        reverse = self.sort_dir == "desc"
        try:
            items = sorted(items, key=lambda p: (p.get(field) or "").lower(), reverse=reverse)
        except Exception:
            pass
        return items

    @rx.var(cache=True)
    def filtered_participants(self) -> list[dict]:
        return self.sorted_filtered_participants

    @rx.var(cache=True)
    def booked_participants(self) -> list[dict]:
        """Filtered participants that are NOT completed, sorted by date."""
        return [p for p in self.sorted_filtered_participants if p.get("status") != "Completed"]

    @rx.var(cache=True)
    def completed_participants(self) -> list[dict]:
        """Filtered participants that ARE completed, sorted by date."""
        return [p for p in self.sorted_filtered_participants if p.get("status") == "Completed"]

    @rx.var(cache=True)
    def participant_view_is_filtered(self) -> bool:
        return bool(self.search_query or self.active_filter_count)

    @rx.var(cache=True)
    def selection_count(self) -> int:
        return len(self.selected_ids)

    @rx.var(cache=True)
    def selection_label(self) -> str:
        suffix = " visible selected" if self.participant_view_is_filtered else " selected"
        return str(self.selection_count) + suffix

    @rx.var(cache=True)
    def all_selected(self) -> bool:
        visible_count = len(self.sorted_filtered_participants)
        if visible_count == 0:
            return False
        return len(self.selected_ids) >= visible_count

    @rx.var(cache=True)
    def campaign_name(self) -> str:
        return self.current_campaign.get("name", "")

    @rx.var(cache=True)
    def campaign_description(self) -> str:
        return self.current_campaign.get("description", "")

    @rx.var(cache=True)
    def campaign_booking_url(self) -> str:
        return self.current_campaign.get("booking_url", "")

    @rx.var(cache=True)
    def campaign_notion_url(self) -> str:
        return self.current_campaign.get("notion_url", "")

    @rx.var(cache=True)
    def campaign_linear_url(self) -> str:
        return self.current_campaign.get("linear_url", "")

    @rx.var(cache=True)
    def campaign_deadline(self) -> str:
        raw = self.current_campaign.get("deadline", "")
        if not raw:
            return ""
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
            return dt.strftime("%b %d, %Y")
        except Exception:
            return raw

    @rx.var(cache=True)
    def campaign_goal(self) -> int:
        return int(self.current_campaign.get("goal", 100))

    @rx.var(cache=True)
    def campaign_booked(self) -> int:
        return int(self.current_campaign.get("booked", 0))

    @rx.var(cache=True)
    def campaign_completed_all(self) -> int:
        return int(self.current_campaign.get("completed_all", 0))

    @rx.var(cache=True)
    def booked_pct(self) -> int:
        g = self.campaign_goal
        return min(100, int(self.campaign_booked / g * 100)) if g else 0

    @rx.var(cache=True)
    def completed_pct(self) -> int:
        g = self.campaign_goal
        return min(100, int(self.campaign_completed_all / g * 100)) if g else 0

    @rx.var(cache=True)
    def milestone_quarter(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal * 0.25

    @rx.var(cache=True)
    def milestone_half(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal * 0.5

    @rx.var(cache=True)
    def milestone_three_quarter(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal * 0.75

    @rx.var(cache=True)
    def milestone_complete(self) -> bool:
        return self.campaign_completed_all >= self.campaign_goal

    @rx.var(cache=True)
    def campaign_last_sync(self) -> str:
        raw = self.current_campaign.get("last_sync_at", "")
        if not raw:
            return "Never"
        try:
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%b %d %H:%M")
        except Exception:
            return str(raw)

    @rx.var(cache=True)
    def campaign_calendar_filter(self) -> str:
        return self.current_campaign.get("calendar_filter", "")

    @rx.var(cache=True)
    def campaign_calendar_id_display(self) -> str:
        return self.current_campaign.get("calendar_id", "primary")

    @rx.var(cache=True)
    def campaign_status(self) -> str:
        return self.current_campaign.get("status", "active")

    @rx.var(cache=True)
    def campaign_device_types(self) -> list[str]:
        return self.current_campaign.get("device_types", [])

    @rx.var(cache=True)
    def campaign_device_quota(self) -> dict:
        return self.current_campaign.get("device_quota", {})

    @rx.var(cache=True)
    def platform_breakdown_for_render(self) -> list[BreakdownPlatform]:
        """List of platform items with typed nested model lists for rendering."""
        breakdown = self.platform_model_breakdown  # {platform: {model: {total, completed}}}
        config = self.platform_model_tags           # {platform: [model_tags]}
        expanded = set(self.expanded_platform_panels)

        # Filter to only platforms selected for this campaign
        campaign_platforms = set(self.current_campaign.get("device_types", []))

        all_platforms = sorted(set(breakdown.keys()) | set(config.keys()))
        # If campaign has selected platforms, only show those
        if campaign_platforms:
            all_platforms = [p for p in all_platforms if p in campaign_platforms]
        result: list[BreakdownPlatform] = []
        for platform in all_platforms:
            models_data = breakdown.get(platform, {})
            configured_models = config.get(platform, [])
            all_models = sorted(set(models_data.keys()) | set(configured_models))

            platform_total = sum(v.get("total", 0) for v in models_data.values())
            platform_completed = sum(v.get("completed", 0) for v in models_data.values())
            platform_pct = int(platform_completed / platform_total * 100) if platform_total else 0
            near_full = platform_total > 0 and platform_completed >= platform_total * 0.9
            is_expanded = platform in expanded

            models: list[BreakdownModel] = []
            if is_expanded:
                for model in all_models:
                    v = models_data.get(model, {"total": 0, "completed": 0})
                    total = v.get("total", 0)
                    completed = v.get("completed", 0)
                    pct = int(completed / total * 100) if total else 0
                    models.append(BreakdownModel(
                        model=model or "(no model)",
                        total=total,
                        completed=completed,
                        pct=pct,
                    ))

            result.append(BreakdownPlatform(
                platform=platform,
                total=platform_total,
                completed=platform_completed,
                pct=platform_pct,
                near_full=near_full,
                is_expanded=is_expanded,
                models=models,
            ))

        return result

    @rx.var(cache=True)
    def active_filter_count(self) -> int:
        count = 0
        if self.filter_platform:
            count += 1
        if self.filter_status:
            count += 1
        if self.filter_date:
            count += 1
        if self.filter_has_issue:
            count += 1
        return count

    @rx.var(cache=True)
    def participant_dates(self) -> list[str]:
        """Distinct appointment dates from loaded participants."""
        dates = sorted({p.get("appointment_date", "") for p in self.participants if p.get("appointment_date")})
        return dates

    @rx.var(cache=True)
    def campaign_created_at(self) -> str:
        raw = self.current_campaign.get("created_at", "")
        if not raw:
            return ""
        try:
            dt = datetime.fromisoformat(raw)
            return dt.strftime("%b %d, %Y")
        except Exception:
            return raw

    @rx.var(cache=True)
    def active_campaign_count(self) -> int:
        return sum(1 for c in self.campaigns if c.get("status") == "active")

    @rx.var(cache=True)
    def total_participants_today(self) -> int:
        return sum(c.get("today_total", 0) for c in self.campaigns)

    @rx.var(cache=True)
    def total_completed_today(self) -> int:
        return sum(c.get("today_completed", 0) for c in self.campaigns)

    @rx.var(cache=True)
    def overall_progress(self) -> int:
        total = self.total_participants_today
        done = self.total_completed_today
        return int(done / total * 100) if total else 0

    @rx.var(cache=True)
    def filtered_campaigns(self) -> list[dict]:
        items = self.campaigns

        # Text search
        if self.campaign_search_query:
            q = self.campaign_search_query.lower()
            items = [
                c for c in items
                if q in c.get("name", "").lower()
                or q in c.get("description", "").lower()
            ]

        # Device type filter
        if self.campaign_device_filter:
            items = [
                c for c in items
                if self.campaign_device_filter in c.get("device_types", [])
            ]

        # Sort
        sf = self.campaign_sort_field
        if sf == "name":
            items = sorted(items, key=lambda c: c.get("name", "").lower())
        elif sf == "device_type":
            items = sorted(items, key=lambda c: ", ".join(c.get("device_types", [])))
        elif sf == "progress":
            items = sorted(
                items,
                key=lambda c: c.get("completed_all", 0) / max(c.get("goal", 1), 1),
                reverse=True,
            )
        # default: created_at (already sorted from DB)

        return items

    @rx.var(cache=True)
    def display_date_label(self) -> str:
        d = self.selected_date
        today = datetime.now().date()
        if not d:
            return datetime.now().strftime("%A, %B %d")
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            delta = (dt.date() - today).days
            suffix = ""
            if delta == -1:
                suffix = "  \u00b7  Yesterday"
            elif delta == 1:
                suffix = "  \u00b7  Tomorrow"
            return dt.strftime("%A, %B %d") + suffix
        except Exception:
            return d

    @rx.var(cache=True)
    def is_today(self) -> bool:
        d = self.selected_date
        if not d:
            return True
        return d == datetime.now().strftime("%Y-%m-%d")

    @rx.var(cache=True)
    def selected_date_iso(self) -> str:
        return self.selected_date or datetime.now().strftime("%Y-%m-%d")

    # SETTINGS / LABELS

    @rx.var(cache=True)
    def platforms_with_none(self) -> list[str]:
        return ["__none__"] + list(self.platforms)

    @rx.var(cache=True)
    def platform_options(self) -> list[PlatformOption]:
        """Platforms with selected state for the campaign form checkboxes."""
        selected = set(self.form_device_types)
        return [
            PlatformOption(name=p, selected=p in selected)
            for p in self.platforms
        ]

    @rx.var(cache=True)
    def all_model_tags(self) -> list[str]:
        """Flat list of all model tags across all platforms."""
        tags: list[str] = []
        for models in self.platform_model_tags.values():
            if isinstance(models, list):
                for t in models:
                    if t and t not in tags:
                        tags.append(t)
        return sorted(tags)

    @rx.var(cache=True)
    def model_tags_with_none(self) -> list[str]:
        return ["__none__"] + self.all_model_tags

    @rx.var(cache=True)
    def platform_model_configs(self) -> list[PlatformModelConfig]:
        """Typed list for rendering model tags per platform in settings."""
        result: list[PlatformModelConfig] = []
        # Convert MutableProxy dicts to plain dicts to avoid .get() failures
        pmt = dict(self.platform_model_tags) if self.platform_model_tags else {}
        mti = dict(self.model_tag_inputs) if self.model_tag_inputs else {}
        for platform in self.platforms:
            tags = pmt.get(platform, [])
            result.append(PlatformModelConfig(
                platform=platform,
                tags=list(tags) if isinstance(tags, list) else [],
                input_value=mti.get(platform, ""),
            ))
        return result

    @rx.var(cache=True)
    def form_default_platform_display(self) -> str:
        """Convert empty string to sentinel for select display."""
        return "__none__" if self.form_default_platform == "" else self.form_default_platform

    @rx.var(cache=True)
    def form_default_model_tag_display(self) -> str:
        """Convert empty string to sentinel for select display."""
        return "__none__" if self.form_default_model_tag == "" else self.form_default_model_tag

    async def load_settings(self):
        doc = await get_settings()
        self.platforms = doc.get("platforms", self.platforms)
        self.has_admin_pin = bool(doc.get("admin_pin_hash", ""))
        self.platform_model_tags = doc.get("platform_model_tags", {})

    async def load_recent_admin_actions(self):
        rows = await get_recent_audit_events(limit=8)
        events: list[AuditEvent] = []
        for row in rows:
            raw = row.get("created_at", "")
            timestamp = raw
            try:
                timestamp = datetime.fromisoformat(raw).strftime("%b %d, %H:%M")
            except Exception:
                pass
            events.append(AuditEvent(
                timestamp=timestamp,
                summary=row.get("summary", ""),
                action=row.get("action", ""),
                resource_label=row.get("resource_label", ""),
            ))
        self.recent_admin_actions = events

    def _clear_gate_error(self, target: str) -> None:
        self._set_gate_error(target, "")

    def _set_gate_error(self, target: str, message: str) -> None:
        if target == "form":
            self.form_error = message
        elif target == "detail":
            self.detail_error = message
        else:
            self.admin_error = message

    def _require_admin(self, *, target: str, message: str) -> bool:
        if self.admin_mode:
            self._clear_gate_error(target)
            return True
        self._set_gate_error(target, message)
        return False

    async def _log_admin_action(
        self,
        *,
        action: str,
        summary: str,
        resource_type: str = "",
        resource_id: str = "",
        resource_label: str = "",
        metadata: dict | None = None,
        refresh_settings_view: bool = False,
    ) -> None:
        await db_record_audit_event(
            action=action,
            summary=summary,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_label=resource_label,
            metadata=metadata,
        )
        if refresh_settings_view:
            await self.load_recent_admin_actions()

    def _decorate_participants_for_ui(self, participants: list[dict]) -> list[dict]:
        selected = set(self.selected_ids)
        plain = _to_plain_python(participants) or []
        out: list[dict] = []
        for participant in plain:
            row = dict(participant)
            row.setdefault("_save_state", "")
            row["_is_selected"] = row.get("google_event_id", "") in selected
            out.append(row)
        return out

    def _visible_participant_ids(self) -> list[str]:
        return [
            participant.get("google_event_id", "")
            for participant in self.sorted_filtered_participants
            if participant.get("google_event_id", "")
        ]

    def _sync_selection_state(self) -> None:
        self.selected_ids = _filter_selection_to_visible(
            list(self.selected_ids),
            self._visible_participant_ids(),
        )
        selected = set(self.selected_ids)
        self.participants = [
            {
                **dict(participant),
                "_is_selected": participant.get("google_event_id", "") in selected,
            }
            for participant in (_to_plain_python(self.participants) or [])
        ]

    def _refresh_loaded_participant_metrics(self) -> None:
        participants = _to_plain_python(self.participants) or []
        progress = _compute_campaign_progress_from_participants(participants)
        self.per_device_stats = _compute_per_device_progress_from_participants(participants)
        self.platform_model_breakdown = _compute_platform_model_breakdown_from_participants(
            participants,
        )
        if self.current_campaign:
            campaign = dict(self.current_campaign)
            campaign["booked"] = progress["booked"]
            campaign["completed_all"] = progress["completed"]
            self.current_campaign = campaign

    def _set_loaded_participants(
        self,
        participants: list[dict],
        *,
        preserve_selection: bool = True,
    ) -> None:
        previous_selection = list(self.selected_ids) if preserve_selection else []
        self.participants = self._decorate_participants_for_ui(participants)
        self.selected_ids = previous_selection
        self._refresh_loaded_participant_metrics()
        self._sync_selection_state()

    def _clear_row_save_states(self) -> None:
        self.participants = [
            {**dict(participant), "_save_state": ""}
            for participant in (_to_plain_python(self.participants) or [])
        ]

    def _set_row_save_state(self, event_ids: list[str], state: str) -> None:
        ids = set(event_ids)
        self.participants = [
            {
                **dict(participant),
                "_save_state": (
                    state if participant.get("google_event_id", "") in ids else ""
                ),
            }
            for participant in (_to_plain_python(self.participants) or [])
        ]

    def _snapshot_participants(self) -> list[dict]:
        return self._decorate_participants_for_ui(self.participants)

    def _apply_participant_updates(self, event_ids: list[str], transform) -> None:
        ids = set(event_ids)
        updated: list[dict] = []
        for participant in (_to_plain_python(self.participants) or []):
            row = dict(participant)
            if row.get("google_event_id", "") in ids:
                row = transform(row)
            updated.append(row)
        self.participants = updated

    async def _run_optimistic_participant_update(
        self,
        *,
        event_ids: list[str],
        apply_local,
        persist,
        refresh_metrics: bool = True,
    ) -> bool:
        if not event_ids:
            return False
        before_selected_ids = list(self.selected_ids)
        self.detail_error = ""
        self._clear_row_save_states()
        before_participants = self._snapshot_participants()
        apply_local()
        self._set_row_save_state(event_ids, "saving")
        if refresh_metrics:
            self._refresh_loaded_participant_metrics()
        self._sync_selection_state()

        try:
            await persist()
        except Exception as exc:
            self.participants = self._decorate_participants_for_ui(before_participants)
            self.selected_ids = before_selected_ids
            self._refresh_loaded_participant_metrics()
            self._sync_selection_state()
            self.detail_error = str(exc)
            return False

        if refresh_metrics:
            try:
                await self._check_auto_complete()
            except Exception as exc:
                self.detail_error = str(exc)

        self._set_row_save_state(event_ids, "saved")
        self._sync_selection_state()
        return True

    def set_new_platform(self, v: str):
        self.new_platform = v

    async def handle_platform_key_down(self, key: str):
        if key == "Enter":
            await self.add_platform()

    async def add_platform(self):
        if not self._require_admin(
            target="admin",
            message="Admin mode is required to edit platform settings.",
        ):
            return
        v = self.new_platform.strip()
        if v and v not in self.platforms:
            self.platforms = list(self.platforms) + [v]
            await update_label_list("platforms", list(self.platforms))
            # Ensure the new platform has an entry in platform_model_tags
            pmt = dict(self.platform_model_tags)
            if v not in pmt:
                pmt[v] = []
                self.platform_model_tags = pmt
                await db_update_platform_model_tags(_to_plain_python(pmt))
            await self._log_admin_action(
                action="add_platform",
                summary=f"Added platform '{v}'.",
                resource_type="settings",
                resource_label=v,
                refresh_settings_view=True,
            )
        self.new_platform = ""

    async def remove_platform(self, label: str):
        if not self._require_admin(
            target="admin",
            message="Admin mode is required to edit platform settings.",
        ):
            return
        self.platforms = [p for p in self.platforms if p != label]
        await update_label_list("platforms", list(self.platforms))
        # Also remove from platform_model_tags
        pmt = dict(self.platform_model_tags)
        pmt.pop(label, None)
        self.platform_model_tags = pmt
        await db_update_platform_model_tags(_to_plain_python(pmt))
        await self._log_admin_action(
            action="remove_platform",
            summary=f"Removed platform '{label}'.",
            resource_type="settings",
            resource_label=label,
            refresh_settings_view=True,
        )

    def set_new_model_tag(self, v: str):
        self.new_model_tag = v

    def set_model_tag_add_platform(self, v: str):
        self.model_tag_add_platform = v

    def set_model_tag_input_for(self, platform: str, value: str):
        """Update the per-platform text input value (isolated, no cross-contamination)."""
        inputs = dict(self.model_tag_inputs)
        inputs[platform] = value
        self.model_tag_inputs = inputs

    async def handle_model_tag_key_down(self, platform: str, key: str):
        if key == "Enter":
            await self.add_platform_model_tag(platform)

    async def add_platform_model_tag(self, platform: str):
        """Add a model tag under a specific platform."""
        if not self._require_admin(
            target="admin",
            message="Admin mode is required to edit model-tag settings.",
        ):
            return
        v = self.model_tag_inputs.get(platform, "").strip()
        if not v:
            return
        pmt = dict(self.platform_model_tags)
        existing = list(pmt.get(platform, []))
        if v not in existing:
            existing.append(v)
            pmt[platform] = existing
            self.platform_model_tags = pmt
            await db_update_platform_model_tags(_to_plain_python(pmt))
            await self._log_admin_action(
                action="add_model_tag",
                summary=f"Added model tag '{v}' to {platform}.",
                resource_type="settings",
                resource_label=platform,
                metadata={"model_tag": v},
                refresh_settings_view=True,
            )
        inputs = dict(self.model_tag_inputs)
        inputs[platform] = ""
        self.model_tag_inputs = inputs

    async def remove_platform_model_tag(self, platform: str, tag: str):
        """Remove a model tag from a specific platform."""
        if not self._require_admin(
            target="admin",
            message="Admin mode is required to edit model-tag settings.",
        ):
            return
        pmt = dict(self.platform_model_tags)
        existing = list(pmt.get(platform, []))
        existing = [t for t in existing if t != tag]
        pmt[platform] = existing
        self.platform_model_tags = pmt
        await db_update_platform_model_tags(_to_plain_python(pmt))
        await self._log_admin_action(
            action="remove_model_tag",
            summary=f"Removed model tag '{tag}' from {platform}.",
            resource_type="settings",
            resource_label=platform,
            metadata={"model_tag": tag},
            refresh_settings_view=True,
        )

    @rx.event(background=True)
    async def fetch_available_calendars(self):
        async with self:
            self.calendars_loading = True
        try:
            cals = await list_calendars()
            async with self:
                self.available_calendars = cals
                self.calendars_loading = False
        except Exception:
            log.exception("Failed to list calendars")
            async with self:
                self.calendars_loading = False

    # ADMIN MODE

    def set_admin_pin_input(self, v: str):
        self.admin_pin_input = v
        self.admin_error = ""

    def set_new_admin_pin(self, v: str):
        self.new_admin_pin = v

    async def login_admin(self):
        if self.admin_lockout_until:
            try:
                lockout_until = datetime.fromisoformat(self.admin_lockout_until)
                if lockout_until > datetime.now():
                    self.admin_error = (
                        "Too many incorrect PIN attempts. "
                        f"Try again after {lockout_until.strftime('%H:%M:%S')}."
                    )
                    return
                self.admin_lockout_until = ""
            except Exception:
                self.admin_lockout_until = ""

        pin = self.admin_pin_input.strip()
        if not pin:
            self.admin_error = "Enter a PIN."
            return
        stored = await get_admin_pin_hash()
        if not stored:
            # No PIN set — first-time setup, accept any PIN
            self.admin_mode = True
            self.admin_error = ""
            self.admin_pin_input = ""
            self.admin_login_attempts = 0
            self.admin_lockout_until = ""
            return
        is_valid, needs_upgrade = db_verify_admin_pin(pin, stored)
        if is_valid:
            self.admin_mode = True
            self.admin_error = ""
            self.admin_pin_input = ""
            self.admin_login_attempts = 0
            self.admin_lockout_until = ""
            if needs_upgrade:
                await db_set_admin_pin(db_hash_admin_pin(pin))
        else:
            self.admin_login_attempts += 1
            if self.admin_login_attempts >= 5:
                self.admin_lockout_until = (
                    datetime.now() + timedelta(minutes=1)
                ).isoformat()
                self.admin_login_attempts = 0
                self.admin_error = (
                    "Too many incorrect PIN attempts. "
                    "Admin login is locked for 1 minute."
                )
            else:
                remaining = 5 - self.admin_login_attempts
                self.admin_error = (
                    "Incorrect PIN. "
                    f"{remaining} attempt(s) remaining before a 1-minute lockout."
                )
            self.admin_pin_input = ""

    async def set_admin_pin_value(self):
        if not self._require_admin(
            target="admin",
            message="Admin mode is required to set or change the admin PIN.",
        ):
            return
        pin = self.new_admin_pin.strip()
        if len(pin) < 4:
            self.admin_error = "PIN must be at least 4 characters."
            return
        pin_hash = db_hash_admin_pin(pin)
        await db_set_admin_pin(pin_hash)
        self.has_admin_pin = True
        self.admin_pin_input = ""
        self.new_admin_pin = ""
        self.admin_error = ""
        await self._log_admin_action(
            action="set_admin_pin",
            summary="Updated the admin PIN.",
            resource_type="settings",
            refresh_settings_view=True,
        )

    def logout_admin(self):
        self.admin_mode = False
        self.admin_pin_input = ""
        self.new_admin_pin = ""
        self.admin_error = ""

    # DASHBOARD FILTERS

    def set_campaign_device_filter(self, v: str):
        self.campaign_device_filter = v

    def set_campaign_sort_field(self, v: str):
        self.campaign_sort_field = v

    # PARTICIPANT FILTERS

    def set_filter_platform(self, v: str):
        self.filter_platform = v
        self._sync_selection_state()

    def set_filter_status(self, v: str):
        self.filter_status = v
        self._sync_selection_state()

    def set_filter_date(self, v: str):
        self.filter_date = v
        self._sync_selection_state()

    def toggle_filter_has_issue(self):
        self.filter_has_issue = not self.filter_has_issue
        self._sync_selection_state()

    def clear_all_filters(self):
        self.filter_platform = ""
        self.filter_status = ""
        self.filter_date = ""
        self.filter_has_issue = False
        self.search_query = ""
        self._sync_selection_state()

    # DATE NAVIGATION

    def go_to_today(self):
        self.selected_date = ""

    def go_prev_day(self):
        d = self._get_date()
        prev = datetime.strptime(d, "%Y-%m-%d") - timedelta(days=1)
        self.selected_date = prev.strftime("%Y-%m-%d")

    def go_next_day(self):
        d = self._get_date()
        nxt = datetime.strptime(d, "%Y-%m-%d") + timedelta(days=1)
        self.selected_date = nxt.strftime("%Y-%m-%d")

    def set_date(self, date_str: str):
        self.selected_date = date_str

    async def _reload_participants(self):
        cid = self.active_campaign_id
        if cid:
            fresh = await get_participants_for_campaign(cid)
            self._set_loaded_participants(fresh, preserve_selection=True)
            await self._check_auto_complete()

    async def _check_auto_complete(self):
        """Mark campaign as completed when completed participants reach the goal."""
        cid = self.active_campaign_id
        if not cid:
            return
        status = self.current_campaign.get("status", "active")
        if status == "completed":
            return
        goal = int(self.current_campaign.get("goal", 100))
        completed = int(self.current_campaign.get("completed_all", 0))
        if goal > 0 and completed >= goal:
            await db_update_campaign_field(cid, "status", "completed")
            camp = dict(self.current_campaign)
            camp["status"] = "completed"
            self.current_campaign = camp

    async def navigate_prev_day(self):
        self.go_prev_day()

    async def navigate_next_day(self):
        self.go_next_day()

    async def navigate_to_today(self):
        self.go_to_today()

    # DASHBOARD

    async def load_campaigns(self):
        self.is_loading = True
        await ensure_indexes()
        await self.load_settings()
        date = self._get_date()
        self.campaigns = await get_all_campaigns_with_stats(
            date, include_archived=self.show_archived,
        )
        counts = await count_all_campaigns()
        self.all_campaigns_count = counts["total"]
        self.all_active_count = counts["active"]
        self.all_completed_count = counts["completed"]
        self.is_loading = False

    def set_campaign_search(self, q: str):
        self.campaign_search_query = q

    async def toggle_show_archived(self):
        self.show_archived = not self.show_archived
        await self.load_campaigns()

    # CAMPAIGN DETAIL

    async def load_campaign_detail(self):
        self.is_loading = True
        cid = self.router.page.params.get("campaign_id", "")
        self.active_campaign_id = cid
        self.search_query = ""
        self.sync_error = ""
        self.detail_error = ""
        self.last_sync_time = ""
        self.range_sync_result = ""
        self.bulk_platform_value = ""
        self.bulk_model_value = ""
        self.show_delete_dialog = False
        self.show_delete_participant_dialog = False
        self.delete_participant_event_id = ""
        self.delete_participant_name = ""
        self.show_bulk_delete_dialog = False
        self.show_edit_participant = False
        self.edit_participant_eid = ""
        self.edit_participant_name = ""
        self.edit_participant_email = ""
        self.edit_participant_date = ""
        self.edit_participant_time = ""
        self.show_add_participant = False
        self.editing_issue_event_id = ""
        self.editing_issue_comment = ""
        self.selected_ids = []
        self.sort_field = "appointment_time"
        self.sort_dir = "asc"
        # Reset participant filters
        self.filter_platform = ""
        self.filter_status = ""
        self.filter_date = ""
        self.filter_has_issue = False
        if not self.selected_date:
            self.selected_date = datetime.now().strftime("%Y-%m-%d")
        if cid:
            await self.load_settings()
            campaign = await get_campaign(cid)
            if campaign:
                self.current_campaign = campaign
                fresh = await get_participants_for_campaign(cid)
                self._set_loaded_participants(fresh, preserve_selection=False)
                self.device_breakdown_open = True
                self.expanded_platform_panels = self._all_visible_platforms()
            else:
                self.current_campaign = {}
                self.participants = self._decorate_participants_for_ui([])
                self.per_device_stats = {}
                self.platform_model_breakdown = {}
                self.expanded_platform_panels = []
        self.is_loading = False

    # SORTING

    def set_sort(self, field: str):
        if self.sort_field == field:
            self.sort_dir = "desc" if self.sort_dir == "asc" else "asc"
        else:
            self.sort_field = field
            self.sort_dir = "asc"

    # BULK SELECTION

    def toggle_select(self, event_id: str):
        if event_id in self.selected_ids:
            self.selected_ids = [i for i in self.selected_ids if i != event_id]
        else:
            self.selected_ids = self.selected_ids + [event_id]
        self._sync_selection_state()

    def select_all(self):
        visible_ids = self._visible_participant_ids()
        if self.all_selected:
            self.selected_ids = []
        else:
            self.selected_ids = visible_ids
        self._sync_selection_state()

    async def bulk_set_status(self, new_status: str):
        cid = self.active_campaign_id
        if cid and self.selected_ids:
            target_ids = list(self.selected_ids)
            await self._run_optimistic_participant_update(
                event_ids=target_ids,
                apply_local=lambda: self._apply_participant_updates(
                    target_ids,
                    lambda participant: {
                        **participant,
                        "status": new_status,
                        "end_time": (
                            datetime.now().isoformat()
                            if new_status == "Completed"
                            else None
                        ),
                        "start_time": (
                            None
                            if new_status == "Booked"
                            else participant.get("start_time")
                        ),
                    },
                ),
                persist=lambda: db_bulk_update_status(cid, target_ids, new_status),
            )

    async def apply_bulk_platform(self):
        cid = self.active_campaign_id
        platform = self.bulk_platform_value
        if cid and self.selected_ids and platform:
            target_ids = list(self.selected_ids)
            await self._run_optimistic_participant_update(
                event_ids=target_ids,
                apply_local=lambda: self._apply_participant_updates(
                    target_ids,
                    lambda participant: {**participant, "platform": platform},
                ),
                persist=lambda: db_bulk_update(cid, target_ids, "platform", platform),
            )
            self.bulk_platform_value = ""

    async def apply_bulk_model(self):
        cid = self.active_campaign_id
        model_tag = self.bulk_model_value
        if cid and self.selected_ids and model_tag:
            target_ids = list(self.selected_ids)
            await self._run_optimistic_participant_update(
                event_ids=target_ids,
                apply_local=lambda: self._apply_participant_updates(
                    target_ids,
                    lambda participant: {**participant, "model_tag": model_tag},
                ),
                persist=lambda: db_bulk_update(
                    cid, target_ids, "model_tag", model_tag,
                ),
            )
            self.bulk_model_value = ""

    def clear_selection(self):
        self.selected_ids = []
        self.bulk_platform_value = ""
        self.bulk_model_value = ""
        self._sync_selection_state()

    def _all_visible_platforms(self) -> list[str]:
        """Compute the set of platforms visible in the breakdown panel."""
        all_platforms = sorted(
            set(self.platform_model_breakdown.keys()) | set(self.platform_model_tags.keys())
        )
        campaign_platforms = set(self.current_campaign.get("device_types", []))
        if campaign_platforms:
            all_platforms = [p for p in all_platforms if p in campaign_platforms]
        return all_platforms

    def toggle_platform_panel(self, platform: str):
        """Expand or collapse a platform card in the breakdown panel."""
        if platform in self.expanded_platform_panels:
            self.expanded_platform_panels = [p for p in self.expanded_platform_panels if p != platform]
        else:
            self.expanded_platform_panels = list(self.expanded_platform_panels) + [platform]

    def toggle_device_breakdown(self):
        """Toggle the Device & Model Breakdown panel. Opening expands all submenus, closing collapses all."""
        self.device_breakdown_open = not self.device_breakdown_open
        if self.device_breakdown_open:
            self.expanded_platform_panels = self._all_visible_platforms()
        else:
            self.expanded_platform_panels = []

    # CAMPAIGN STATUS

    async def set_campaign_status(self, new_status: str):
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to change campaign status.",
        ):
            return
        cid = self.active_campaign_id
        if not cid:
            return
        await db_update_campaign_field(cid, "status", new_status)
        campaign = await get_campaign(cid)
        if campaign:
            campaign["booked"] = int(self.current_campaign.get("booked", 0))
            campaign["completed_all"] = int(
                self.current_campaign.get("completed_all", 0)
            )
            self.current_campaign = campaign
            await self._log_admin_action(
                action="update_campaign_status",
                summary=f"Changed campaign status to {new_status}.",
                resource_type="campaign",
                resource_id=cid,
                resource_label=campaign.get("name", ""),
            )

    # CALENDAR SYNC (background)

    @rx.event(background=True)
    async def sync_campaign_calendar(self):
        async with self:
            self.is_syncing = True
            self.sync_error = ""
            campaign = dict(self.current_campaign)
            cid = self.active_campaign_id
            date = self.selected_date or datetime.now().strftime("%Y-%m-%d")
        try:
            if not campaign:
                raise ValueError("No campaign loaded")
            count = await sync_calendar_for_campaign(campaign, date)
            # Update last_sync_at on the campaign
            from .backend.mongo_client import update_campaign_field as _ucf
            await _ucf(cid, "last_sync_at", datetime.now().isoformat())
            fresh = await get_participants_for_campaign(cid)
            async with self:
                self._set_loaded_participants(fresh, preserve_selection=True)
                camp = dict(self.current_campaign)
                camp["last_sync_at"] = datetime.now().isoformat()
                self.current_campaign = camp
                self.last_sync_time = datetime.now().strftime("%H:%M:%S")
                self.is_syncing = False
        except Exception as exc:
            log.exception("Calendar sync failed")
            async with self:
                self.sync_error = str(exc)
                self.is_syncing = False

    # RANGE SYNC (background)

    def set_sync_start_date(self, v: str):
        self.sync_start_date = v

    def set_sync_end_date(self, v: str):
        self.sync_end_date = v

    @rx.event(background=True)
    async def sync_campaign_range(self):
        """Sync events for a date range instead of a single day."""
        async with self:
            self.is_syncing = True
            self.sync_error = ""
            self.range_sync_result = ""
            campaign = dict(self.current_campaign)
            cid = self.active_campaign_id
            start = self.sync_start_date
            end = self.sync_end_date
        if not start or not end:
            async with self:
                self.sync_error = "Select both start and end dates."
                self.is_syncing = False
            return
        try:
            if not campaign:
                raise ValueError("No campaign loaded")
            result = await sync_campaign_date_range(campaign, start, end)
            # Update last_sync_at on the campaign
            from .backend.mongo_client import update_campaign_field as _ucf
            await _ucf(cid, "last_sync_at", datetime.now().isoformat())
            fresh = await get_participants_for_campaign(cid)
            async with self:
                self._set_loaded_participants(fresh, preserve_selection=True)
                camp = dict(self.current_campaign)
                camp["last_sync_at"] = datetime.now().isoformat()
                self.current_campaign = camp
                self.range_sync_result = (
                    f"Synced {result['synced']} events across {result['days']} days"
                )
                self.is_syncing = False
        except Exception as exc:
            log.exception("Range sync failed")
            async with self:
                self.sync_error = str(exc)
                self.is_syncing = False

    # AUTO-REFRESH (background)

    @rx.event(background=True)
    async def start_auto_refresh(self):
        global _auto_refresh_running
        if _auto_refresh_running:
            return
        _auto_refresh_running = True
        while True:
            await asyncio.sleep(10)
            try:
                async with self:
                    date = self.selected_date or datetime.now().strftime("%Y-%m-%d")
                    cid = self.active_campaign_id
                    show_arch = self.show_archived
                fresh_campaigns = await get_all_campaigns_with_stats(
                    date, include_archived=show_arch,
                )
                counts = await count_all_campaigns()
                async with self:
                    self.campaigns = fresh_campaigns
                    self.all_campaigns_count = counts["total"]
                    self.all_active_count = counts["active"]
                    self.all_completed_count = counts["completed"]
                if cid:
                    fresh = await get_participants_for_campaign(cid)
                    async with self:
                        self._set_loaded_participants(fresh, preserve_selection=True)
            except Exception:
                pass

    # PARTICIPANT MUTATIONS

    async def set_platform(self, event_id: str, platform: str):
        cid = self.active_campaign_id
        if cid:
            await self._run_optimistic_participant_update(
                event_ids=[event_id],
                apply_local=lambda: self._apply_participant_updates(
                    [event_id],
                    lambda participant: {**participant, "platform": platform},
                ),
                persist=lambda: db_update_field(cid, event_id, "platform", platform),
            )

    async def set_model_tag(self, event_id: str, model_tag: str):
        cid = self.active_campaign_id
        if cid:
            await self._run_optimistic_participant_update(
                event_ids=[event_id],
                apply_local=lambda: self._apply_participant_updates(
                    [event_id],
                    lambda participant: {**participant, "model_tag": model_tag},
                ),
                persist=lambda: db_update_field(
                    cid, event_id, "model_tag", model_tag,
                ),
            )

    async def set_status(self, event_id: str, new_status: str):
        cid = self.active_campaign_id
        if cid:
            await self._run_optimistic_participant_update(
                event_ids=[event_id],
                apply_local=lambda: self._apply_participant_updates(
                    [event_id],
                    lambda participant: {
                        **participant,
                        "status": new_status,
                        "end_time": (
                            datetime.now().isoformat()
                            if new_status == "Completed"
                            else None
                        ),
                        "start_time": (
                            None
                            if new_status == "Booked"
                            else participant.get("start_time")
                        ),
                    },
                ),
                persist=lambda: db_update_status(cid, event_id, new_status),
            )

    async def toggle_completed(self, event_id: str):
        """Toggle a participant between Booked and Completed."""
        cid = self.active_campaign_id
        if not cid:
            return
        new_status = "Completed"
        for p in self.participants:
            if p.get("google_event_id") == event_id:
                new_status = (
                    "Booked" if p.get("status") == "Completed" else "Completed"
                )
                break
        await self.set_status(event_id, new_status)

    async def set_notes(self, event_id: str, notes: str):
        cid = self.active_campaign_id
        if cid:
            await self._run_optimistic_participant_update(
                event_ids=[event_id],
                apply_local=lambda: self._apply_participant_updates(
                    [event_id],
                    lambda participant: {**participant, "notes": notes},
                ),
                persist=lambda: db_update_field(cid, event_id, "notes", notes),
                refresh_metrics=False,
            )

    # EDIT PARTICIPANT

    def open_edit_participant(self, event_id: str):
        for p in self.participants:
            if p.get("google_event_id") == event_id:
                self.edit_participant_eid = event_id
                self.edit_participant_name = p.get("name", "")
                self.edit_participant_email = p.get("email", "")
                self.edit_participant_date = p.get("appointment_date", "")
                self.edit_participant_time = p.get("appointment_time", "")
                self.show_edit_participant = True
                break

    def close_edit_participant(self):
        self.show_edit_participant = False

    def set_edit_participant_name(self, v: str):
        self.edit_participant_name = v

    def set_edit_participant_email(self, v: str):
        self.edit_participant_email = v

    def set_edit_participant_date(self, v: str):
        self.edit_participant_date = v

    def set_edit_participant_time(self, v: str):
        self.edit_participant_time = v

    async def _persist_edit_participant(
        self,
        cid: str,
        eid: str,
        name: str,
        email: str,
        appointment_date: str,
        appointment_time: str,
    ) -> None:
        await db_update_field(cid, eid, "name", name)
        await db_update_field(cid, eid, "email", email)
        await db_update_field(cid, eid, "appointment_date", appointment_date)
        await db_update_field(cid, eid, "appointment_time", appointment_time)

    async def save_edit_participant(self):
        cid = self.active_campaign_id
        eid = self.edit_participant_eid
        if not cid or not eid:
            return
        new_name = self.edit_participant_name.strip()
        new_email = self.edit_participant_email.strip()
        new_date = self.edit_participant_date.strip()
        new_time = self.edit_participant_time.strip()
        saved = await self._run_optimistic_participant_update(
            event_ids=[eid],
            apply_local=lambda: self._apply_participant_updates(
                [eid],
                lambda participant: {
                    **participant,
                    "name": new_name,
                    "email": new_email,
                    "appointment_date": new_date,
                    "appointment_time": new_time,
                },
            ),
            persist=lambda: self._persist_edit_participant(
                cid, eid, new_name, new_email, new_date, new_time,
            ),
        )
        if saved:
            self.show_edit_participant = False
            self.edit_participant_eid = ""
            self.edit_participant_name = ""
            self.edit_participant_email = ""
            self.edit_participant_date = ""
            self.edit_participant_time = ""

    # ISSUE TRACKING

    def open_issue_editor(self, event_id: str):
        """Open the issue comment editor for a participant."""
        self.editing_issue_event_id = event_id
        # Pre-fill with existing comment
        for p in self.participants:
            if p.get("google_event_id") == event_id:
                self.editing_issue_comment = p.get("issue_comment", "")
                break

    def set_editing_issue_comment(self, v: str):
        self.editing_issue_comment = v

    async def save_issue_comment(self):
        """Save the issue comment and close editor."""
        cid = self.active_campaign_id
        eid = self.editing_issue_event_id
        comment = self.editing_issue_comment.strip()
        if cid and eid:
            saved = await self._run_optimistic_participant_update(
                event_ids=[eid],
                apply_local=lambda: self._apply_participant_updates(
                    [eid],
                    lambda participant: {
                        **participant,
                        "issue_comment": comment,
                    },
                ),
                persist=lambda: db_update_field(
                    cid, eid, "issue_comment", comment,
                ),
                refresh_metrics=False,
            )
            if saved:
                self.editing_issue_event_id = ""
                self.editing_issue_comment = ""

    def close_issue_editor(self):
        self.editing_issue_event_id = ""
        self.editing_issue_comment = ""

    async def toggle_issue_flag(self, event_id: str):
        """Toggle issue flag: if comment exists, clear it; if empty, open editor."""
        for p in self.participants:
            if p.get("google_event_id") == event_id:
                if p.get("issue_comment", "").strip():
                    await self._run_optimistic_participant_update(
                        event_ids=[event_id],
                        apply_local=lambda: self._apply_participant_updates(
                            [event_id],
                            lambda participant: {
                                **participant,
                                "issue_comment": "",
                            },
                        ),
                        persist=lambda: db_update_field(
                            self.active_campaign_id,
                            event_id,
                            "issue_comment",
                            "",
                        ),
                        refresh_metrics=False,
                    )
                else:
                    # Open editor
                    self.open_issue_editor(event_id)
                break

    def set_search(self, query: str):
        self.search_query = query
        self._sync_selection_state()

    def set_bulk_platform_value(self, value: str):
        self.bulk_platform_value = value

    def set_bulk_model_value(self, value: str):
        self.bulk_model_value = value

    # MANUAL PARTICIPANT ADD

    def toggle_add_participant(self):
        self.show_add_participant = not self.show_add_participant
        self.add_name = ""
        self.add_email = ""
        self.add_date = datetime.now().strftime("%Y-%m-%d")
        self.add_time = ""

    def set_add_name(self, v: str):
        self.add_name = v

    def set_add_email(self, v: str):
        self.add_email = v

    def set_add_date(self, v: str):
        self.add_date = v

    def set_add_time(self, v: str):
        self.add_time = v

    async def submit_add_participant(self):
        name = self.add_name.strip()
        if not name:
            return
        cid = self.active_campaign_id
        await add_manual_participant(
            campaign_id=cid,
            name=name,
            email=self.add_email.strip(),
            appointment_date=self.add_date.strip(),
            appointment_time=self.add_time.strip(),
            default_platform=self.current_campaign.get("default_platform", ""),
            default_model_tag=self.current_campaign.get("default_model_tag", ""),
        )
        self.show_add_participant = False
        self.add_name = ""
        self.add_email = ""
        self.add_date = ""
        self.add_time = ""
        await self._reload_participants()

    # CSV EXPORT

    async def export_csv(self):
        cid = self.active_campaign_id
        if not cid:
            return
        rows = await get_participants_for_export(cid)
        if not rows:
            return
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["name", "email", "date", "time", "platform", "model_tag", "status", "notes", "issue_comment"],
        )
        writer.writeheader()
        writer.writerows(rows)
        csv_str = buf.getvalue()
        campaign_name = self.current_campaign.get("name", "export").replace(" ", "_")
        filename = f"{campaign_name}_all.csv"
        return rx.download(data=csv_str, filename=filename)

    # DELETE CAMPAIGN

    def toggle_delete_dialog(self):
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to delete campaigns.",
        ):
            return
        self.show_delete_dialog = not self.show_delete_dialog

    async def confirm_delete_campaign(self):
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to delete campaigns.",
        ):
            return
        cid = self.active_campaign_id
        if cid:
            campaign_name = self.current_campaign.get("name", "")
            await db_delete_campaign(cid)
            self.show_delete_dialog = False
            await self._log_admin_action(
                action="delete_campaign",
                summary=f"Deleted campaign '{campaign_name}'.",
                resource_type="campaign",
                resource_id=cid,
                resource_label=campaign_name,
            )
            return rx.redirect("/")

    # DELETE PARTICIPANT

    def open_delete_participant(self, event_id: str):
        """Open confirmation dialog for deleting a participant."""
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to delete participants.",
        ):
            return
        self.delete_participant_event_id = event_id
        for p in self.participants:
            if p.get("google_event_id") == event_id:
                self.delete_participant_name = p.get("name", "")
                break
        self.show_delete_participant_dialog = True

    def close_delete_participant(self):
        self.show_delete_participant_dialog = False
        self.delete_participant_event_id = ""
        self.delete_participant_name = ""

    async def confirm_delete_participant(self):
        """Delete a single participant after confirmation."""
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to delete participants.",
        ):
            return
        cid = self.active_campaign_id
        eid = self.delete_participant_event_id
        if cid and eid:
            participant_name = self.delete_participant_name
            await db_delete_participant(cid, eid)
            self.show_delete_participant_dialog = False
            self.delete_participant_event_id = ""
            self.delete_participant_name = ""
            await self._log_admin_action(
                action="delete_participant",
                summary=f"Deleted participant '{participant_name}'.",
                resource_type="participant",
                resource_id=eid,
                resource_label=participant_name,
                metadata={"campaign_id": cid},
            )
            await self._reload_participants()

    def open_bulk_delete(self):
        """Open confirmation dialog for bulk delete."""
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to bulk delete participants.",
        ):
            return
        if self.selected_ids:
            self.show_bulk_delete_dialog = True

    def close_bulk_delete(self):
        self.show_bulk_delete_dialog = False

    async def confirm_bulk_delete(self):
        """Delete all selected participants after confirmation."""
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to bulk delete participants.",
        ):
            return
        cid = self.active_campaign_id
        if cid and self.selected_ids:
            deleted_count = len(self.selected_ids)
            await db_bulk_delete(cid, list(self.selected_ids))
            self.selected_ids = []
            self.show_bulk_delete_dialog = False
            await self._log_admin_action(
                action="bulk_delete_participants",
                summary=f"Deleted {deleted_count} participant(s) from the campaign view.",
                resource_type="participant",
                metadata={"campaign_id": cid, "count": deleted_count},
            )
            await self._reload_participants()

    # CAMPAIGN FORM

    def set_form_name(self, v: str):
        self.form_name = v
        self.form_error = ""

    def set_form_description(self, v: str):
        self.form_description = v

    def set_form_booking_url(self, v: str):
        self.form_booking_url = v

    def set_form_goal(self, v: str):
        self.form_goal = v

    def set_form_calendar_id(self, v: str):
        self.form_calendar_id = v

    def set_form_calendar_filter(self, v: str):
        self.form_calendar_filter = v

    def set_form_notion_url(self, v: str):
        self.form_notion_url = v

    def set_form_linear_url(self, v: str):
        self.form_linear_url = v

    def set_form_deadline(self, v: str):
        self.form_deadline = v

    def set_form_device_type(self, v: str):
        """Toggle a platform in the selected device types list."""
        current = list(self.form_device_types)
        if v in current:
            current.remove(v)
        else:
            current.append(v)
        self.form_device_types = current

    def set_form_default_platform(self, v: str):
        # Convert sentinel "__none__" back to empty string
        self.form_default_platform = "" if v == "__none__" else v

    def set_form_default_model_tag(self, v: str):
        # Convert sentinel "__none__" back to empty string
        self.form_default_model_tag = "" if v == "__none__" else v

    def set_form_device_quota_value(self, key_value: str):
        """Set a single device quota entry. Format: 'device_name:quota_int'."""
        parts = key_value.split(":", 1)
        if len(parts) == 2:
            device = parts[0].strip()
            try:
                quota = max(0, int(parts[1].strip()))
            except (ValueError, TypeError):
                return
            new_quota = dict(self.form_device_quota)
            new_quota[device] = quota
            self.form_device_quota = new_quota

    def clear_form(self):
        self.form_name = ""
        self.form_description = ""
        self.form_booking_url = ""
        self.form_notion_url = ""
        self.form_linear_url = ""
        self.form_deadline = ""
        self.form_goal = "100"
        self.form_calendar_id = "primary"
        self.form_calendar_filter = ""
        self.form_error = ""
        self.form_is_edit = False
        self.form_edit_campaign_id = ""
        self.form_device_types = []
        self.form_device_quota = {}
        self.form_default_platform = ""
        self.form_default_model_tag = ""

    async def load_edit_campaign(self):
        cid = self.router.page.params.get("campaign_id", "")
        if not cid:
            return
        await self.load_settings()
        campaign = await get_campaign(cid)
        if not campaign:
            return rx.redirect("/")
        self.form_is_edit = True
        self.form_edit_campaign_id = cid
        self.form_name = campaign.get("name", "")
        self.form_description = campaign.get("description", "")
        self.form_booking_url = campaign.get("booking_url", "")
        self.form_notion_url = campaign.get("notion_url", "")
        self.form_linear_url = campaign.get("linear_url", "")
        self.form_deadline = campaign.get("deadline", "")
        self.form_goal = str(campaign.get("goal", 100))
        self.form_calendar_id = campaign.get("calendar_id", "primary")
        self.form_calendar_filter = campaign.get("calendar_filter", "")
        self.form_device_types = campaign.get("device_types", [])
        self.form_device_quota = campaign.get("device_quota", {})
        self.form_default_platform = campaign.get("default_platform", "")
        self.form_default_model_tag = campaign.get("default_model_tag", "")
        self.form_error = ""

    async def create_campaign(self):
        if not self._require_admin(
            target="form",
            message="Admin mode is required to create campaigns.",
        ):
            return
        if not self.form_name.strip():
            self.form_error = "Campaign name is required."
            return
        if not self.form_device_types:
            self.form_error = "At least one platform must be selected."
            return
        cid = await db_create_campaign({
            "name": self.form_name.strip(),
            "description": self.form_description.strip(),
            "booking_url": self.form_booking_url.strip(),
            "notion_url": self.form_notion_url.strip(),
            "linear_url": self.form_linear_url.strip(),
            "deadline": self.form_deadline.strip(),
            "goal": self.form_goal.strip() or "100",
            "calendar_id": self.form_calendar_id.strip() or "primary",
            "calendar_filter": self.form_calendar_filter.strip(),
            "device_types": list(self.form_device_types),
            "device_quota": dict(self.form_device_quota),
            "default_platform": self.form_default_platform,
            "default_model_tag": self.form_default_model_tag,
        })
        await self._log_admin_action(
            action="create_campaign",
            summary=f"Created campaign '{self.form_name.strip()}'.",
            resource_type="campaign",
            resource_id=cid,
            resource_label=self.form_name.strip(),
        )
        self.clear_form()
        return rx.redirect(f"/campaign/{cid}")

    async def save_campaign(self):
        if not self._require_admin(
            target="form",
            message="Admin mode is required to edit campaigns.",
        ):
            return
        if not self.form_name.strip():
            self.form_error = "Campaign name is required."
            return
        if not self.form_device_types:
            self.form_error = "At least one platform must be selected."
            return
        cid = self.form_edit_campaign_id
        if not cid:
            return
        await db_update_campaign(cid, {
            "name": self.form_name.strip(),
            "description": self.form_description.strip(),
            "booking_url": self.form_booking_url.strip(),
            "notion_url": self.form_notion_url.strip(),
            "linear_url": self.form_linear_url.strip(),
            "deadline": self.form_deadline.strip(),
            "goal": self.form_goal.strip() or "100",
            "calendar_id": self.form_calendar_id.strip() or "primary",
            "calendar_filter": self.form_calendar_filter.strip(),
            "device_types": list(self.form_device_types),
            "device_quota": dict(self.form_device_quota),
            "default_platform": self.form_default_platform,
            "default_model_tag": self.form_default_model_tag,
        })
        await self._log_admin_action(
            action="update_campaign",
            summary=f"Updated campaign '{self.form_name.strip()}'.",
            resource_type="campaign",
            resource_id=cid,
            resource_label=self.form_name.strip(),
        )
        self.clear_form()
        return rx.redirect(f"/campaign/{cid}")

    # CAMPAIGN CLONING

    async def clone_current_campaign(self):
        if not self._require_admin(
            target="detail",
            message="Admin mode is required to clone campaigns.",
        ):
            return
        cid = self.active_campaign_id
        if cid:
            new_cid = await db_clone_campaign(cid)
            if new_cid:
                source_name = self.current_campaign.get("name", "")
                await self._log_admin_action(
                    action="clone_campaign",
                    summary=f"Cloned campaign '{source_name}'.",
                    resource_type="campaign",
                    resource_id=new_cid,
                    resource_label=source_name,
                    metadata={"source_campaign_id": cid},
                )
                return rx.redirect(f"/campaign/{new_cid}/edit")
