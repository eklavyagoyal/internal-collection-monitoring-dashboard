"""Settings page - label editor, calendar discovery, booking info. Two-column layout."""

import reflex as rx

from ..state import NexusState
from ..components.design_tokens import (
    ACCENT,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
    BORDER,
    CARD_BG,
    GREEN,
    HEADING,
    MAX_WIDTH,
    MUTED,
    PAGE_PADDING_BOTTOM,
    PAGE_PADDING_X,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    RED,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    TRANSITION_FAST,
    glass_card,
    section_header,
)


# ---------------------------------------------------------------------------
# Reusable: single label chip with remove button
# ---------------------------------------------------------------------------

def _label_chip(label: rx.Var[str], on_remove) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(
                label,
                size="2",
                weight="medium",
                color=HEADING,
            ),
            rx.icon_button(
                rx.icon("x", size=12),
                size="1",
                variant="ghost",
                color_scheme="red",
                on_click=on_remove(label),
                cursor="pointer",
                border_radius="50%",
            ),
            spacing="2",
            align="center",
        ),
        padding_x="14px",
        padding_y="8px",
        border_radius=RADIUS_MD,
        background=CARD_BG,
        border=BORDER,
        backdrop_filter="blur(16px) saturate(180%)",
        transition=TRANSITION_FAST,
        _hover={
            "border_color": rx.color_mode_cond(
                light="rgba(99,102,241,0.4)", dark="rgba(167,139,250,0.4)"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Reusable: label section (title + chips + add input)
# ---------------------------------------------------------------------------

def _label_section(
    title: str,
    description: str,
    icon_name: str,
    labels: rx.Var,
    new_value: rx.Var,
    set_new: callable,
    add_fn: callable,
    remove_fn: callable,
) -> rx.Component:
    return glass_card(
        section_header(icon_name, title, description),
        # Chips grid
        rx.flex(
            rx.foreach(
                labels,
                lambda label: _label_chip(label, remove_fn),
            ),
            wrap="wrap",
            gap="8px",
            margin_bottom="16px",
        ),
        # Add input row
        rx.hstack(
            rx.input(
                placeholder="Add new " + title.lower().rstrip("s") + "...",
                value=new_value,
                on_change=set_new,
                size="2",
                variant="surface",
                border_radius=RADIUS_MD,
                flex="1",
            ),
            rx.button(
                rx.icon("plus", size=16),
                "Add",
                size="2",
                variant="soft",
                color_scheme="iris",
                border_radius=RADIUS_MD,
                on_click=add_fn(),
                cursor="pointer",
            ),
            spacing="2",
            width="100%",
        ),
    )


# ---------------------------------------------------------------------------
# Calendar discovery section
# ---------------------------------------------------------------------------

def _calendar_discovery() -> rx.Component:
    return glass_card(
        section_header(
            "calendar-days",
            "Connected Calendars",
            "Calendars visible to your Google account. Use these IDs when setting up campaigns.",
        ),
        rx.button(
            rx.cond(
                NexusState.calendars_loading,
                rx.spinner(size="1"),
                rx.icon("refresh-cw", size=14),
            ),
            "Discover Calendars",
            size="2",
            variant="soft",
            color_scheme="iris",
            border_radius=RADIUS_MD,
            on_click=NexusState.fetch_available_calendars,
            loading=NexusState.calendars_loading,
            cursor="pointer",
            margin_bottom="12px",
        ),
        rx.cond(
            NexusState.available_calendars.length() > 0,
            rx.vstack(
                rx.foreach(
                    NexusState.available_calendars,
                    lambda cal: rx.hstack(
                        rx.cond(
                            cal["primary"],
                            rx.badge("Primary", color_scheme="green", size="1"),
                            rx.badge("Shared", color_scheme="blue", size="1"),
                        ),
                        rx.vstack(
                            rx.text(
                                cal["summary"].to(str),
                                size="2",
                                weight="medium",
                                color=HEADING,
                            ),
                            rx.text(
                                cal["id"].to(str),
                                size="1",
                                color=SUBTEXT,
                            ),
                            spacing="0",
                        ),
                        rx.spacer(),
                        rx.icon_button(
                            rx.icon("copy", size=14),
                            size="1",
                            variant="ghost",
                            color_scheme="gray",
                            on_click=rx.set_clipboard(cal["id"].to(str)),
                            cursor="pointer",
                        ),
                        spacing="3",
                        align="center",
                        padding="10px",
                        border_radius=RADIUS_MD,
                        background=CARD_BG,
                        border=BORDER,
                        width="100%",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.text(
                "Click Discover to list all available calendars.",
                size="2",
                color=SUBTEXT,
                font_style="italic",
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Booking page info card
# ---------------------------------------------------------------------------

def _booking_info() -> rx.Component:
    return glass_card(
        section_header(
            "info",
            "Appointment Booking Pages",
            "Calendly, Cal.com, Acuity, and similar tools create events directly on Google Calendar.",
        ),
        rx.text(
            "Nexus-Track automatically picks them up during sync. No extra integration needed.",
            size="2",
            color=TEXT,
            line_height="1.6",
            margin_bottom="16px",
        ),
        rx.box(
            rx.text("How it works", size="2", weight="bold", color=HEADING, margin_bottom="8px"),
            rx.vstack(
                rx.hstack(
                    rx.text("1.", weight="bold", color=ACCENT),
                    rx.text("Set up your booking tool to write to a Google Calendar.", size="2", color=TEXT),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text("2.", weight="bold", color=ACCENT),
                    rx.text("Create a campaign and set the Calendar ID to that calendar.", size="2", color=TEXT),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text("3.", weight="bold", color=ACCENT),
                    rx.text("Optionally add a keyword filter to only import matching events.", size="2", color=TEXT),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text("4.", weight="bold", color=ACCENT),
                    rx.text("Hit Sync on the campaign detail page - bookings appear instantly.", size="2", color=TEXT),
                    spacing="2",
                ),
                spacing="2",
                padding_left="8px",
            ),
            padding="16px",
            border_radius=RADIUS_MD,
            background=ACCENT_SOFT,
        ),
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def settings_page() -> rx.Component:
    return rx.box(
        # -- header
        rx.hstack(
            rx.link(
                rx.hstack(
                    rx.icon("arrow-left", size=16),
                    rx.text("Dashboard", size="2"),
                    spacing="2",
                    align="center",
                    color=SUBTEXT,
                    _hover={"color": ACCENT},
                ),
                href="/",
            ),
            rx.spacer(),
            rx.heading(
                "Settings",
                size="6",
                weight="bold",
                color=HEADING,
            ),
            rx.spacer(),
            # invisible spacer to center heading
            rx.box(width="80px"),
            width="100%",
            align="center",
            margin_bottom="32px",
        ),
        # -- 2-column grid for label editors
        rx.grid(
            _label_section(
                title="Platforms",
                description="Device/platform types used in data collection",
                icon_name="monitor-smartphone",
                labels=NexusState.platforms,
                new_value=NexusState.new_platform,
                set_new=NexusState.set_new_platform,
                add_fn=NexusState.add_platform,
                remove_fn=NexusState.remove_platform,
            ),
            _label_section(
                title="Model Tags",
                description="AI model versions being tested",
                icon_name="tag",
                labels=NexusState.model_tags,
                new_value=NexusState.new_model_tag,
                set_new=NexusState.set_new_model_tag,
                add_fn=NexusState.add_model_tag,
                remove_fn=NexusState.remove_model_tag,
            ),
            _label_section(
                title="Statuses",
                description="Participant tracking statuses",
                icon_name="list-checks",
                labels=NexusState.statuses,
                new_value=NexusState.new_status_label,
                set_new=NexusState.set_new_status_label,
                add_fn=NexusState.add_status_label,
                remove_fn=NexusState.remove_status_label,
            ),
            _calendar_discovery(),
            columns=rx.breakpoints(initial="1", md="2"),
            spacing="4",
            width="100%",
        ),
        # -- full-width info card
        rx.box(
            _booking_info(),
            margin_top="16px",
            width="100%",
        ),
        max_width="1000px",
        margin="0 auto",
        padding_x=PAGE_PADDING_X,
        padding_top="100px",
        padding_bottom=PAGE_PADDING_BOTTOM,
        min_height="100vh",
    )
