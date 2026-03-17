"""Dashboard - campaign grid with global stats, search, and archive toggle."""

import reflex as rx

from ..state import NexusState
from ..components.navbar import navbar
from ..components.campaign_card import campaign_card
from ..components.stat_card import stat_card
from ..components.design_tokens import (
    ACCENT,
    ACCENT_GRADIENT_H,
    ACCENT_LIGHT,
    ACCENT_SOFT,
    BG,
    BORDER,
    CARD_BG,
    HEADING,
    MAX_WIDTH,
    MUTED,
    PAGE_PADDING_BOTTOM,
    PAGE_PADDING_TOP,
    PAGE_PADDING_X,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    glass_card,
    progress_bar,
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
            rx.text(
                "Create your first collection campaign to start tracking.",
                size="2", color=SUBTEXT, text_align="center",
                max_width="320px",
            ),
            rx.link(
                rx.button(
                    rx.icon("plus", size=14),
                    "Create Campaign",
                    size="2",
                    variant="solid",
                    cursor="pointer",
                    border_radius=RADIUS_MD,
                    background=ACCENT,
                ),
                href="/new",
                _hover={"text_decoration": "none"},
            ),
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
                    # Show archived toggle
                    rx.hstack(
                        rx.switch(
                            checked=NexusState.show_archived,
                            on_change=lambda _v: NexusState.toggle_show_archived(),
                            size="1",
                            color_scheme="iris",
                        ),
                        rx.text(
                            "Archived", size="1", color=SUBTEXT, weight="medium",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    # New campaign button
                    rx.link(
                        rx.button(
                            rx.icon("plus", size=15),
                            "New Campaign",
                            size="2",
                            variant="solid",
                            cursor="pointer",
                            border_radius=RADIUS_MD,
                            background=ACCENT,
                        ),
                        href="/new",
                        _hover={"text_decoration": "none"},
                    ),
                    spacing="3",
                    align="center",
                ),
                direction=rx.breakpoints(initial="column", sm="row"),
                justify="between",
                align=rx.breakpoints(initial="start", sm="end"),
                gap="4",
                width="100%",
            ),
            # -- Stat row
            rx.grid(
                stat_card(
                    "Campaigns",
                    NexusState.campaigns.length(),
                    "layers",
                    "#6366f1",
                ),
                stat_card(
                    "Active",
                    NexusState.active_campaign_count,
                    "zap",
                    "#22c55e",
                ),
                stat_card(
                    "Participants",
                    NexusState.total_participants_today,
                    "users",
                    "#3b82f6",
                ),
                stat_card(
                    "Completed",
                    NexusState.total_completed_today,
                    "circle-check-big",
                    "#8b5cf6",
                ),
                columns=rx.breakpoints(initial="2", sm="4"),
                spacing="3",
                width="100%",
            ),
            # -- Overall progress bar card
            glass_card(
                rx.hstack(
                    rx.text(
                        "Overall Progress", size="2", weight="medium",
                        color=SUBTEXT,
                    ),
                    rx.spacer(),
                    rx.text(
                        NexusState.overall_progress, "%",
                        size="2", weight="bold",
                        color=ACCENT_LIGHT,
                        font_variant_numeric="tabular-nums",
                    ),
                    width="100%",
                ),
                rx.box(height="8px"),
                progress_bar(NexusState.overall_progress, height="6px"),
                padding="16px 20px",
                width="100%",
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
