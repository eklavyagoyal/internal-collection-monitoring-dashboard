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
    progress_bar,
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
# Date navigator strip
# -----------------------------------------------------------------------

def _date_navigator() -> rx.Component:
    return rx.hstack(
        rx.icon_button(
            rx.icon("chevron-left", size=18),
            size="2",
            variant="soft",
            color_scheme="gray",
            border_radius=RADIUS_MD,
            on_click=NexusState.navigate_prev_day,
            cursor="pointer",
        ),
        rx.vstack(
            rx.text(
                NexusState.display_date_label,
                size="3",
                weight="bold",
                color=HEADING,
                text_align="center",
            ),
            spacing="0",
            align="center",
        ),
        rx.icon_button(
            rx.icon("chevron-right", size=18),
            size="2",
            variant="soft",
            color_scheme="gray",
            border_radius=RADIUS_MD,
            on_click=NexusState.navigate_next_day,
            cursor="pointer",
        ),
        rx.cond(
            ~NexusState.is_today,
            rx.button(
                "Today",
                size="1",
                variant="soft",
                color_scheme="iris",
                border_radius=RADIUS_SM,
                on_click=NexusState.navigate_to_today,
                cursor="pointer",
            ),
        ),
        spacing="3",
        align="center",
        padding_x="16px",
        padding_y="10px",
        border_radius=RADIUS_MD,
        background=CARD_BG,
        border=BORDER,
        backdrop_filter="blur(16px) saturate(180%)",
    )


# -----------------------------------------------------------------------
# Campaign header card
# -----------------------------------------------------------------------

def _campaign_header() -> rx.Component:
    return glass_card(
        # Top row: name + actions
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        NexusState.campaign_name,
                        size="6",
                        weight="bold",
                        color=HEADING,
                    ),
                    # status badge
                    rx.cond(
                        NexusState.campaign_status == "active",
                        rx.badge("Active", color_scheme="green", size="1",
                                 variant="soft", cursor="pointer",
                                 on_click=NexusState.toggle_campaign_status),
                        rx.cond(
                            NexusState.campaign_status == "archived",
                            rx.badge("Archived", color_scheme="gray", size="1",
                                     variant="soft"),
                            rx.badge("Paused", color_scheme="orange", size="1",
                                     variant="soft", cursor="pointer",
                                     on_click=NexusState.toggle_campaign_status),
                        ),
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
                spacing="2",
            ),
            rx.spacer(),
            # Action buttons
            rx.hstack(
                # Archive / Unarchive
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
                    rx.icon("trash-2", size=16),
                    size="2",
                    variant="soft",
                    color_scheme="red",
                    border_radius=RADIUS_MD,
                    on_click=NexusState.toggle_delete_dialog,
                    cursor="pointer",
                ),
                spacing="2",
            ),
            width="100%",
            align="start",
        ),
        # Meta pills row
        rx.hstack(
            rx.cond(
                NexusState.campaign_calendar_filter != "",
                rx.hstack(
                    rx.icon("filter", size=12, color=ACCENT),
                    rx.text(NexusState.campaign_calendar_filter, size="1"),
                    spacing="1",
                    align="center",
                    padding_x="10px",
                    padding_y="4px",
                    border_radius=RADIUS_SM,
                    background=ACCENT_SOFT,
                ),
            ),
            rx.cond(
                NexusState.campaign_created_at != "",
                rx.hstack(
                    rx.icon("calendar", size=12, color=SUBTEXT),
                    rx.text(NexusState.campaign_created_at, size="1", color=SUBTEXT),
                    spacing="1",
                    align="center",
                ),
            ),
            # External links
            rx.cond(
                NexusState.campaign_notion_url != "",
                rx.link(
                    rx.hstack(
                        rx.icon("book-open", size=12),
                        rx.text("Notion", size="1"),
                        spacing="1", color=ACCENT,
                    ),
                    href=NexusState.campaign_notion_url,
                    is_external=True,
                ),
            ),
            rx.cond(
                NexusState.campaign_linear_url != "",
                rx.link(
                    rx.hstack(
                        rx.icon("git-branch", size=12),
                        rx.text("Linear", size="1"),
                        spacing="1", color=ACCENT,
                    ),
                    href=NexusState.campaign_linear_url,
                    is_external=True,
                ),
            ),
            rx.cond(
                NexusState.campaign_booking_url != "",
                rx.link(
                    rx.hstack(
                        rx.icon("calendar-check", size=12),
                        rx.text("Booking", size="1"),
                        spacing="1", color=ACCENT,
                    ),
                    href=NexusState.campaign_booking_url,
                    is_external=True,
                ),
            ),
            spacing="3",
            align="center",
            flex_wrap="wrap",
            margin_top="12px",
        ),
        margin_bottom="16px",
    )


# -----------------------------------------------------------------------
# Stats + progress bar
# -----------------------------------------------------------------------

def _stats_and_progress() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            _stat_pill("Pending", NexusState.pending_count, AMBER, AMBER_SOFT),
            _stat_pill("Active", NexusState.in_progress_count, ACCENT, ACCENT_SOFT),
            _stat_pill("Done", NexusState.completed_count, GREEN, GREEN_SOFT),
            rx.spacer(),
            rx.text(
                NexusState.progress_pct.to(str) + "%",
                size="4",
                weight="bold",
                background=ACCENT_GRADIENT,
                background_clip="text",
                color="transparent",
            ),
            spacing="3",
            align="center",
            width="100%",
            flex_wrap="wrap",
        ),
        progress_bar(NexusState.progress_pct, height="8px"),
        spacing="3",
        width="100%",
        margin_bottom="16px",
    )


# -----------------------------------------------------------------------
# Sync bar + search + CSV export + Add participant
# -----------------------------------------------------------------------

def _sync_bar() -> rx.Component:
    return rx.hstack(
        # Sync button
        rx.button(
            rx.cond(
                NexusState.is_syncing,
                rx.spinner(size="1"),
                rx.icon("refresh-cw", size=14),
            ),
            "Sync",
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
                    "Mark In-Progress",
                    size="1",
                    variant="soft",
                    color_scheme="orange",
                    border_radius=RADIUS_SM,
                    on_click=NexusState.bulk_set_status("In-Progress"),
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
            # column header with sort
            rx.hstack(
                rx.checkbox(
                    checked=NexusState.all_selected,
                    on_change=lambda _v: NexusState.select_all(),
                    size="1",
                    color_scheme="iris",
                    cursor="pointer",
                ),
                rx.text("", width="10px"),
                _sort_header("Time", "appointment_time", width="60px"),
                _sort_header("Participant", "name"),
                rx.text("Platform", size="1", weight="bold", width="130px", color=SUBTEXT),
                rx.text("Model", size="1", weight="bold", width="110px", color=SUBTEXT),
                _sort_header("Status", "status", width="130px"),
                rx.text("Notes", size="1", weight="bold", width="180px", color=SUBTEXT),
                padding_x="16px",
                padding_y="6px",
                width="100%",
                display=["none", "none", "none", "flex"],
                spacing="3",
                align="center",
            ),
            rx.foreach(
                NexusState.sorted_filtered_participants,
                participant_row,
            ),
            spacing="2",
            width="100%",
        ),
        # empty state
        rx.center(
            rx.vstack(
                rx.center(
                    rx.icon("calendar-x", size=48, color=MUTED),
                    width="88px", height="88px",
                    border_radius="50%",
                    background=ACCENT_SOFT,
                ),
                rx.text(
                    "No participants for this date",
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
        # -- date navigator
        _date_navigator(),
        rx.box(height="16px"),
        # -- stats & progress
        _stats_and_progress(),
        # -- sync & search bar
        _sync_bar(),
        # -- add participant panel
        _add_participant_dialog(),
        # -- bulk action bar
        _bulk_action_bar(),
        # -- participant list
        _participant_list(),
        # -- delete dialog
        _delete_dialog(),
        max_width=MAX_WIDTH,
        margin="0 auto",
        padding_x=PAGE_PADDING_X,
        padding_top="100px",
        padding_bottom=PAGE_PADDING_BOTTOM,
        min_height="100vh",
    )
