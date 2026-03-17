"""Campaign detail page - participants, date nav, sync, bulk actions, CSV export."""

import reflex as rx

from ..components.participant_row import participant_row
from ..components.design_tokens import (
    ACCENT,
    ACCENT_DARK,
    ACCENT_GRADIENT,
    ACCENT_GRADIENT_H,
    ACCENT_LIGHT,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
    BG,
    BLUE,
    BLUE_SOFT,
    BORDER,
    BORDER_ACCENT,
    BORDER_SUBTLE,
    CARD_BG,
    CARD_BG_SOLID,
    GREEN,
    GREEN_SOFT,
    HEADING,
    MAX_WIDTH,
    MUTED,
    PAGE_PADDING_BOTTOM,
    PAGE_PADDING_X,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    RED,
    RED_SOFT,
    SHADOW_ACCENT,
    SHADOW_MD,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    TRANSITION,
    TRANSITION_FAST,
    VIOLET,
    glass_card,
    ghost_icon_btn,
    dual_progress_bar,
    section_header,
    status_dot,
)
from ..state import NexusState


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _stat_pill(label: str, value: rx.Var, color: str, bg) -> rx.Component:
    return rx.hstack(
        rx.box(
            width="8px", height="8px",
            border_radius="50%",
            background=color,
        ),
        rx.text(
            value.to(str),
            size="3",
            weight="bold",
            color=HEADING,
        ),
        rx.text(
            label,
            size="2",
            color=TEXT,
        ),
        spacing="2",
        align="center",
        padding_x="14px",
        padding_y="8px",
        border_radius=RADIUS_MD,
        background=bg,
    )




# -----------------------------------------------------------------------
# Campaign header card
# -----------------------------------------------------------------------

def _campaign_header() -> rx.Component:
    return glass_card(
        # ── 3-zone upper row: left | center badge | right goal card ──
        rx.flex(
            # LEFT: title, description, docs/links/booking
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        NexusState.campaign_name,
                        size="6",
                        weight="bold",
                        color=HEADING,
                    ),
                    spacing="3",
                    align="center",
                ),
                rx.cond(
                    NexusState.campaign_description != "",
                    rx.text(
                        NexusState.campaign_description,
                        size="2",
                        color=TEXT,
                        line_height="1.5",
                    ),
                ),
                # Links row: Docs, Links, Booking
                rx.hstack(
                    rx.cond(
                        NexusState.campaign_notion_url != "",
                        rx.link(
                            rx.hstack(
                                rx.icon("book-open", size=13),
                                rx.text("Docs", size="2", weight="medium"),
                                spacing="1",
                                align="center",
                                color=ACCENT,
                            ),
                            href=NexusState.campaign_notion_url,
                            is_external=True,
                            padding_x="10px",
                            padding_y="5px",
                            border_radius=RADIUS_SM,
                            background=ACCENT_SOFT,
                            _hover={"opacity": "0.8"},
                        ),
                    ),
                    rx.cond(
                        NexusState.campaign_linear_url != "",
                        rx.link(
                            rx.hstack(
                                rx.icon("layers", size=13),
                                rx.text("Links", size="2", weight="medium"),
                                spacing="1",
                                align="center",
                                color=SUBTEXT,
                            ),
                            href=NexusState.campaign_linear_url,
                            is_external=True,
                            padding_x="10px",
                            padding_y="5px",
                            border_radius=RADIUS_SM,
                            background=ACCENT_SOFT,
                            _hover={"opacity": "0.8"},
                        ),
                    ),
                    rx.cond(
                        NexusState.campaign_booking_url != "",
                        rx.link(
                            rx.hstack(
                                rx.icon("calendar-check", size=13),
                                rx.text("Booking", size="2", weight="medium"),
                                spacing="1",
                                align="center",
                                color=ACCENT,
                            ),
                            href=NexusState.campaign_booking_url,
                            is_external=True,
                            padding_x="10px",
                            padding_y="5px",
                            border_radius=RADIUS_SM,
                            background=ACCENT_SOFT,
                            _hover={"opacity": "0.8"},
                        ),
                    ),
                    spacing="2",
                    flex_wrap="wrap",
                    margin_top="4px",
                ),
                spacing="2",
                flex="1",
                min_width="0",
            ),
            # CENTER: campaign status badge
            rx.vstack(
                rx.cond(
                    NexusState.campaign_status == "active",
                    rx.badge("Active", color_scheme="green", size="2",
                             variant="soft", cursor="pointer",
                             on_click=NexusState.toggle_campaign_status),
                    rx.cond(
                        NexusState.campaign_status == "archived",
                        rx.badge("Archived", color_scheme="gray", size="2",
                                 variant="soft"),
                        rx.badge("Paused", color_scheme="orange", size="2",
                                 variant="soft", cursor="pointer",
                                 on_click=NexusState.toggle_campaign_status),
                    ),
                ),
                # Meta pills: filter, created, last sync
                rx.hstack(
                    rx.cond(
                        NexusState.campaign_calendar_filter != "",
                        rx.hstack(
                            rx.icon("filter", size=11, color=ACCENT),
                            rx.text(NexusState.campaign_calendar_filter, size="1"),
                            spacing="1", align="center",
                        ),
                    ),
                    rx.cond(
                        NexusState.campaign_last_sync != "",
                        rx.hstack(
                            rx.icon("refresh-cw", size=11, color=SUBTEXT),
                            rx.text(NexusState.campaign_last_sync, size="1", color=SUBTEXT),
                            spacing="1", align="center",
                        ),
                    ),
                    spacing="2",
                    flex_wrap="wrap",
                ),
                spacing="2",
                align="center",
                flex_shrink="0",
                padding_x="16px",
            ),
            # RIGHT: goal/deadline card + action buttons
            rx.vstack(
                # Goal / Deadline card
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("target", size=14, color=ACCENT),
                            rx.text(
                                "Goal: ",
                                rx.text(
                                    NexusState.campaign_goal.to(str),
                                    weight="bold",
                                    as_="span",
                                ),
                                size="2",
                                color=HEADING,
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.cond(
                            NexusState.campaign_deadline != "",
                            rx.hstack(
                                rx.icon("calendar-clock", size=14, color=AMBER),
                                rx.text(
                                    "Due " + NexusState.campaign_deadline,
                                    size="2",
                                    color=AMBER,
                                    weight="medium",
                                ),
                                spacing="2",
                                align="center",
                            ),
                        ),
                        spacing="2",
                    ),
                    padding="12px 16px",
                    border_radius=RADIUS_MD,
                    background=CARD_BG,
                    border=BORDER,
                    min_width="160px",
                ),
                # Action buttons
                rx.hstack(
                    rx.cond(
                        NexusState.campaign_status == "archived",
                        rx.icon_button(
                            rx.icon("archive-restore", size=16),
                            size="2",
                            variant="soft",
                            color_scheme="green",
                            border_radius=RADIUS_MD,
                            on_click=NexusState.unarchive_campaign,
                            cursor="pointer",
                            title="Unarchive",
                        ),
                        rx.icon_button(
                            rx.icon("archive", size=16),
                            size="2",
                            variant="soft",
                            color_scheme="gray",
                            border_radius=RADIUS_MD,
                            on_click=NexusState.archive_campaign,
                            cursor="pointer",
                            title="Archive",
                        ),
                    ),
                    rx.link(
                        rx.icon_button(
                            rx.icon("pencil", size=16),
                            size="2",
                            variant="soft",
                            color_scheme="iris",
                            border_radius=RADIUS_MD,
                            cursor="pointer",
                        ),
                        href="/campaign/" + NexusState.active_campaign_id + "/edit",
                    ),
                    rx.icon_button(
                        rx.icon("copy", size=16),
                        size="2",
                        variant="soft",
                        color_scheme="blue",
                        border_radius=RADIUS_MD,
                        on_click=NexusState.clone_current_campaign,
                        cursor="pointer",
                        title="Clone Campaign",
                    ),
                    rx.icon_button(
                        rx.icon("trash-2", size=16),
                        size="2",
                        variant="soft",
                        color_scheme="red",
                        border_radius=RADIUS_MD,
                        on_click=NexusState.toggle_delete_dialog,
                        cursor="pointer",
                    ),
                    spacing="2",
                    margin_top="8px",
                ),
                spacing="2",
                align="end",
                flex_shrink="0",
            ),
            direction=rx.breakpoints(initial="column", md="row"),
            justify="between",
            align=rx.breakpoints(initial="start", md="start"),
            gap="4",
            width="100%",
        ),
        # ── Progress bar directly under header content ──
        rx.box(
            rx.hstack(
                rx.hstack(
                    rx.text(
                        NexusState.campaign_completed_all.to(str) + " completed",
                        size="1", weight="medium", color=GREEN,
                    ),
                    rx.text("·", size="1", color=MUTED),
                    rx.text(
                        NexusState.campaign_booked.to(str) + " booked",
                        size="1", weight="medium", color=ACCENT,
                    ),
                    rx.text("·", size="1", color=MUTED),
                    rx.text(
                        "Goal: " + NexusState.campaign_goal.to(str),
                        size="1", weight="medium", color=SUBTEXT,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.text(
                    NexusState.completed_pct.to(str) + "%",
                    size="2", weight="bold",
                    background=ACCENT_GRADIENT,
                    background_clip="text",
                    color="transparent",
                ),
                width="100%",
                align="center",
            ),
            rx.box(height="6px"),
            dual_progress_bar(
                NexusState.booked_pct,
                NexusState.completed_pct,
                height="12px",
            ),
            margin_top="16px",
            padding_top="16px",
            border_top=BORDER_SUBTLE,
            width="100%",
        ),
        margin_bottom="16px",
    )


# -----------------------------------------------------------------------
# Stats + progress bar
# -----------------------------------------------------------------------

def _stats_and_progress() -> rx.Component:
    return rx.vstack(
        # Stat pills
        rx.hstack(
            _stat_pill("Booked", NexusState.booked_count, AMBER, AMBER_SOFT),
            _stat_pill("Done", NexusState.completed_count, GREEN, GREEN_SOFT),
            rx.spacer(),
            rx.text(
                NexusState.total_count.to(str) + " total",
                size="2",
                weight="medium",
                color=SUBTEXT,
            ),
            spacing="3",
            align="center",
            width="100%",
            flex_wrap="wrap",
        ),
        spacing="3",
        width="100%",
        margin_bottom="16px",
    )


# -----------------------------------------------------------------------
# Participant filter bar
# -----------------------------------------------------------------------

def _filter_chip(label: str, is_active, on_click) -> rx.Component:
    return rx.box(
        rx.text(label, size="1", weight="medium",
                color=rx.cond(is_active, "white", SUBTEXT)),
        padding_x="10px",
        padding_y="4px",
        border_radius=RADIUS_SM,
        background=rx.cond(is_active, ACCENT, "transparent"),
        border=rx.cond(is_active, "1px solid transparent", BORDER_SUBTLE),
        cursor="pointer",
        transition=TRANSITION_FAST,
        on_click=on_click,
        _hover={"opacity": "0.8"},
    )


def _participant_filter_bar() -> rx.Component:
    return glass_card(
        rx.hstack(
            # Status chips
            rx.text("Status:", size="1", weight="medium", color=SUBTEXT),
            _filter_chip("All", NexusState.filter_status == "", NexusState.set_filter_status("")),
            _filter_chip("Booked", NexusState.filter_status == "Booked", NexusState.set_filter_status("Booked")),
            _filter_chip("Completed", NexusState.filter_status == "Completed", NexusState.set_filter_status("Completed")),
            rx.box(width="1px", height="20px", background=BORDER_SUBTLE),
            # Platform filter
            rx.select(
                NexusState.platforms,
                value=NexusState.filter_platform,
                on_change=NexusState.set_filter_platform,
                placeholder="Platform",
                size="1",
                variant="soft",
            ),
            # Date filter
            rx.select(
                NexusState.participant_dates,
                value=NexusState.filter_date,
                on_change=NexusState.set_filter_date,
                placeholder="Date",
                size="1",
                variant="soft",
            ),
            # Issues toggle
            _filter_chip(
                "Issues only",
                NexusState.filter_has_issue,
                NexusState.toggle_filter_has_issue(),
            ),
            rx.spacer(),
            # Active filter badge + clear
            rx.cond(
                NexusState.active_filter_count > 0,
                rx.hstack(
                    rx.badge(
                        NexusState.active_filter_count.to(str) + " filters",
                        color_scheme="iris",
                        size="1",
                        variant="soft",
                    ),
                    rx.button(
                        "Clear",
                        size="1",
                        variant="ghost",
                        color_scheme="gray",
                        on_click=NexusState.clear_all_filters,
                        cursor="pointer",
                    ),
                    spacing="2",
                    align="center",
                ),
            ),
            spacing="2",
            align="center",
            width="100%",
            flex_wrap="wrap",
        ),
        padding="10px 16px",
        margin_bottom="12px",
    )


# -----------------------------------------------------------------------
# Sync bar + search + CSV export + Add participant
# -----------------------------------------------------------------------

def _range_sync_panel() -> rx.Component:
    """Date-range sync UI - sync multiple days at once."""
    return glass_card(
        rx.hstack(
            rx.icon("calendar-range", size=16, color=ACCENT),
            rx.text("Range Sync", size="2", weight="bold", color=HEADING),
            rx.spacer(),
            rx.cond(
                NexusState.range_sync_result != "",
                rx.badge(
                    NexusState.range_sync_result,
                    color_scheme="green",
                    size="1",
                    variant="soft",
                ),
            ),
            width="100%",
            align="center",
        ),
        rx.hstack(
            rx.vstack(
                rx.text("Start", size="1", color=SUBTEXT),
                rx.el.input(
                    type="date",
                    default_value=NexusState.sync_start_date,
                    on_change=NexusState.set_sync_start_date,
                    style={
                        "padding": "6px 10px",
                        "border_radius": RADIUS_SM,
                        "border": BORDER,
                        "background": CARD_BG,
                        "color": TEXT,
                        "font_size": "13px",
                    },
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("End", size="1", color=SUBTEXT),
                rx.el.input(
                    type="date",
                    default_value=NexusState.sync_end_date,
                    on_change=NexusState.set_sync_end_date,
                    style={
                        "padding": "6px 10px",
                        "border_radius": RADIUS_SM,
                        "border": BORDER,
                        "background": CARD_BG,
                        "color": TEXT,
                        "font_size": "13px",
                    },
                ),
                spacing="1",
            ),
            rx.button(
                rx.cond(
                    NexusState.is_syncing,
                    rx.spinner(size="1"),
                    rx.icon("refresh-cw", size=14),
                ),
                "Sync Range",
                size="2",
                variant="solid",
                color_scheme="iris",
                border_radius=RADIUS_MD,
                on_click=NexusState.sync_campaign_range,
                loading=NexusState.is_syncing,
                cursor="pointer",
                align_self="end",
            ),
            spacing="3",
            align="end",
            margin_top="8px",
        ),
        margin_bottom="12px",
        padding="14px 18px",
    )


def _issue_editor_dialog() -> rx.Component:
    """Modal dialog for editing a participant's issue comment."""
    return rx.cond(
        NexusState.editing_issue_event_id != "",
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Edit Issue Comment"),
                rx.dialog.description(
                    "Describe the issue with this participant. "
                    "Leave blank and save to clear the issue flag.",
                ),
                rx.text_area(
                    value=NexusState.editing_issue_comment,
                    on_change=NexusState.set_editing_issue_comment,
                    placeholder="e.g. Participant arrived late, device malfunction...",
                    width="100%",
                    min_height="100px",
                    margin_top="12px",
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                            on_click=NexusState.close_issue_editor,
                            cursor="pointer",
                        ),
                    ),
                    rx.button(
                        "Save",
                        color_scheme="iris",
                        on_click=NexusState.save_issue_comment,
                        cursor="pointer",
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                    margin_top="16px",
                ),
            ),
            open=NexusState.editing_issue_event_id != "",
        ),
        rx.fragment(),
    )


def _sync_bar() -> rx.Component:
    return rx.hstack(
        # Sync today button
        rx.button(
            rx.cond(
                NexusState.is_syncing,
                rx.spinner(size="1"),
                rx.icon("refresh-cw", size=14),
            ),
            "Sync Today",
            size="2",
            variant="soft",
            color_scheme="iris",
            border_radius=RADIUS_MD,
            on_click=NexusState.sync_campaign_calendar,
            loading=NexusState.is_syncing,
            cursor="pointer",
        ),
        rx.cond(
            NexusState.last_sync_time != "",
            rx.text(
                "Synced " + NexusState.last_sync_time,
                size="1",
                color=SUBTEXT,
            ),
        ),
        rx.spacer(),
        # CSV export
        rx.button(
            rx.icon("download", size=14),
            "Export CSV",
            size="1",
            variant="soft",
            color_scheme="gray",
            border_radius=RADIUS_SM,
            on_click=NexusState.export_csv,
            cursor="pointer",
        ),
        # Add participant
        rx.button(
            rx.icon("user-plus", size=14),
            "Add",
            size="1",
            variant="soft",
            color_scheme="iris",
            border_radius=RADIUS_SM,
            on_click=NexusState.toggle_add_participant,
            cursor="pointer",
        ),
        # Search
        rx.box(
            rx.hstack(
                rx.icon("search", size=14, color=SUBTEXT),
                rx.input(
                    placeholder="Search participants...",
                    value=NexusState.search_query,
                    on_change=NexusState.set_search,
                    variant="surface",
                    size="2",
                    border_radius=RADIUS_MD,
                    width="200px",
                ),
                spacing="2",
                align="center",
            ),
        ),
        spacing="3",
        align="center",
        width="100%",
        flex_wrap="wrap",
        margin_bottom="8px",
    )


# -----------------------------------------------------------------------
# Bulk action bar (appears when items selected)
# -----------------------------------------------------------------------

def _bulk_action_bar() -> rx.Component:
    return rx.cond(
        NexusState.selection_count > 0,
        glass_card(
            rx.hstack(
                rx.hstack(
                    rx.checkbox(
                        checked=NexusState.all_selected,
                        on_change=lambda _v: NexusState.select_all(),
                        size="2",
                        color_scheme="iris",
                        cursor="pointer",
                    ),
                    rx.text(
                        NexusState.selection_count.to(str) + " selected",
                        size="2",
                        weight="bold",
                        color=ACCENT,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                # Bulk status change
                rx.button(
                    "Mark Completed",
                    size="1",
                    variant="soft",
                    color_scheme="green",
                    border_radius=RADIUS_SM,
                    on_click=NexusState.bulk_set_status("Completed"),
                    cursor="pointer",
                ),
                rx.button(
                    "Mark Booked",
                    size="1",
                    variant="soft",
                    color_scheme="amber",
                    border_radius=RADIUS_SM,
                    on_click=NexusState.bulk_set_status("Booked"),
                    cursor="pointer",
                ),
                rx.button(
                    rx.icon("trash-2", size=12),
                    "Delete",
                    size="1",
                    variant="soft",
                    color_scheme="red",
                    border_radius=RADIUS_SM,
                    on_click=NexusState.open_bulk_delete,
                    cursor="pointer",
                ),
                rx.button(
                    "Clear",
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                    border_radius=RADIUS_SM,
                    on_click=NexusState.clear_selection,
                    cursor="pointer",
                ),
                spacing="2",
                align="center",
            ),
            padding="12px 20px",
            border=BORDER_ACCENT,
            margin_bottom="12px",
        ),
        rx.fragment(),
    )


# -----------------------------------------------------------------------
# Add participant dialog
# -----------------------------------------------------------------------

def _add_participant_dialog() -> rx.Component:
    return rx.cond(
        NexusState.show_add_participant,
        glass_card(
            rx.hstack(
                rx.icon("user-plus", size=18, color=ACCENT),
                rx.text("Add Participant Manually", size="3", weight="bold", color=HEADING),
                rx.spacer(),
                rx.icon_button(
                    rx.icon("x", size=14),
                    size="1",
                    variant="ghost",
                    on_click=NexusState.toggle_add_participant,
                    cursor="pointer",
                ),
                width="100%",
                align="center",
            ),
            rx.grid(
                rx.vstack(
                    rx.text("Name *", size="2", weight="medium", color=SUBTEXT),
                    rx.input(
                        value=NexusState.add_name,
                        on_change=NexusState.set_add_name,
                        placeholder="Jane Doe",
                        size="2",
                        variant="surface",
                        border_radius=RADIUS_SM,
                        width="100%",
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Email", size="2", weight="medium", color=SUBTEXT),
                    rx.input(
                        value=NexusState.add_email,
                        on_change=NexusState.set_add_email,
                        placeholder="jane@example.com",
                        size="2",
                        variant="surface",
                        border_radius=RADIUS_SM,
                        width="100%",
                    ),
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Time", size="2", weight="medium", color=SUBTEXT),
                    rx.input(
                        value=NexusState.add_time,
                        on_change=NexusState.set_add_time,
                        placeholder="14:30",
                        size="2",
                        variant="surface",
                        border_radius=RADIUS_SM,
                        width="100%",
                    ),
                    spacing="1",
                ),
                columns="3",
                spacing="3",
                width="100%",
                margin_top="12px",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    "Cancel",
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                    border_radius=RADIUS_SM,
                    on_click=NexusState.toggle_add_participant,
                    cursor="pointer",
                ),
                rx.button(
                    rx.icon("plus", size=14),
                    "Add Participant",
                    size="2",
                    color_scheme="iris",
                    border_radius=RADIUS_SM,
                    on_click=NexusState.submit_add_participant,
                    cursor="pointer",
                ),
                spacing="2",
                margin_top="16px",
            ),
            margin_bottom="12px",
        ),
        rx.fragment(),
    )


# -----------------------------------------------------------------------
# Sort header row
# -----------------------------------------------------------------------

def _sort_header(label: str, field: str, width: str = "auto") -> rx.Component:
    """Clickable column header that toggles sort."""
    return rx.hstack(
        rx.text(
            label, size="1", weight="bold",
            color=SUBTEXT,
        ),
        rx.cond(
            NexusState.sort_field == field,
            rx.cond(
                NexusState.sort_dir == "asc",
                rx.icon("arrow-up", size=10, color=ACCENT),
                rx.icon("arrow-down", size=10, color=ACCENT),
            ),
            rx.icon("arrow-up-down", size=10, color=MUTED),
        ),
        spacing="1",
        align="center",
        cursor="pointer",
        on_click=NexusState.set_sort(field),
        width=width,
        _hover={"color": ACCENT},
    )


# -----------------------------------------------------------------------
# Delete dialog
# -----------------------------------------------------------------------

def _bulk_delete_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Participants"),
            rx.alert_dialog.description(
                "Are you sure you want to delete the selected participant(s)? "
                "This action cannot be undone."
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=NexusState.close_bulk_delete,
                        cursor="pointer",
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=NexusState.confirm_bulk_delete,
                        cursor="pointer",
                    ),
                ),
                spacing="3",
                justify="end",
                width="100%",
                margin_top="16px",
            ),
        ),
        open=NexusState.show_bulk_delete_dialog,
    )


def _delete_participant_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Participant"),
            rx.alert_dialog.description(
                "Are you sure you want to delete this participant? This action cannot be undone."
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=NexusState.close_delete_participant,
                        cursor="pointer",
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=NexusState.confirm_delete_participant,
                        cursor="pointer",
                    ),
                ),
                spacing="3",
                justify="end",
                width="100%",
                margin_top="16px",
            ),
        ),
        open=NexusState.show_delete_participant_dialog,
    )


def _delete_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Delete Campaign"),
            rx.alert_dialog.description(
                "This will permanently delete the campaign and all participant "
                "records. This action cannot be undone."
            ),
            rx.hstack(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                        on_click=NexusState.toggle_delete_dialog,
                        cursor="pointer",
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Delete",
                        color_scheme="red",
                        on_click=NexusState.confirm_delete_campaign,
                        cursor="pointer",
                    ),
                ),
                spacing="3",
                justify="end",
                width="100%",
                margin_top="16px",
            ),
        ),
        open=NexusState.show_delete_dialog,
    )


# -----------------------------------------------------------------------
# Participant list
# -----------------------------------------------------------------------

def _participant_list() -> rx.Component:
    return rx.cond(
        NexusState.total_count > 0,
        rx.vstack(
            # ── Bookings section ──
            rx.hstack(
                rx.icon("calendar", size=16, color=AMBER),
                rx.text(
                    "Bookings",
                    size="3",
                    weight="bold",
                    color=HEADING,
                ),
                rx.badge(
                    NexusState.booked_count.to(str),
                    color_scheme="amber",
                    size="1",
                    variant="soft",
                ),
                spacing="2",
                align="center",
                width="100%",
                padding_x="4px",
            ),
            # column header with sort
            rx.hstack(
                rx.box(width="24px", flex_shrink="0"),  # checkbox spacer
                _sort_header("Date / Time", "appointment_time", width="110px"),
                _sort_header("Participant", "name"),
                rx.text("Platform", size="1", weight="bold", width="130px", color=SUBTEXT),
                rx.text("Model", size="1", weight="bold", width="110px", color=SUBTEXT),
                rx.text("Notes", size="1", weight="bold", width="180px", color=SUBTEXT),
                padding_x="16px",
                padding_y="6px",
                width="100%",
                display=["none", "none", "none", "flex"],
                spacing="3",
                align="center",
            ),
            rx.cond(
                NexusState.booked_count > 0,
                rx.vstack(
                    rx.foreach(
                        NexusState.booked_participants,
                        participant_row,
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.center(
                    rx.text("All participants completed!", size="2", color=SUBTEXT),
                    padding_y="20px",
                ),
            ),
            # ── Completed section ──
            rx.box(height="24px"),
            rx.hstack(
                rx.icon("check-circle-2", size=16, color=GREEN),
                rx.text(
                    "Completed",
                    size="3",
                    weight="bold",
                    color=HEADING,
                ),
                rx.badge(
                    NexusState.completed_count.to(str),
                    color_scheme="green",
                    size="1",
                    variant="soft",
                ),
                spacing="2",
                align="center",
                width="100%",
                padding_x="4px",
            ),
            rx.cond(
                NexusState.completed_count > 0,
                rx.vstack(
                    rx.foreach(
                        NexusState.completed_participants,
                        participant_row,
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.center(
                    rx.text("No completed participants yet", size="2", color=SUBTEXT),
                    padding_y="20px",
                ),
            ),
            spacing="2",
            width="100%",
        ),
        # empty state
        rx.center(
            rx.vstack(
                rx.center(
                    rx.icon("users", size=48, color=MUTED),
                    width="88px", height="88px",
                    border_radius="50%",
                    background=ACCENT_SOFT,
                ),
                rx.text(
                    "No participants yet",
                    size="3",
                    weight="medium",
                    color=HEADING,
                ),
                rx.text(
                    "Sync a calendar or add participants manually.",
                    size="2",
                    color=SUBTEXT,
                ),
                spacing="2",
                align="center",
            ),
            padding_y="60px",
        ),
    )


# -----------------------------------------------------------------------
# Page
# -----------------------------------------------------------------------

def campaign_detail_page() -> rx.Component:
    return rx.box(
        # -- sync error banner
        rx.cond(
            NexusState.sync_error != "",
            rx.callout(
                NexusState.sync_error,
                icon="triangle-alert",
                color_scheme="red",
                border_radius=RADIUS_MD,
                margin_bottom="16px",
            ),
        ),
        # -- back link
        rx.link(
            rx.hstack(
                rx.icon("arrow-left", size=16),
                rx.text("All Campaigns", size="2"),
                spacing="2",
                align="center",
                color=SUBTEXT,
                _hover={"color": ACCENT},
            ),
            href="/",
            margin_bottom="20px",
        ),
        # -- campaign header
        _campaign_header(),
        rx.box(height="16px"),
        # -- stats & progress
        _stats_and_progress(),
        # -- participant filters
        _participant_filter_bar(),
        # -- sync & search bar
        _sync_bar(),
        # -- range sync panel
        _range_sync_panel(),
        # -- issue editor dialog
        _issue_editor_dialog(),
        # -- add participant panel
        _add_participant_dialog(),
        # -- bulk action bar
        _bulk_action_bar(),
        # -- participant list
        _participant_list(),
        # -- bulk delete dialog
        _bulk_delete_dialog(),
        # -- delete participant dialog
        _delete_participant_dialog(),
        # -- delete campaign dialog
        _delete_dialog(),
        max_width=MAX_WIDTH,
        margin="0 auto",
        padding_x=PAGE_PADDING_X,
        padding_top="100px",
        padding_bottom=PAGE_PADDING_BOTTOM,
        min_height="100vh",
    )
