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
    platform = p["platform"].to(str)
    model_tag = p["model_tag"].to(str)
    status = p["status"].to(str)
    notes = p["notes"].to(str)
    issue_comment = p["issue_comment"].to(str)

    has_issue = issue_comment != ""

    return rx.box(
        rx.hstack(
            # -- Checkbox for bulk selection
            rx.checkbox(
                checked=NexusState.selected_ids.contains(eid),
                on_change=lambda _v: NexusState.toggle_select(eid),
                size="2",
                color_scheme="iris",
                cursor="pointer",
                flex_shrink="0",
            ),
            # -- Status dot
            status_dot(status, size="8px"),
            # -- Issue indicator (!)
            rx.tooltip(
                rx.box(
                    rx.icon(
                        "alert-triangle",
                        size=14,
                        color=rx.cond(has_issue, RED, SUBTEXT),
                    ),
                    padding="4px",
                    border_radius=RADIUS_SM,
                    background=rx.cond(has_issue, RED_SOFT, "transparent"),
                    cursor="pointer",
                    on_click=NexusState.open_issue_editor(eid),
                    _hover={"opacity": "0.8"},
                    flex_shrink="0",
                ),
                content=rx.cond(
                    has_issue,
                    issue_comment,
                    "Flag issue",
                ),
            ),
            # -- Time chip
            rx.center(
                rx.text(
                    time,
                    size="1",
                    weight="bold",
                    color=ACCENT,
                    font_variant_numeric="tabular-nums",
                ),
                padding="3px 10px",
                border_radius=RADIUS_SM,
                background=ACCENT_SOFT,
                flex_shrink="0",
            ),
            # -- Name / email
            rx.vstack(
                rx.text(
                    name,
                    size="2",
                    weight="medium",
                    color=HEADING,
                ),
                rx.cond(
                    email != "",
                    rx.text(
                        email, size="1",
                        color=SUBTEXT,
                    ),
                    rx.fragment(),
                ),
                spacing="0",
                flex="1",
                min_width="0",
            ),
            # -- Selects (using dynamic labels from state)
            rx.select(
                NexusState.platforms,
                value=platform,
                placeholder="Platform",
                on_change=lambda v: NexusState.set_platform(eid, v),
                size="1",
                variant="soft",
            ),
            rx.select(
                NexusState.model_tags,
                value=model_tag,
                placeholder="Model",
                on_change=lambda v: NexusState.set_model_tag(eid, v),
                size="1",
                variant="soft",
            ),
            rx.select(
                NexusState.statuses,
                value=status,
                on_change=lambda v: NexusState.set_status(eid, v),
                size="1",
                variant="soft",
            ),
            spacing="3",
            align="center",
            width="100%",
            flex_wrap="wrap",
        ),
        # -- Notes input — use default_value + on_blur for uncontrolled mode
        #    (fixes the "notes box not responsive" bug)
        rx.box(
            rx.hstack(
                rx.icon(
                    "message-square", size=11,
                    color=SUBTEXT,
                    flex_shrink="0",
                    margin_top="5px",
                ),
                rx.el.input(
                    default_value=notes,
                    placeholder="Add notes...",
                    on_blur=lambda e: NexusState.set_notes(eid, e.target.value),
                    style={
                        "width": "100%",
                        "padding": "6px 10px",
                        "border_radius": RADIUS_SM,
                        "border": "1px solid rgba(0,0,0,0.06)",
                        "font_size": "13px",
                        "outline": "none",
                        "background": "transparent",
                        "color": "inherit",
                    },
                ),
                spacing="2",
                align="start",
                width="100%",
            ),
            padding_top="10px",
            margin_top="10px",
            border_top=BORDER_SUBTLE,
        ),
        # -- Card chrome — fixed min_height for consistent sizing
        padding="16px 18px",
        min_height="110px",
        border_radius=RADIUS_MD,
        background=CARD_BG,
        border=rx.cond(
            has_issue,
            f"1px solid {AMBER}",
            BORDER,
        ),
        backdrop_filter="blur(16px) saturate(180%)",
        box_shadow=SHADOW_SM,
        transition=TRANSITION_FAST,
        _hover={
            "border_color": rx.color_mode_cond(
                light="rgba(99,102,241,0.12)",
                dark="rgba(139,92,246,0.18)",
            ),
            "box_shadow": rx.color_mode_cond(
                light="0 2px 10px rgba(0,0,0,0.03)",
                dark="0 2px 10px rgba(0,0,0,0.12)",
            ),
        },
    )
