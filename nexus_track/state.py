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

from .backend.gcal_sync import list_calendars, sync_calendar_for_campaign
from .backend.mongo_client import (
    add_manual_participant,
    archive_campaign as db_archive_campaign,
    bulk_update_participant_field as db_bulk_update,
    create_campaign as db_create_campaign,
    delete_campaign as db_delete_campaign,
    ensure_indexes,
    get_all_campaigns_with_stats,
    get_campaign,
    get_participants_for_campaign,
    get_participants_for_export,
    get_settings,
    unarchive_campaign as db_unarchive_campaign,
    update_campaign as db_update_campaign,
    update_campaign_field as db_update_campaign_field,
    update_label_list,
    update_participant_field as db_update_field,
    update_participant_status as db_update_status,
)

log = logging.getLogger(__name__)

_auto_refresh_running = False


class NexusState(rx.State):
    """Single state class for the entire multi-page app."""

    # SETTINGS / LABELS
    platforms: list[str] = ["Orb", "Kiosk-v1", "Kiosk-v2", "Self-Serve", "Other"]
    model_tags: list[str] = ["v4.5", "v4.6", "v5.0", "beta"]
    statuses: list[str] = ["Pending", "In-Progress", "Completed"]

    new_platform: str = ""
    new_model_tag: str = ""
    new_status_label: str = ""

    available_calendars: list[dict] = []
    calendars_loading: bool = False

    # LOADING STATE
    is_loading: bool = False

    # DASHBOARD
    campaigns: list[dict] = []
    campaign_search_query: str = ""
    show_archived: bool = False

    # DATE NAVIGATION
    selected_date: str = ""

    # CAMPAIGN DETAIL
    current_campaign: dict = {}
    active_campaign_id: str = ""
    participants: list[dict] = []
    search_query: str = ""

    # SORTING
    sort_field: str = "appointment_time"
    sort_dir: str = "asc"

    # BULK SELECTION
    selected_ids: list[str] = []

    # MANUAL ADD PARTICIPANT
    show_add_participant: bool = False
    add_name: str = ""
    add_email: str = ""
    add_time: str = ""

    # SYNC
    is_syncing: bool = False
    last_sync_time: str = ""
    sync_error: str = ""

    # CAMPAIGN FORM
    form_name: str = ""
    form_description: str = ""
    form_notion_url: str = ""
    form_linear_url: str = ""
    form_booking_url: str = ""
    form_calendar_id: str = "primary"
    form_calendar_filter: str = ""
    form_error: str = ""
    form_is_edit: bool = False
    form_edit_campaign_id: str = ""

    # DELETE CONFIRMATION
    show_delete_dialog: bool = False

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
    def in_progress_count(self) -> int:
        return sum(1 for p in self.participants if p.get("status") == "In-Progress")

    @rx.var(cache=True)
    def pending_count(self) -> int:
        return sum(1 for p in self.participants if p.get("status") == "Pending")

    @rx.var(cache=True)
    def progress_pct(self) -> int:
        t = self.total_count
        return int(self.completed_count / t * 100) if t else 0

    @rx.var(cache=True)
    def sorted_filtered_participants(self) -> list[dict]:
        items = self.participants
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
    def selection_count(self) -> int:
        return len(self.selected_ids)

    @rx.var(cache=True)
    def all_selected(self) -> bool:
        if not self.participants:
            return False
        return len(self.selected_ids) >= len(self.participants)

    @rx.var(cache=True)
    def campaign_name(self) -> str:
        return self.current_campaign.get("name", "")

    @rx.var(cache=True)
    def campaign_description(self) -> str:
        return self.current_campaign.get("description", "")

    @rx.var(cache=True)
    def campaign_notion_url(self) -> str:
        return self.current_campaign.get("notion_url", "")

    @rx.var(cache=True)
    def campaign_linear_url(self) -> str:
        return self.current_campaign.get("linear_url", "")

    @rx.var(cache=True)
    def campaign_booking_url(self) -> str:
        return self.current_campaign.get("booking_url", "")

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
        if not self.campaign_search_query:
            return self.campaigns
        q = self.campaign_search_query.lower()
        return [
            c for c in self.campaigns
            if q in c.get("name", "").lower()
            or q in c.get("description", "").lower()
        ]

    @rx.var(cache=True)
    def display_date_label(self) -> str:
        d = self.selected_date
        if not d:
            return datetime.now().strftime("%A, %B %d")
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            today = datetime.now().date()
            if dt.date() == today:
                return dt.strftime("%A, %B %d") + "  \u00b7  Today"
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

    async def load_settings(self):
        doc = await get_settings()
        self.platforms = doc.get("platforms", self.platforms)
        self.model_tags = doc.get("model_tags", self.model_tags)
        self.statuses = doc.get("statuses", self.statuses)

    def set_new_platform(self, v: str):
        self.new_platform = v

    async def add_platform(self):
        v = self.new_platform.strip()
        if v and v not in self.platforms:
            self.platforms.append(v)
            await update_label_list("platforms", self.platforms)
        self.new_platform = ""

    async def remove_platform(self, label: str):
        self.platforms = [p for p in self.platforms if p != label]
        await update_label_list("platforms", self.platforms)

    def set_new_model_tag(self, v: str):
        self.new_model_tag = v

    async def add_model_tag(self):
        v = self.new_model_tag.strip()
        if v and v not in self.model_tags:
            self.model_tags.append(v)
            await update_label_list("model_tags", self.model_tags)
        self.new_model_tag = ""

    async def remove_model_tag(self, label: str):
        self.model_tags = [t for t in self.model_tags if t != label]
        await update_label_list("model_tags", self.model_tags)

    def set_new_status_label(self, v: str):
        self.new_status_label = v

    async def add_status_label(self):
        v = self.new_status_label.strip()
        if v and v not in self.statuses:
            self.statuses.append(v)
            await update_label_list("statuses", self.statuses)
        self.new_status_label = ""

    async def remove_status_label(self, label: str):
        self.statuses = [s for s in self.statuses if s != label]
        await update_label_list("statuses", self.statuses)

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
            date = self._get_date()
            self.participants = await get_participants_for_campaign(cid, date)
            self.selected_ids = []

    async def navigate_prev_day(self):
        self.go_prev_day()
        await self._reload_participants()

    async def navigate_next_day(self):
        self.go_next_day()
        await self._reload_participants()

    async def navigate_to_today(self):
        self.go_to_today()
        await self._reload_participants()

    # DASHBOARD

    async def load_campaigns(self):
        self.is_loading = True
        await ensure_indexes()
        await self.load_settings()
        date = self._get_date()
        self.campaigns = await get_all_campaigns_with_stats(
            date, include_archived=self.show_archived,
        )
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
        self.last_sync_time = ""
        self.show_delete_dialog = False
        self.selected_ids = []
        self.sort_field = "appointment_time"
        self.sort_dir = "asc"
        if not self.selected_date:
            self.selected_date = datetime.now().strftime("%Y-%m-%d")
        if cid:
            await self.load_settings()
            campaign = await get_campaign(cid)
            if campaign:
                self.current_campaign = campaign
                date = self._get_date()
                self.participants = await get_participants_for_campaign(cid, date)
            else:
                self.current_campaign = {}
                self.participants = []
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

    def select_all(self):
        if self.all_selected:
            self.selected_ids = []
        else:
            self.selected_ids = [
                p.get("google_event_id", "") for p in self.participants
            ]

    async def bulk_set_status(self, new_status: str):
        cid = self.active_campaign_id
        if cid and self.selected_ids:
            await db_bulk_update(cid, list(self.selected_ids), "status", new_status)
            self.selected_ids = []
            await self._reload_participants()

    async def bulk_set_platform(self, platform: str):
        cid = self.active_campaign_id
        if cid and self.selected_ids:
            await db_bulk_update(cid, list(self.selected_ids), "platform", platform)
            self.selected_ids = []
            await self._reload_participants()

    async def bulk_set_model(self, model_tag: str):
        cid = self.active_campaign_id
        if cid and self.selected_ids:
            await db_bulk_update(cid, list(self.selected_ids), "model_tag", model_tag)
            self.selected_ids = []
            await self._reload_participants()

    def clear_selection(self):
        self.selected_ids = []

    # CAMPAIGN STATUS TOGGLE

    async def toggle_campaign_status(self):
        cid = self.active_campaign_id
        if not cid:
            return
        cur = self.current_campaign.get("status", "active")
        new_status = "paused" if cur == "active" else "active"
        await db_update_campaign_field(cid, "status", new_status)
        campaign = await get_campaign(cid)
        if campaign:
            self.current_campaign = campaign

    # ARCHIVE CAMPAIGN

    async def archive_campaign(self):
        cid = self.active_campaign_id
        if cid:
            await db_archive_campaign(cid)
            return rx.redirect("/")

    async def unarchive_campaign(self):
        cid = self.active_campaign_id
        if cid:
            await db_unarchive_campaign(cid)
            campaign = await get_campaign(cid)
            if campaign:
                self.current_campaign = campaign

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
            fresh = await get_participants_for_campaign(cid, date)
            async with self:
                self.participants = fresh
                self.last_sync_time = datetime.now().strftime("%H:%M:%S")
                self.is_syncing = False
        except Exception as exc:
            log.exception("Calendar sync failed")
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
                async with self:
                    self.campaigns = fresh_campaigns
                if cid:
                    fresh = await get_participants_for_campaign(cid, date)
                    async with self:
                        self.participants = fresh
            except Exception:
                pass

    # PARTICIPANT MUTATIONS

    async def set_platform(self, event_id: str, platform: str):
        cid = self.active_campaign_id
        if cid:
            await db_update_field(cid, event_id, "platform", platform)
            await self._reload_participants()

    async def set_model_tag(self, event_id: str, model_tag: str):
        cid = self.active_campaign_id
        if cid:
            await db_update_field(cid, event_id, "model_tag", model_tag)
            await self._reload_participants()

    async def set_status(self, event_id: str, new_status: str):
        cid = self.active_campaign_id
        if cid:
            await db_update_status(cid, event_id, new_status)
            await self._reload_participants()

    async def set_notes(self, event_id: str, notes: str):
        cid = self.active_campaign_id
        if cid:
            await db_update_field(cid, event_id, "notes", notes)
            self.participants = [
                {**p, "notes": notes} if p.get("google_event_id") == event_id else p
                for p in self.participants
            ]

    def set_search(self, query: str):
        self.search_query = query

    # MANUAL PARTICIPANT ADD

    def toggle_add_participant(self):
        self.show_add_participant = not self.show_add_participant
        self.add_name = ""
        self.add_email = ""
        self.add_time = ""

    def set_add_name(self, v: str):
        self.add_name = v

    def set_add_email(self, v: str):
        self.add_email = v

    def set_add_time(self, v: str):
        self.add_time = v

    async def submit_add_participant(self):
        name = self.add_name.strip()
        if not name:
            return
        cid = self.active_campaign_id
        date = self._get_date()
        await add_manual_participant(
            campaign_id=cid,
            name=name,
            email=self.add_email.strip(),
            appointment_date=date,
            appointment_time=self.add_time.strip(),
        )
        self.show_add_participant = False
        self.add_name = ""
        self.add_email = ""
        self.add_time = ""
        await self._reload_participants()

    # CSV EXPORT

    async def export_csv(self):
        cid = self.active_campaign_id
        if not cid:
            return
        date = self._get_date()
        rows = await get_participants_for_export(cid, date)
        if not rows:
            return
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["name", "email", "date", "time", "platform", "model_tag", "status", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)
        csv_str = buf.getvalue()
        campaign_name = self.current_campaign.get("name", "export").replace(" ", "_")
        filename = f"{campaign_name}_{date}.csv"
        return rx.download(data=csv_str, filename=filename)

    # DELETE CAMPAIGN

    def toggle_delete_dialog(self):
        self.show_delete_dialog = not self.show_delete_dialog

    async def confirm_delete_campaign(self):
        cid = self.active_campaign_id
        if cid:
            await db_delete_campaign(cid)
            self.show_delete_dialog = False
            return rx.redirect("/")

    # CAMPAIGN FORM

    def set_form_name(self, v: str):
        self.form_name = v
        self.form_error = ""

    def set_form_description(self, v: str):
        self.form_description = v

    def set_form_notion_url(self, v: str):
        self.form_notion_url = v

    def set_form_linear_url(self, v: str):
        self.form_linear_url = v

    def set_form_booking_url(self, v: str):
        self.form_booking_url = v

    def set_form_calendar_id(self, v: str):
        self.form_calendar_id = v

    def set_form_calendar_filter(self, v: str):
        self.form_calendar_filter = v

    def clear_form(self):
        self.form_name = ""
        self.form_description = ""
        self.form_notion_url = ""
        self.form_linear_url = ""
        self.form_booking_url = ""
        self.form_calendar_id = "primary"
        self.form_calendar_filter = ""
        self.form_error = ""
        self.form_is_edit = False
        self.form_edit_campaign_id = ""

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
        self.form_notion_url = campaign.get("notion_url", "")
        self.form_linear_url = campaign.get("linear_url", "")
        self.form_booking_url = campaign.get("booking_url", "")
        self.form_calendar_id = campaign.get("calendar_id", "primary")
        self.form_calendar_filter = campaign.get("calendar_filter", "")
        self.form_error = ""

    async def create_campaign(self):
        if not self.form_name.strip():
            self.form_error = "Campaign name is required."
            return
        cid = await db_create_campaign({
            "name": self.form_name.strip(),
            "description": self.form_description.strip(),
            "notion_url": self.form_notion_url.strip(),
            "linear_url": self.form_linear_url.strip(),
            "booking_url": self.form_booking_url.strip(),
            "calendar_id": self.form_calendar_id.strip() or "primary",
            "calendar_filter": self.form_calendar_filter.strip(),
        })
        self.clear_form()
        return rx.redirect(f"/campaign/{cid}")

    async def save_campaign(self):
        if not self.form_name.strip():
            self.form_error = "Campaign name is required."
            return
        cid = self.form_edit_campaign_id
        if not cid:
            return
        await db_update_campaign(cid, {
            "name": self.form_name.strip(),
            "description": self.form_description.strip(),
            "notion_url": self.form_notion_url.strip(),
            "linear_url": self.form_linear_url.strip(),
            "booking_url": self.form_booking_url.strip(),
            "calendar_id": self.form_calendar_id.strip() or "primary",
            "calendar_filter": self.form_calendar_filter.strip(),
        })
        self.clear_form()
        return rx.redirect(f"/campaign/{cid}")
