"""Campaign card — glass card with gradient accent stripe and dual progress bar."""

import reflex as rx

from ..state import NexusState
from .design_tokens import (
    ACCENT,
    ACCENT_GRADIENT_H,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
    BORDER,
    CARD_BG,
    GREEN,
    GREEN_SOFT,
    HEADING,
    HOVER_LIFT,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
    RED,
    RED_SOFT,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    TRANSITION,
    campaign_status_indicator,
    dual_progress_bar,
)


def _sync_meta_item(label: str, value) -> rx.Component:
    return rx.vstack(
        rx.text(
            label,
            size="1",
            color=SUBTEXT,
            text_transform="uppercase",
            letter_spacing="0.04em",
        ),
        rx.text(
            value,
            size="1",
            weight="medium",
            color=HEADING,
            line_height="1.3",
        ),
        spacing="1",
        align="start",
        min_width="0",
    )


def _sync_health_panel(campaign: dict) -> rx.Component:
    sync_state = campaign["sync_health_state"].to(str)
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.box(
                        width="7px",
                        height="7px",
                        border_radius="50%",
                        background=rx.cond(
                            sync_state == "fresh",
                            GREEN,
                            rx.cond(
                                sync_state == "stale",
                                AMBER,
                                rx.cond(
                                    sync_state == "failed",
                                    RED,
                                    SUBTEXT,
                                ),
                            ),
                        ),
                    ),
                    rx.text(
                        campaign["sync_health_label"],
                        size="1",
                        weight="bold",
                        color=HEADING,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.spacer(),
                rx.cond(
                    campaign["sync_needs_attention"],
                    rx.badge(
                        "Check sync",
                        size="1",
                        variant="soft",
                        color_scheme=rx.cond(
                            sync_state == "failed",
                            "red",
                            "amber",
                        ),
                    ),
                    rx.fragment(),
                ),
                width="100%",
                align="center",
            ),
            rx.text(
                campaign["sync_primary_message"],
                size="1",
                color=TEXT,
                line_height="1.55",
            ),
            rx.cond(
                campaign["sync_secondary_message"] != "",
                rx.text(
                    campaign["sync_secondary_message"],
                    size="1",
                    color=rx.cond(
                        sync_state == "failed",
                        RED,
                        rx.cond(
                            sync_state == "stale",
                            AMBER,
                            SUBTEXT,
                        ),
                    ),
                    line_height="1.55",
                ),
                rx.fragment(),
            ),
            rx.hstack(
                rx.cond(
                    campaign["sync_show_last_attempt"],
                    _sync_meta_item("Attempted", campaign["sync_last_attempt_display"]),
                    rx.fragment(),
                ),
                _sync_meta_item("Successful", campaign["sync_last_success_display"]),
                spacing="3",
                align="start",
                width="100%",
                flex_wrap="wrap",
            ),
            spacing="2",
            width="100%",
            align="start",
        ),
        padding="12px",
        border_radius=RADIUS_MD,
        background=rx.cond(
            sync_state == "fresh",
            GREEN_SOFT,
            rx.cond(
                sync_state == "stale",
                AMBER_SOFT,
                rx.cond(
                    sync_state == "failed",
                    RED_SOFT,
                    ACCENT_SOFT,
                ),
            ),
        ),
        border=rx.cond(
            sync_state == "fresh",
            "1px solid rgba(34,197,94,0.16)",
            rx.cond(
                sync_state == "stale",
                "1px solid rgba(245,158,11,0.18)",
                rx.cond(
                    sync_state == "failed",
                    "1px solid rgba(239,68,68,0.18)",
                    "1px solid rgba(148,163,184,0.16)",
                ),
            ),
        ),
        width="100%",
    )


def campaign_card(campaign: dict) -> rx.Component:
    cid = campaign["campaign_id"].to(str)
    name = campaign["name"].to(str)
    description = campaign["description"].to(str)
    status = campaign["status"].to(str)
    today_total = campaign["today_total"].to(int)
    today_completed = campaign["today_completed"].to(int)
    today_booked = campaign["today_booked"].to(int)

    # Overall progress (all dates, goal-based)
    goal = campaign["goal"].to(int)
    booked = campaign["booked"].to(int)
    completed_all = campaign["completed_all"].to(int)
    device_types_display = campaign["device_types_display"].to(str)
    sync_state = campaign["sync_health_state"].to(str)

    booked_pct = rx.cond(goal > 0, (booked * 100 / goal).to(int), 0)
    completed_pct = rx.cond(goal > 0, (completed_all * 100 / goal).to(int), 0)

    return rx.link(
        rx.box(
            # -- Gradient accent stripe at the top
            rx.box(
                width="100%",
                height="3px",
                background=rx.cond(
                    sync_state == "failed",
                    "linear-gradient(90deg, #ef4444, #f97316)",
                    rx.cond(
                        sync_state == "stale",
                        "linear-gradient(90deg, #f59e0b, #f97316)",
                        rx.cond(
                            sync_state == "never",
                            "linear-gradient(90deg, #94a3b8, #cbd5e1)",
                            ACCENT_GRADIENT_H,
                        ),
                    ),
                ),
                border_radius="16px 16px 0 0",
                opacity="0.7",
            ),
            rx.vstack(
                # -- Top: status + device types + goal fraction
                rx.hstack(
                    campaign_status_indicator(status),
                    rx.cond(
                        device_types_display != "",
                        rx.badge(
                            device_types_display,
                            size="1",
                            variant="soft",
                            color_scheme="blue",
                        ),
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.text(
                            completed_all, "/", goal,
                            size="1", weight="bold",
                            color=ACCENT,
                            font_variant_numeric="tabular-nums",
                        ),
                        rx.text(
                            "goal",
                            size="1",
                            color=SUBTEXT,
                        ),
                        spacing="1",
                        align="center",
                    ),
                    width="100%", align="center",
                ),
                # -- Campaign name
                rx.text(
                    name,
                    size="3", weight="bold",
                    color=HEADING,
                    line_height="1.3",
                ),
                # -- Dual progress bar directly under title
                rx.vstack(
                    dual_progress_bar(booked_pct, completed_pct, height="10px"),
                    rx.hstack(
                        rx.hstack(
                            rx.box(
                                width="8px", height="3px",
                                border_radius="2px",
                                background=ACCENT_GRADIENT_H,
                            ),
                            rx.text(completed_all, " done", size="1", color=SUBTEXT),
                            spacing="1", align="center",
                        ),
                        rx.hstack(
                            rx.box(
                                width="8px", height="3px",
                                border_radius="2px",
                                background=ACCENT_SOFT,
                            ),
                            rx.text(booked, " booked", size="1", color=SUBTEXT),
                            spacing="1", align="center",
                        ),
                        spacing="3",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # -- Description (2 lines max)
                rx.cond(
                    description != "",
                    rx.text(
                        description,
                        size="2",
                        color=TEXT,
                        max_height="40px",
                        overflow="hidden",
                        line_height="1.45",
                    ),
                    rx.fragment(),
                ),
                _sync_health_panel(campaign),
                rx.spacer(),
                # -- Today's activity pills
                rx.hstack(
                    rx.center(
                        rx.text(
                            NexusState.dashboard_day_metric_label, ": ", today_completed, "/", today_total,
                            size="1", weight="medium", color=ACCENT,
                        ),
                        padding="2px 8px",
                        border_radius=RADIUS_SM,
                        background=ACCENT_SOFT,
                    ),
                    rx.cond(
                        today_booked > 0,
                        rx.hstack(
                            rx.box(
                                width="5px", height="5px",
                                border_radius="50%", bg=AMBER,
                            ),
                            rx.text(
                                today_booked, " booked",
                                size="1", color=AMBER,
                            ),
                            spacing="1", align="center",
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                ),
                spacing="3",
                height="100%",
                padding="20px 22px 22px",
            ),
            # -- Card chrome
            border_radius=RADIUS_LG,
            background=CARD_BG,
            border=rx.cond(
                sync_state == "failed",
                "1px solid rgba(239,68,68,0.18)",
                rx.cond(
                    sync_state == "stale",
                    "1px solid rgba(245,158,11,0.18)",
                    rx.cond(
                        sync_state == "never",
                        "1px solid rgba(148,163,184,0.18)",
                        BORDER,
                    ),
                ),
            ),
            backdrop_filter="blur(16px) saturate(180%)",
            box_shadow=rx.cond(
                sync_state == "failed",
                "0 10px 24px rgba(239,68,68,0.10)",
                rx.cond(
                    sync_state == "stale",
                    "0 10px 24px rgba(245,158,11,0.10)",
                    SHADOW_SM,
                ),
            ),
            min_height="340px",
            overflow="hidden",
            transition=TRANSITION,
            cursor="pointer",
            _hover={
                **HOVER_LIFT,
                "border_color": rx.cond(
                    sync_state == "failed",
                    "rgba(239,68,68,0.28)",
                    rx.cond(
                        sync_state == "stale",
                        "rgba(245,158,11,0.28)",
                        rx.color_mode_cond(
                            light="rgba(99,102,241,0.18)",
                            dark="rgba(139,92,246,0.25)",
                        ),
                    ),
                ),
            },
        ),
        href="/campaign/" + cid,
        _hover={"text_decoration": "none"},
        text_decoration="none",
    )
