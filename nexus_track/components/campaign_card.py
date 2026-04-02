"""Campaign card — compact and scannable for the dashboard grid."""

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


def _sync_state_tone(sync_state) -> tuple[str, str]:
    background = rx.cond(
        sync_state == "fresh",
        GREEN_SOFT,
        rx.cond(
            sync_state == "stale",
            AMBER_SOFT,
            rx.cond(sync_state == "failed", RED_SOFT, ACCENT_SOFT),
        ),
    )
    color = rx.cond(
        sync_state == "fresh",
        GREEN,
        rx.cond(sync_state == "stale", AMBER, rx.cond(sync_state == "failed", RED, ACCENT)),
    )
    return background, color


def campaign_card(campaign: dict) -> rx.Component:
    cid = campaign["campaign_id"].to(str)
    name = campaign["name"].to(str)
    description = campaign["description"].to(str)
    status = campaign["status"].to(str)
    today_total = campaign["today_total"].to(int)
    today_completed = campaign["today_completed"].to(int)
    today_booked = campaign["today_booked"].to(int)
    goal = campaign["goal"].to(int)
    booked = campaign["booked"].to(int)
    completed_all = campaign["completed_all"].to(int)
    device_types_display = campaign["device_types_display"].to(str)
    sync_state = campaign["sync_health_state"].to(str)
    sync_background, sync_color = _sync_state_tone(sync_state)

    booked_pct = rx.cond(goal > 0, (booked * 100 / goal).to(int), 0)
    completed_pct = rx.cond(goal > 0, (completed_all * 100 / goal).to(int), 0)

    return rx.link(
        rx.box(
            rx.box(
                width="100%",
                height="2px",
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
                border_radius="14px 14px 0 0",
                opacity="0.8",
            ),
            rx.vstack(
                rx.hstack(
                    campaign_status_indicator(status),
                    rx.cond(
                        device_types_display != "",
                        rx.badge(
                            device_types_display,
                            size="1",
                            variant="soft",
                            color_scheme="gray",
                        ),
                        rx.fragment(),
                    ),
                    rx.spacer(),
                    rx.cond(
                        campaign["sync_needs_attention"],
                        rx.badge(
                            "Needs attention",
                            size="1",
                            variant="soft",
                            color_scheme=rx.cond(sync_state == "failed", "red", "amber"),
                        ),
                        rx.badge(
                            campaign["sync_compact_label"],
                            size="1",
                            variant="soft",
                            color_scheme=rx.cond(sync_state == "fresh", "green", "gray"),
                        ),
                    ),
                    width="100%",
                    align="center",
                ),
                rx.vstack(
                    rx.text(
                        name,
                        size="4",
                        weight="bold",
                        color=HEADING,
                        line_height="1.2",
                        max_width="100%",
                    ),
                    rx.cond(
                        description != "",
                        rx.text(
                            description,
                            size="1",
                            color=TEXT,
                            max_height="32px",
                            overflow="hidden",
                            line_height="1.4",
                        ),
                        rx.fragment(),
                    ),
                    spacing="1",
                    align="start",
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            completed_all,
                            "/",
                            goal,
                            size="2",
                            weight="bold",
                            color=HEADING,
                            font_variant_numeric="tabular-nums",
                        ),
                        rx.text("goal", size="1", color=SUBTEXT),
                        rx.spacer(),
                        rx.text(
                            booked,
                            " booked",
                            size="1",
                            color=SUBTEXT,
                            font_variant_numeric="tabular-nums",
                        ),
                        spacing="1",
                        align="center",
                        width="100%",
                    ),
                    dual_progress_bar(booked_pct, completed_pct, height="8px"),
                    rx.hstack(
                        rx.text(
                            completed_all,
                            " done",
                            size="1",
                            color=ACCENT,
                            font_variant_numeric="tabular-nums",
                        ),
                        rx.text("·", size="1", color=SUBTEXT),
                        rx.text(
                            booked,
                            " total booked",
                            size="1",
                            color=SUBTEXT,
                            font_variant_numeric="tabular-nums",
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.hstack(
                    rx.hstack(
                        rx.text(
                            NexusState.dashboard_day_metric_label + ":",
                            size="1",
                            color=SUBTEXT,
                        ),
                        rx.text(
                            today_completed,
                            "/",
                            today_total,
                            size="1",
                            weight="bold",
                            color=ACCENT,
                            font_variant_numeric="tabular-nums",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.cond(
                        today_booked > 0,
                        rx.badge(
                            today_booked.to(str),
                            " booked",
                            size="1",
                            variant="soft",
                            color_scheme="amber",
                        ),
                        rx.fragment(),
                    ),
                    rx.spacer(),
                    width="100%",
                    align="center",
                    flex_wrap="wrap",
                ),
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text(
                                campaign["sync_compact_label"],
                                size="1",
                                weight="bold",
                                color=sync_color,
                            ),
                            rx.spacer(),
                            rx.text(
                                campaign["sync_compact_detail"],
                                size="1",
                                color=SUBTEXT,
                            ),
                            width="100%",
                            align="center",
                        ),
                        rx.cond(
                            campaign["sync_needs_attention"],
                            rx.text(
                                campaign["sync_secondary_message"],
                                size="1",
                                color=sync_color,
                                line_height="1.4",
                            ),
                            rx.fragment(),
                        ),
                        spacing="1",
                        width="100%",
                        align="start",
                    ),
                    padding="10px 12px",
                    border_radius=RADIUS_MD,
                    background=sync_background,
                    border=BORDER,
                    width="100%",
                ),
                spacing="3",
                align="start",
                width="100%",
                padding="13px 14px 14px 14px",
                min_height="244px",
            ),
            width="100%",
            height="100%",
            border_radius=RADIUS_LG,
            background=CARD_BG,
            border=BORDER,
            box_shadow=SHADOW_SM,
            transition=TRANSITION,
            overflow="hidden",
            _hover=HOVER_LIFT,
        ),
        href="/campaign/" + cid,
        _hover={"text_decoration": "none"},
        width="100%",
        display="block",
    )
