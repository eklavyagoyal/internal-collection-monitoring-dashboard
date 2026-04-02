"""Dashboard - lightweight campaign grid with compact controls and summary strip."""

import reflex as rx

from ..state import NexusState
from ..components.navbar import navbar
from ..components.campaign_card import campaign_card
from ..components.design_tokens import (
    ACCENT,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
    BG,
    BORDER,
    GREEN,
    GREEN_SOFT,
    HEADING,
    MAX_WIDTH,
    MUTED,
    PAGE_PADDING_BOTTOM,
    PAGE_PADDING_X,
    RADIUS_FULL,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    RED,
    RED_SOFT,
    SUBTEXT,
    TEXT,
    TRANSITION_FAST,
    glass_card,
)


def _device_chip(label: str, value: str) -> rx.Component:
    """Filter chip that highlights when active."""
    is_active = NexusState.campaign_device_filter == value
    return rx.box(
        rx.text(
            label,
            size="1",
            weight="medium",
            color=rx.cond(is_active, "white", SUBTEXT),
        ),
        padding_x="10px",
        padding_y="5px",
        border_radius=RADIUS_FULL,
        background=rx.cond(is_active, ACCENT, "transparent"),
        border=rx.cond(is_active, "1px solid transparent", BORDER),
        cursor="pointer",
        transition=TRANSITION_FAST,
        on_click=NexusState.set_campaign_device_filter(value),
        _hover={"opacity": "0.85"},
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


def _summary_metric(label: str, value, accent_bg) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                value,
                size="3",
                weight="bold",
                color=HEADING,
                font_variant_numeric="tabular-nums",
                line_height="1",
            ),
            rx.text(
                label,
                size="1",
                color=SUBTEXT,
                text_transform="uppercase",
                letter_spacing="0.04em",
            ),
            spacing="1",
            align="start",
        ),
        padding="9px 11px",
        border_radius=RADIUS_MD,
        background=accent_bg,
        border=BORDER,
        min_width="100px",
    )


def _attention_chip() -> rx.Component:
    state = NexusState.dashboard_sync_attention_state
    background = rx.cond(
        state == "ok",
        GREEN_SOFT,
        rx.cond(state == "failed", RED_SOFT, AMBER_SOFT),
    )
    dot = rx.cond(
        state == "ok",
        GREEN,
        rx.cond(state == "failed", RED, AMBER),
    )
    return rx.box(
        rx.hstack(
            rx.box(
                width="7px",
                height="7px",
                border_radius="50%",
                background=dot,
                flex_shrink="0",
            ),
            rx.vstack(
                rx.text(
                    NexusState.dashboard_sync_attention_short,
                    size="1",
                    weight="bold",
                    color=HEADING,
                ),
                rx.text(
                    NexusState.dashboard_sync_attention_detail,
                    size="1",
                    color=SUBTEXT,
                    line_height="1.4",
                ),
                spacing="0",
                align="start",
            ),
            spacing="2",
            align="center",
        ),
        padding="9px 11px",
        border_radius=RADIUS_MD,
        background=background,
        border=BORDER,
    )


def _dashboard_summary_strip() -> rx.Component:
    return glass_card(
        rx.vstack(
            rx.flex(
                rx.vstack(
                    rx.text("Day", size="1", weight="bold", color=SUBTEXT),
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
                        line_height="1.45",
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.vstack(
                    _attention_chip(),
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
                    align=rx.breakpoints(initial="start", md="end"),
                    width=rx.breakpoints(initial="100%", md="auto"),
                ),
                direction=rx.breakpoints(initial="column", md="row"),
                justify="between",
                align=rx.breakpoints(initial="start", md="center"),
                gap="4",
                width="100%",
            ),
            rx.box(height="1px", background=BORDER, width="100%"),
            rx.flex(
                rx.hstack(
                    _summary_metric("Total", NexusState.all_campaigns_count, ACCENT_SOFT),
                    _summary_metric("Active", NexusState.all_active_count, GREEN_SOFT),
                    _summary_metric("Completed", NexusState.all_completed_count, AMBER_SOFT),
                    spacing="2",
                    flex_wrap="wrap",
                ),
                rx.hstack(
                    _device_chip("All", ""),
                    rx.foreach(
                        NexusState.platforms,
                        lambda platform: _device_chip(platform, platform),
                    ),
                    rx.select(
                        ["created_at", "name", "device_type", "progress"],
                        value=NexusState.campaign_sort_field,
                        on_change=NexusState.set_campaign_sort_field,
                        placeholder="Sort by...",
                        size="1",
                        variant="soft",
                        width="120px",
                    ),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                    justify="end",
                ),
                direction=rx.breakpoints(initial="column", lg="row"),
                justify="between",
                align=rx.breakpoints(initial="start", lg="center"),
                gap="3",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        padding="16px 18px",
    )


def _empty_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.center(
                rx.icon(
                    "folder-plus",
                    size=42,
                    stroke_width=1.2,
                    color=MUTED,
                ),
                width="88px",
                height="88px",
                border_radius="50%",
                background=ACCENT_SOFT,
            ),
            rx.text(
                "No campaigns yet",
                size="4",
                weight="medium",
                color=HEADING,
            ),
            rx.cond(
                NexusState.admin_mode,
                rx.text(
                    "Create your first campaign to start tracking.",
                    size="2",
                    color=SUBTEXT,
                    text_align="center",
                    max_width="320px",
                ),
                rx.text(
                    "Unlock admin in Settings to create your first campaign.",
                    size="2",
                    color=SUBTEXT,
                    text_align="center",
                    max_width="320px",
                ),
            ),
            _campaign_cta("Create Campaign"),
            align="center",
            spacing="3",
            padding="80px 24px",
        ),
    )


def _loading_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.spinner(size="3"),
            rx.text(
                "Loading campaigns",
                size="4",
                weight="medium",
                color=HEADING,
            ),
            rx.text(
                "Waiting for the first dashboard refresh.",
                size="2",
                color=SUBTEXT,
                text_align="center",
                max_width="320px",
            ),
            align="center",
            spacing="3",
            padding="80px 24px",
        ),
    )


def _refresh_error_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.center(
                rx.icon(
                    "triangle-alert",
                    size=42,
                    stroke_width=1.2,
                    color=RED,
                ),
                width="88px",
                height="88px",
                border_radius="50%",
                background=RED_SOFT,
            ),
            rx.text(
                "Couldn't load campaigns",
                size="4",
                weight="medium",
                color=HEADING,
            ),
            rx.text(
                NexusState.app_refresh_health["detail"],
                size="2",
                color=SUBTEXT,
                text_align="center",
                max_width="360px",
            ),
            rx.text(
                NexusState.last_data_refresh_error,
                size="1",
                color=RED,
                text_align="center",
                max_width="420px",
                line_height="1.5",
            ),
            align="center",
            spacing="3",
            padding="80px 24px",
        ),
    )


def _filtered_empty_state() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.center(
                rx.icon(
                    "search-x",
                    size=42,
                    stroke_width=1.2,
                    color=MUTED,
                ),
                width="88px",
                height="88px",
                border_radius="50%",
                background=ACCENT_SOFT,
            ),
            rx.text(
                "No campaigns match this view",
                size="4",
                weight="medium",
                color=HEADING,
            ),
            rx.text(
                rx.cond(
                    (NexusState.campaign_search_query != "")
                    & (NexusState.campaign_device_filter != ""),
                    "Adjust the search and platform filter to bring campaigns back into view.",
                    rx.cond(
                        NexusState.campaign_search_query != "",
                        "Adjust the search query to bring campaigns back into view.",
                        "Adjust the platform filter to bring campaigns back into view.",
                    ),
                ),
                size="2",
                color=SUBTEXT,
                text_align="center",
                max_width="360px",
            ),
            align="center",
            spacing="3",
            padding="80px 24px",
        ),
    )


def dashboard_page() -> rx.Component:
    return rx.box(
        navbar(),
        rx.box(
            rx.flex(
                rx.vstack(
                    rx.heading(
                        "Campaigns",
                        size="6",
                        weight="bold",
                        color=HEADING,
                        letter_spacing="-0.03em",
                    ),
                    rx.text(
                        "Progress, sync, and today’s work.",
                        size="1",
                        color=SUBTEXT,
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.hstack(
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
                                width=rx.breakpoints(initial="100%", sm="220px"),
                            ),
                            spacing="2",
                            align="center",
                        ),
                        width=rx.breakpoints(initial="100%", sm="auto"),
                    ),
                    rx.hstack(
                        rx.switch(
                            checked=NexusState.show_archived,
                            on_change=lambda _v: NexusState.toggle_show_archived(),
                            size="1",
                            color_scheme="iris",
                        ),
                        rx.text(
                            "Show completed",
                            size="1",
                            color=SUBTEXT,
                            weight="medium",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    _campaign_cta("New Campaign"),
                    spacing="3",
                    align="center",
                    flex_wrap="wrap",
                    justify="end",
                ),
                direction=rx.breakpoints(initial="column", sm="row"),
                justify="between",
                align=rx.breakpoints(initial="start", sm="end"),
                gap="4",
                width="100%",
            ),
            _dashboard_summary_strip(),
            rx.cond(
                NexusState.filtered_campaigns.length() > 0,
                rx.grid(
                    rx.foreach(NexusState.filtered_campaigns, campaign_card),
                    columns=rx.breakpoints(initial="1", sm="2", lg="3"),
                    spacing="3",
                    width="100%",
                ),
                rx.cond(
                    NexusState.is_loading & (NexusState.campaigns.length() == 0),
                    _loading_state(),
                    rx.cond(
                        (NexusState.campaigns.length() == 0)
                        & (NexusState.last_data_refresh_error != ""),
                        _refresh_error_state(),
                        rx.cond(
                            NexusState.campaigns.length() > 0,
                            _filtered_empty_state(),
                            _empty_state(),
                        ),
                    ),
                ),
            ),
            max_width=MAX_WIDTH,
            margin_x="auto",
            padding_x=PAGE_PADDING_X,
            padding_top="28px",
            padding_bottom=PAGE_PADDING_BOTTOM,
            width="100%",
            display="flex",
            flex_direction="column",
            gap="18px",
            class_name="page-content",
        ),
        bg=BG,
        min_height="100vh",
    )
