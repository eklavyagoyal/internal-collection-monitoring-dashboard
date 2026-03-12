"""Edit-campaign page - pre-populates the shared form fields."""

import reflex as rx

from ..state import NexusState
from ..components.design_tokens import (
    ACCENT,
    ACCENT_GRADIENT,
    HEADING,
    MAX_WIDTH_NARROW,
    PAGE_PADDING_BOTTOM,
    PAGE_PADDING_X,
    RADIUS_MD,
    RADIUS_SM,
    SUBTEXT,
    TEXT,
    form_field,
    glass_card,
    section_header,
)


def edit_campaign_page() -> rx.Component:
    return rx.box(
        # -- back link
        rx.hstack(
            rx.link(
                rx.hstack(
                    rx.icon("arrow-left", size=16),
                    rx.text("Back to Campaign", size="2"),
                    spacing="2",
                    align="center",
                    color=SUBTEXT,
                    _hover={"color": ACCENT},
                ),
                href=rx.cond(
                    NexusState.form_edit_campaign_id != "",
                    "/campaign/" + NexusState.form_edit_campaign_id,
                    "/",
                ),
            ),
            margin_bottom="24px",
        ),
        # -- title
        rx.heading(
            "Edit Campaign",
            size="7",
            weight="bold",
            color=HEADING,
            margin_bottom="8px",
        ),
        rx.text(
            "Update the details, links, and calendar configuration.",
            size="3",
            color=TEXT,
            margin_bottom="32px",
        ),
        # -- error banner
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
        # -- Section 1: Details
        glass_card(
            section_header(
                "file-text",
                "Campaign Details",
                "Name and description for this campaign",
            ),
            rx.vstack(
                form_field("Campaign Name", NexusState.form_name,
                       NexusState.set_form_name, "e.g. Q1 Berlin Sprint"),
                form_field("Description", NexusState.form_description,
                       NexusState.set_form_description,
                       "Brief description...", area=True),
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
                "Collection target, deadline, and booking page",
            ),
            rx.vstack(
                form_field("Collection Goal", NexusState.form_goal,
                       NexusState.set_form_goal,
                       "100"),
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
                        },
                    ),
                    spacing="1",
                    width="100%",
                ),
                form_field("Booking Page URL", NexusState.form_booking_url,
                       NexusState.set_form_booking_url,
                       "https://calendly.com/..."),
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
                "Notion page and Linear project for this campaign",
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
                "Google Calendar ID and keyword filter",
            ),
            rx.vstack(
                form_field("Calendar ID", NexusState.form_calendar_id,
                       NexusState.set_form_calendar_id,
                       "primary"),
                form_field("Keyword Filter", NexusState.form_calendar_filter,
                       NexusState.set_form_calendar_filter,
                       "e.g. Worldcoin"),
                rx.text(
                    "Tip: Go to Settings -> Discover Calendars to find your Calendar IDs.",
                    size="1",
                    color=SUBTEXT,
                    font_style="italic",
                ),
                spacing="3",
                width="100%",
            ),
            margin_bottom="24px",
        ),
        # -- Action buttons
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
                href=rx.cond(
                    NexusState.form_edit_campaign_id != "",
                    "/campaign/" + NexusState.form_edit_campaign_id,
                    "/",
                ),
            ),
            rx.button(
                rx.icon("save", size=16),
                "Save Changes",
                size="3",
                color_scheme="iris",
                border_radius=RADIUS_MD,
                cursor="pointer",
                on_click=NexusState.save_campaign,
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
