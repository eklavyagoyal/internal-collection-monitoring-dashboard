"""New-campaign page - create a campaign with all configurable fields."""

import reflex as rx

from ..state import NexusState
from ..components.design_tokens import (
    ACCENT,
    ACCENT_GRADIENT,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
    BORDER,
    HEADING,
    MAX_WIDTH_NARROW,
    PAGE_PADDING_BOTTOM,
    PAGE_PADDING_X,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    SUBTEXT,
    TEXT,
    form_field,
    glass_card,
    section_header,
)


def _admin_locked_panel() -> rx.Component:
    return glass_card(
        section_header(
            "lock",
            "Admin Access Required",
            "Campaign creation is protected so the dashboard stays safe and deliberate.",
        ),
        rx.text(
            "Unlock admin mode in Settings to create a campaign. Once admin mode is active, this page immediately becomes the full campaign setup form.",
            size="2",
            color=TEXT,
            line_height="1.6",
            margin_bottom="20px",
        ),
        rx.hstack(
            rx.link(
                rx.button(
                    rx.icon("lock", size=14),
                    "Unlock Admin",
                    size="2",
                    color_scheme="iris",
                    border_radius=RADIUS_MD,
                    cursor="pointer",
                    background=ACCENT_GRADIENT,
                ),
                href="/settings",
                _hover={"text_decoration": "none"},
            ),
            rx.link(
                rx.button(
                    "Back to Dashboard",
                    variant="soft",
                    color_scheme="gray",
                    size="2",
                    border_radius=RADIUS_MD,
                    cursor="pointer",
                ),
                href="/",
                _hover={"text_decoration": "none"},
            ),
            spacing="3",
            flex_wrap="wrap",
        ),
    )


def _calendar_discovery_hint() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.button(
                rx.cond(
                    NexusState.calendars_loading,
                    rx.spinner(size="1"),
                    rx.icon("refresh-cw", size=14),
                ),
                "Discover Calendars Here",
                size="2",
                variant="soft",
                color_scheme="iris",
                border_radius=RADIUS_MD,
                on_click=NexusState.fetch_available_calendars,
                loading=NexusState.calendars_loading,
                cursor="pointer",
            ),
            rx.link(
                rx.button(
                    "Open Settings",
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                    border_radius=RADIUS_MD,
                    cursor="pointer",
                ),
                href="/settings",
                _hover={"text_decoration": "none"},
            ),
            spacing="3",
            flex_wrap="wrap",
            width="100%",
        ),
        rx.text(
            "Booking tools like Calendly and Cal.com write directly to Google Calendar. Use Discover to pull visible IDs without leaving this form.",
            size="1",
            color=SUBTEXT,
            line_height="1.6",
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
                            align="start",
                            min_width="0",
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
                        width="100%",
                        padding="10px 12px",
                        border_radius=RADIUS_MD,
                        border=BORDER,
                        background=ACCENT_SOFT,
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.box(
                rx.hstack(
                    rx.icon("lightbulb", size=14, color=AMBER),
                    rx.text(
                        "Simple campaigns usually need one calendar. Switch to Advanced only when multiple booking calendars feed the same campaign.",
                        size="1",
                        color=SUBTEXT,
                        line_height="1.6",
                    ),
                    spacing="2",
                    align="start",
                ),
                padding="12px",
                border_radius=RADIUS_MD,
                background=AMBER_SOFT,
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
    )


def _advanced_calendar_row(entry) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.badge("Calendar Source", size="1", variant="soft", color_scheme="iris"),
            rx.spacer(),
            rx.button(
                rx.icon("trash-2", size=12),
                "Remove",
                size="1",
                variant="soft",
                color_scheme="red",
                border_radius=RADIUS_MD,
                on_click=NexusState.remove_form_calendar_entry(entry["key"].to(str)),
                cursor="pointer",
            ),
            width="100%",
            align="center",
        ),
        rx.vstack(
            rx.text("Calendar ID *", size="2", weight="medium", color=SUBTEXT),
            rx.input(
                value=entry["calendar_id"].to(str),
                on_change=lambda value: NexusState.set_form_calendar_entry_id(
                    entry["key"].to(str),
                    value,
                ),
                placeholder="primary or team-calendar@group.calendar.google.com",
                size="2",
                variant="surface",
                border_radius=RADIUS_MD,
                width="100%",
            ),
            rx.text(
                "Use 'primary' for the main calendar or paste a shared calendar ID.",
                size="1",
                color=SUBTEXT,
                font_style="italic",
            ),
            spacing="1",
            width="100%",
        ),
        rx.vstack(
            rx.text("Keyword Filter (optional)", size="2", weight="medium", color=SUBTEXT),
            rx.input(
                value=entry["filter"].to(str),
                on_change=lambda value: NexusState.set_form_calendar_entry_filter(
                    entry["key"].to(str),
                    value,
                ),
                placeholder="e.g. Worldcoin",
                size="2",
                variant="surface",
                border_radius=RADIUS_MD,
                width="100%",
            ),
            rx.text(
                "Only events whose title or attendee name contains this text will sync from this calendar.",
                size="1",
                color=SUBTEXT,
                font_style="italic",
            ),
            spacing="1",
            width="100%",
        ),
        spacing="3",
        width="100%",
        padding="16px",
        border_radius=RADIUS_MD,
        border=BORDER,
        background=ACCENT_SOFT,
    )


def _calendar_configuration_section() -> rx.Component:
    return glass_card(
        section_header(
            "calendar",
            "Calendar Configuration",
            "Keep simple campaigns fast, or switch to Advanced when one campaign pulls from multiple booking calendars.",
        ),
        rx.hstack(
            rx.button(
                "Simple setup",
                size="2",
                variant=rx.cond(
                    NexusState.form_calendar_mode == "simple",
                    "solid",
                    "soft",
                ),
                color_scheme="iris",
                border_radius=RADIUS_MD,
                on_click=NexusState.set_form_calendar_mode("simple"),
                cursor="pointer",
            ),
            rx.button(
                "Advanced multi-calendar",
                size="2",
                variant=rx.cond(
                    NexusState.form_calendar_mode == "advanced",
                    "solid",
                    "soft",
                ),
                color_scheme="gray",
                border_radius=RADIUS_MD,
                on_click=NexusState.set_form_calendar_mode("advanced"),
                cursor="pointer",
            ),
            spacing="3",
            flex_wrap="wrap",
            margin_bottom="16px",
        ),
        rx.cond(
            NexusState.form_calendar_mode == "simple",
            rx.vstack(
                form_field(
                    "Calendar ID",
                    NexusState.form_calendar_id,
                    NexusState.set_form_calendar_id,
                    "primary",
                    helper="Use 'primary' for your main calendar, or paste a shared calendar ID.",
                ),
                form_field(
                    "Keyword Filter (optional)",
                    NexusState.form_calendar_filter,
                    NexusState.set_form_calendar_filter,
                    "e.g. Worldcoin",
                    helper="Only sync events whose title contains this keyword.",
                ),
                spacing="3",
                width="100%",
            ),
            rx.vstack(
                rx.box(
                    rx.text(
                        "Advanced mode syncs every listed calendar. Blank rows are ignored, and duplicate calendar IDs are blocked so a campaign never double-imports the same source.",
                        size="1",
                        color=SUBTEXT,
                        line_height="1.6",
                    ),
                    padding="12px",
                    border_radius=RADIUS_MD,
                    background=AMBER_SOFT,
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(
                        NexusState.form_calendar_entries,
                        _advanced_calendar_row,
                    ),
                    spacing="3",
                    width="100%",
                ),
                rx.button(
                    rx.icon("plus", size=14),
                    "Add Another Calendar",
                    size="2",
                    variant="soft",
                    color_scheme="iris",
                    border_radius=RADIUS_MD,
                    on_click=NexusState.add_form_calendar_entry,
                    cursor="pointer",
                    align_self="start",
                ),
                spacing="3",
                width="100%",
            ),
        ),
        rx.box(
            _calendar_discovery_hint(),
            margin_top="16px",
        ),
        margin_bottom="24px",
    )


# -- Page
def new_campaign_page() -> rx.Component:
    return rx.box(
        # -- back link
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
            margin_bottom="24px",
        ),
        # -- title
        rx.heading(
            "Create New Campaign",
            size="7",
            weight="bold",
            color=HEADING,
            margin_bottom="8px",
        ),
        rx.text(
            "Set up a collection campaign with calendar integration, "
            "tracking links, and booking-page support.",
            size="3",
            color=TEXT,
            margin_bottom="32px",
            line_height="1.5",
        ),
        # -- error
        rx.cond(
            NexusState.form_error != "",
            rx.callout(
                NexusState.form_error,
                icon="triangle-alert",
                color_scheme="red",
                border_radius=RADIUS_MD,
                margin_bottom="16px",
            ),
        ),
        rx.cond(
            NexusState.admin_mode,
            rx.fragment(
                # -- Section 1: Campaign Details
                glass_card(
                    section_header(
                        "file-text",
                        "Campaign Details",
                        "Give your campaign a name and a brief description",
                    ),
                    rx.vstack(
                        form_field("Campaign Name *", NexusState.form_name,
                               NexusState.set_form_name,
                               "e.g. Q1 Berlin Sprint"),
                        form_field("Description", NexusState.form_description,
                               NexusState.set_form_description,
                               "What\'s the goal of this campaign?", area=True),
                        spacing="3",
                        width="100%",
                    ),
                    margin_bottom="16px",
                ),
                # -- Section 2: Goal & Timeline
                glass_card(
                    section_header(
                        "target",
                        "Goal & Timeline",
                        "Set a participant goal, deadline, and connect booking tools",
                    ),
                    rx.vstack(
                        form_field("Collection Goal", NexusState.form_goal,
                               NexusState.set_form_goal,
                               "100",
                               helper="Target number of completed participants"),
                        rx.vstack(
                            rx.text("Deadline (optional)", size="2", weight="medium", color=SUBTEXT),
                            rx.el.input(
                                type="date",
                                default_value=NexusState.form_deadline,
                                on_change=NexusState.set_form_deadline,
                                style={
                                    "width": "100%",
                                    "padding": "8px 12px",
                                    "border_radius": RADIUS_MD,
                                    "border": "1px solid rgba(255,255,255,0.1)",
                                    "background": "rgba(255,255,255,0.04)",
                                    "color": "inherit",
                                    "font_size": "14px",
                                    "outline": "none",
                                    "color_scheme": "dark",
                                },
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        form_field("Booking Page URL", NexusState.form_booking_url,
                               NexusState.set_form_booking_url,
                               "https://calendly.com/...",
                               helper="Calendly / Cal.com / Acuity - events auto-sync via Google Calendar"),
                        spacing="3",
                        width="100%",
                    ),
                    margin_bottom="16px",
                ),
                # -- Section 3: External Links
                glass_card(
                    section_header(
                        "link",
                        "External Links",
                        "Connect your Notion page and Linear project",
                    ),
                    rx.vstack(
                        form_field("Notion Page URL", NexusState.form_notion_url,
                               NexusState.set_form_notion_url,
                               "https://notion.so/..."),
                        form_field("Linear Project URL", NexusState.form_linear_url,
                               NexusState.set_form_linear_url,
                               "https://linear.app/..."),
                        spacing="3",
                        width="100%",
                    ),
                    margin_bottom="16px",
                ),
                # -- Section 4: Calendar Config
                _calendar_configuration_section(),
                # -- Section 5: Device Configuration
                glass_card(
                    section_header(
                        "monitor-smartphone",
                        "Device Configuration",
                        "Select the platforms for this campaign and configure defaults",
                    ),
                    rx.vstack(
                        rx.vstack(
                            rx.text("Platforms *", size="2", weight="medium", color=SUBTEXT),
                            rx.text(
                                "Select one or more platforms this campaign will collect on.",
                                size="1", color=SUBTEXT, font_style="italic",
                            ),
                            rx.flex(
                                rx.foreach(
                                    NexusState.platform_options,
                                    lambda opt: rx.box(
                                        rx.hstack(
                                            rx.icon(
                                                rx.cond(opt.selected, "check-square", "square"),
                                                size=16,
                                                color=rx.cond(opt.selected, ACCENT, SUBTEXT),
                                            ),
                                            rx.text(opt.name, size="2", color=TEXT),
                                            spacing="2",
                                            align="center",
                                        ),
                                        padding="6px 12px",
                                        border_radius=RADIUS_SM,
                                        border=rx.cond(
                                            opt.selected,
                                            "1px solid " + ACCENT,
                                            BORDER,
                                        ),
                                        background=rx.cond(
                                            opt.selected,
                                            ACCENT_SOFT,
                                            "transparent",
                                        ),
                                        cursor="pointer",
                                        on_click=NexusState.set_form_device_type(opt.name),
                                    ),
                                ),
                                flex_wrap="wrap",
                                gap="8px",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.text(
                            "Device quotas can be configured after creation via Edit.",
                            size="1",
                            color=SUBTEXT,
                            font_style="italic",
                        ),
                        rx.vstack(
                            rx.text("Default Platform (optional)", size="2", weight="medium", color=SUBTEXT),
                            rx.select(
                                NexusState.form_default_platform_options,
                                value=NexusState.form_default_platform_display,
                                on_change=NexusState.set_form_default_platform,
                                placeholder="None (set manually)",
                                size="2",
                                variant="surface",
                            ),
                            rx.text(
                                NexusState.form_default_platform_helper,
                                size="1",
                                color=SUBTEXT,
                                font_style="italic",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("Default Model Tag (optional)", size="2", weight="medium", color=SUBTEXT),
                            rx.select(
                                NexusState.form_default_model_tag_options,
                                value=NexusState.form_default_model_tag_display,
                                on_change=NexusState.set_form_default_model_tag,
                                placeholder="None (set manually)",
                                size="2",
                                variant="surface",
                            ),
                            rx.text(
                                NexusState.form_default_model_tag_helper,
                                size="1",
                                color=SUBTEXT,
                                font_style="italic",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    margin_bottom="24px",
                ),
                # -- Buttons
                rx.hstack(
                    rx.link(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                            size="3",
                            border_radius=RADIUS_MD,
                            cursor="pointer",
                        ),
                        href="/",
                    ),
                    rx.button(
                        rx.icon("plus", size=16),
                        "Create Campaign",
                        size="3",
                        color_scheme="iris",
                        border_radius=RADIUS_MD,
                        cursor="pointer",
                        on_click=NexusState.create_campaign,
                        background=ACCENT_GRADIENT,
                    ),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
            ),
            _admin_locked_panel(),
        ),
        max_width=MAX_WIDTH_NARROW,
        margin="0 auto",
        padding_x=PAGE_PADDING_X,
        padding_top="100px",
        padding_bottom=PAGE_PADDING_BOTTOM,
        min_height="100vh",
    )
