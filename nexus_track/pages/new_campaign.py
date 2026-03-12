"""New-campaign page - create a campaign with all configurable fields."""

import reflex as rx

from ..state import NexusState
from ..components.design_tokens import (
    ACCENT,
    ACCENT_GRADIENT,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
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
        # -- Section 3: Calendar Config
        glass_card(
            section_header(
                "calendar",
                "Calendar Configuration",
                "Which Google Calendar holds the appointments for this campaign?",
            ),
            rx.vstack(
                form_field("Calendar ID", NexusState.form_calendar_id,
                       NexusState.set_form_calendar_id,
                       "primary",
                       helper="Use \'primary\' for your main calendar, or a specific calendar ID"),
                form_field("Keyword Filter (optional)", NexusState.form_calendar_filter,
                       NexusState.set_form_calendar_filter,
                       "e.g. Worldcoin",
                       helper="Only sync events whose title contains this keyword"),
                spacing="3",
                width="100%",
            ),
            rx.box(
                rx.hstack(
                    rx.icon("lightbulb", size=14, color=AMBER),
                    rx.text(
                        "Tip: Go to Settings -> Discover Calendars to find all "
                        "your Calendar IDs. Booking tools (Calendly, Cal.com) "
                        "write directly to Google Calendar.",
                        size="1",
                        color=SUBTEXT,
                    ),
                    spacing="2",
                    align="start",
                ),
                margin_top="12px",
                padding="12px",
                border_radius=RADIUS_MD,
                background=AMBER_SOFT,
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
        max_width=MAX_WIDTH_NARROW,
        margin="0 auto",
        padding_x=PAGE_PADDING_X,
        padding_top="100px",
        padding_bottom=PAGE_PADDING_BOTTOM,
        min_height="100vh",
    )
