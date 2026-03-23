"""Dashboard - campaign grid with global stats, search, and archive toggle."""

import reflex as rx

from ..state import NexusState
from ..components.navbar import navbar
from ..components.campaign_card import campaign_card
from ..components.stat_card import stat_card
from ..components.design_tokens import (
    ACCENT,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
    BG,
    BORDER,
    CARD_BG,
    GREEN,
    GREEN_SOFT,
    HEADING,
    MAX_WIDTH,
    MUTED,
    PAGE_PADDING_BOTTOM,
    PAGE_PADDING_TOP,
    PAGE_PADDING_X,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    RED,
    RED_SOFT,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    TRANSITION_FAST,
    glass_card,
)


def _device_chip(label: str, value: str) -> rx.Component:
    """Filter chip that highlights when active."""
    is_active = NexusState.campaign_device_filter == value
    return rx.box(
        rx.text(label, size="1", weight="medium",
                color=rx.cond(is_active, "white", SUBTEXT)),
        padding_x="10px",
        padding_y="4px",
        border_radius=RADIUS_SM,
        background=rx.cond(is_active, ACCENT, "transparent"),
        border=rx.cond(is_active, "1px solid transparent", BORDER),
        cursor="pointer",
        transition=TRANSITION_FAST,
        on_click=NexusState.set_campaign_device_filter(value),
        _hover={"opacity": "0.8"},
    )


def _campaign_cta(primary_label: str) -> rx.Component:
    return rx.cond(
        NexusState.admin_mode,
        rx.link(
            rx.button(
                rx.icon("plus", size=15),
                primary_label,
                size="2",
                variant="solid",
                cursor="pointer",
                border_radius=RADIUS_MD,
                background=ACCENT,
            ),
            href="/new",
            _hover={"text_decoration": "none"},
        ),
        rx.link(
            rx.button(
                rx.icon("lock", size=15),
                "Unlock Admin",
                size="2",
                variant="soft",
                cursor="pointer",
                border_radius=RADIUS_MD,
            ),
            href="/settings",
            _hover={"text_decoration": "none"},
        ),
    )


def _dashboard_date_bar() -> rx.Component:
    return glass_card(
        rx.flex(
            rx.vstack(
                rx.hstack(
                    rx.icon("calendar-days", size=16, color=ACCENT),
                    rx.text("Dashboard Day", size="2", weight="bold", color=HEADING),
                    spacing="2",
                    align="center",
                ),
                rx.heading(
                    NexusState.display_date_label,
                    size="5",
                    weight="bold",
                    color=HEADING,
                ),
                rx.text(
                    NexusState.dashboard_date_context_note,
                    size="1",
                    color=SUBTEXT,
                    max_width="520px",
                    line_height="1.5",
                ),
                spacing="2",
                align="start",
            ),
            rx.vstack(
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.box(
                                width="7px",
                                height="7px",
                                border_radius="50%",
                                background=rx.cond(
                                    NexusState.dashboard_sync_attention_state == "ok",
                                    GREEN,
                                    rx.cond(
                                        NexusState.dashboard_sync_attention_state == "failed",
                                        RED,
                                        AMBER,
                                    ),
                                ),
                            ),
                            rx.text(
                                NexusState.dashboard_sync_attention_label,
                                size="1",
                                weight="bold",
                                color=HEADING,
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.text(
                            NexusState.dashboard_sync_attention_detail,
                            size="1",
                            color=SUBTEXT,
                            line_height="1.5",
                            max_width="320px",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    padding="10px 12px",
                    border_radius=RADIUS_MD,
                    background=rx.cond(
                        NexusState.dashboard_sync_attention_state == "ok",
                        GREEN_SOFT,
                        rx.cond(
                            NexusState.dashboard_sync_attention_state == "failed",
                            RED_SOFT,
                            AMBER_SOFT,
                        ),
                    ),
                    border=rx.cond(
                        NexusState.dashboard_sync_attention_state == "ok",
                        "1px solid rgba(34,197,94,0.16)",
                        rx.cond(
                            NexusState.dashboard_sync_attention_state == "failed",
                            "1px solid rgba(239,68,68,0.18)",
                            "1px solid rgba(245,158,11,0.18)",
                        ),
                    ),
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Previous",
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                        border_radius=RADIUS_SM,
                        on_click=NexusState.dashboard_prev_day,
                        cursor="pointer",
                    ),
                    rx.button(
                        "Today",
                        size="1",
                        variant=rx.cond(NexusState.is_today, "solid", "soft"),
                        color_scheme="iris",
                        border_radius=RADIUS_SM,
                        on_click=NexusState.dashboard_today,
                        cursor="pointer",
                    ),
                    rx.button(
                        "Next",
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                        border_radius=RADIUS_SM,
                        on_click=NexusState.dashboard_next_day,
                        cursor="pointer",
                    ),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                ),
                spacing="3",
                align="stretch",
                width=rx.breakpoints(initial="100%", md="auto"),
            ),
            direction=rx.breakpoints(initial="column", md="row"),
            justify="between",
            align=rx.breakpoints(initial="start", md="start"),
            gap="4",
            width="100%",
        ),
        margin_bottom="16px",
    )


# -- Empty state
def _empty_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.center(
                rx.icon(
                    "folder-plus", size=42, stroke_width=1.2,
                    color=MUTED,
                ),
                width="88px", height="88px",
                border_radius="50%",
                background=ACCENT_SOFT,
            ),
            rx.text(
                "No campaigns yet",
                size="4", weight="medium", color=HEADING,
            ),
            rx.cond(
                NexusState.admin_mode,
                rx.text(
                    "Create your first collection campaign to start tracking.",
                    size="2", color=SUBTEXT, text_align="center",
                    max_width="320px",
                ),
                rx.text(
                    "Unlock admin mode in Settings to create your first collection campaign.",
                    size="2", color=SUBTEXT, text_align="center",
                    max_width="320px",
                ),
            ),
            _campaign_cta("Create Campaign"),
            align="center",
            spacing="3",
            padding="80px 24px",
        ),
    )


# -- Page
def dashboard_page() -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            # -- Header row
            rx.flex(
                rx.vstack(
                    rx.heading(
                        "Campaigns",
                        size="6", weight="bold",
                        color=HEADING,
                        letter_spacing="-0.03em",
                    ),
                    spacing="1",
                ),
                rx.hstack(
                    # Search bar
                    rx.box(
                        rx.hstack(
                            rx.icon("search", size=14, color=SUBTEXT),
                            rx.input(
                                placeholder="Search campaigns...",
                                value=NexusState.campaign_search_query,
                                on_change=NexusState.set_campaign_search,
                                variant="surface",
                                size="2",
                                border_radius=RADIUS_MD,
                                width="200px",
                            ),
                            spacing="2",
                            align="center",
                        ),
                    ),
                    # Show completed toggle
                    rx.hstack(
                        rx.switch(
                            checked=NexusState.show_archived,
                            on_change=lambda _v: NexusState.toggle_show_archived(),
                            size="1",
                            color_scheme="iris",
                        ),
                        rx.text(
                            "Completed", size="1", color=SUBTEXT, weight="medium",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    # New campaign button
                    _campaign_cta("New Campaign"),
                    spacing="3",
                    align="center",
                ),
                direction=rx.breakpoints(initial="column", sm="row"),
                justify="between",
                align=rx.breakpoints(initial="start", sm="end"),
                gap="4",
                width="100%",
            ),
            _dashboard_date_bar(),
            # -- Stat row
            rx.grid(
                stat_card(
                    "Total",
                    NexusState.all_campaigns_count,
                    "layers",
                    "#6366f1",
                ),
                stat_card(
                    "Active",
                    NexusState.all_active_count,
                    "zap",
                    "#22c55e",
                ),
                stat_card(
                    "Completed",
                    NexusState.all_completed_count,
                    "circle-check-big",
                    "#8b5cf6",
                ),
                columns=rx.breakpoints(initial="3", sm="3"),
                spacing="3",
                width="100%",
            ),
            # -- Device filter chips + sort selector
            rx.hstack(
                _device_chip("All", ""),
                rx.foreach(
                    NexusState.platforms,
                    lambda platform: _device_chip(platform, platform),
                ),
                rx.spacer(),
                rx.select(
                    ["created_at", "name", "device_type", "progress"],
                    value=NexusState.campaign_sort_field,
                    on_change=NexusState.set_campaign_sort_field,
                    placeholder="Sort by...",
                    size="1",
                    variant="soft",
                ),
                spacing="2",
                align="center",
                width="100%",
                flex_wrap="wrap",
            ),
            # -- Campaign grid
            rx.cond(
                NexusState.filtered_campaigns.length() > 0,
                rx.grid(
                    rx.foreach(NexusState.filtered_campaigns, campaign_card),
                    columns=rx.breakpoints(initial="1", sm="2", lg="3"),
                    spacing="4",
                    width="100%",
                ),
                _empty_state(),
            ),
            # -- Container
            max_width=MAX_WIDTH,
            margin_x="auto",
            padding_x=PAGE_PADDING_X,
            padding_top="28px",
            padding_bottom=PAGE_PADDING_BOTTOM,
            width="100%",
            display="flex",
            flex_direction="column",
            gap="20px",
            class_name="page-content",
        ),
        bg=BG,
        min_height="100vh",
    )
