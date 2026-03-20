"""Participant row - table-style row with checkbox for bulk selection."""

import reflex as rx

from ..state import NexusState
from ..components.design_tokens import (
    ACCENT,
    ACCENT_SOFT,
    AMBER,
    BORDER,
    BORDER_SUBTLE,
    CARD_BG,
    HEADING,
    RADIUS_MD,
    RADIUS_SM,
    RED,
    RED_SOFT,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    TRANSITION_FAST,
    status_dot,
)


def participant_row(p: dict) -> rx.Component:
    eid = p["google_event_id"].to(str)
    name = p["name"].to(str)
    email = p["email"].to(str)
    time = p["appointment_time"].to(str)
    date = p["appointment_date"].to(str)
    platform = p["platform"].to(str)
    model_tag = p["model_tag"].to(str)
    status = p["status"].to(str)
    notes = p["notes"].to(str)
    issue_comment = p["issue_comment"].to(str)

    has_issue = issue_comment != ""
    is_completed = status == "Completed"

    return rx.box(
        # ── Main row (never wraps)
        rx.hstack(
            # Completion checkbox
            rx.checkbox(
                checked=is_completed,
                on_change=lambda _v: NexusState.toggle_completed(eid),
                size="2",
                color_scheme="green",
                cursor="pointer",
                flex_shrink="0",
            ),
            # Date + time chip
            rx.center(
                rx.text(
                    date + " " + time,
                    size="1",
                    weight="bold",
                    color=ACCENT,
                    font_variant_numeric="tabular-nums",
                    white_space="nowrap",
                ),
                padding="3px 8px",
                border_radius=RADIUS_SM,
                background=ACCENT_SOFT,
                flex_shrink="0",
                min_width="110px",
            ),
            # Name / email — grows, truncates
            rx.vstack(
                rx.text(
                    name,
                    size="2",
                    weight="medium",
                    color=rx.cond(is_completed, SUBTEXT, HEADING),
                    white_space="nowrap",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    max_width="100%",
                    text_decoration=rx.cond(is_completed, "line-through", "none"),
                ),
                rx.cond(
                    email != "",
                    rx.text(
                        email,
                        size="1",
                        color=SUBTEXT,
                        white_space="nowrap",
                        overflow="hidden",
                        text_overflow="ellipsis",
                        max_width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="0",
                flex="1",
                min_width="0",
                overflow="hidden",
            ),
            # Selects — fixed, never shrink
            rx.select(
                NexusState.platforms,
                value=platform,
                placeholder="Platform",
                on_change=lambda v: NexusState.set_platform(eid, v),
                size="1",
                variant="soft",
                flex_shrink="0",
            ),
            rx.select(
                NexusState.all_model_tags,
                value=model_tag,
                placeholder="Model",
                on_change=lambda v: NexusState.set_model_tag(eid, v),
                size="1",
                variant="soft",
                flex_shrink="0",
            ),
            # Edit button
            rx.icon_button(
                rx.icon("pencil", size=13),
                size="1",
                variant="ghost",
                color_scheme="iris",
                on_click=NexusState.open_edit_participant(eid),
                cursor="pointer",
                flex_shrink="0",
                _hover={"background": ACCENT_SOFT},
            ),
            # Delete button
            rx.icon_button(
                rx.icon("trash-2", size=13),
                size="1",
                variant="ghost",
                color_scheme="red",
                on_click=NexusState.open_delete_participant(eid),
                cursor="pointer",
                flex_shrink="0",
                _hover={"background": RED_SOFT},
            ),
            spacing="3",
            align="center",
            width="100%",
            overflow="hidden",
        ),
        # ── Notes row (inline, no extra icon)
        rx.box(
            rx.el.input(
                default_value=notes,
                placeholder="Add notes...",
                on_blur=lambda e: NexusState.set_notes(eid, e),
                style={
                    "width": "100%",
                    "padding": "5px 10px",
                    "border_radius": RADIUS_SM,
                    "border": "1px solid rgba(255,255,255,0.07)",
                    "font_size": "12px",
                    "outline": "none",
                    "background": "rgba(255,255,255,0.03)",
                    "color": "inherit",
                },
            ),
            padding_top="10px",
            margin_top="10px",
            border_top=BORDER_SUBTLE,
        ),
        # ── Card chrome
        padding="14px 16px",
        width="100%",
        border_radius=RADIUS_MD,
        background=CARD_BG,
        border=rx.cond(has_issue, f"1px solid {AMBER}", BORDER),
        backdrop_filter="blur(16px) saturate(180%)",
        box_shadow=SHADOW_SM,
        transition=TRANSITION_FAST,
        _hover={
            "border_color": rx.color_mode_cond(
                light="rgba(99,102,241,0.15)",
                dark="rgba(139,92,246,0.22)",
            ),
        },
    )
