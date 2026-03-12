"""Campaign card — glass card with gradient accent stripe and dual progress bar."""

import reflex as rx

from .design_tokens import (
    ACCENT,
    ACCENT_GRADIENT_H,
    ACCENT_SOFT,
    AMBER,
    BORDER,
    CARD_BG,
    GREEN,
    HEADING,
    HOVER_LIFT,
    RADIUS_LG,
    RADIUS_SM,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    TRANSITION,
    campaign_status_indicator,
    dual_progress_bar,
)


def campaign_card(campaign: dict) -> rx.Component:
    cid = campaign["campaign_id"].to(str)
    name = campaign["name"].to(str)
    description = campaign["description"].to(str)
    status = campaign["status"].to(str)
    today_total = campaign["today_total"].to(int)
    today_completed = campaign["today_completed"].to(int)
    today_in_progress = campaign["today_in_progress"].to(int)

    # Overall progress (all dates, goal-based)
    goal = campaign["goal"].to(int)
    booked = campaign["booked"].to(int)
    completed_all = campaign["completed_all"].to(int)

    booked_pct = rx.cond(goal > 0, (booked * 100 / goal).to(int), 0)
    completed_pct = rx.cond(goal > 0, (completed_all * 100 / goal).to(int), 0)

    return rx.link(
        rx.box(
            # -- Gradient accent stripe at the top
            rx.box(
                width="100%",
                height="3px",
                background=ACCENT_GRADIENT_H,
                border_radius="16px 16px 0 0",
                opacity="0.7",
            ),
            rx.vstack(
                # -- Top: status + goal fraction
                rx.hstack(
                    campaign_status_indicator(status),
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
                rx.spacer(),
                # -- Dual progress bar (booked + completed vs goal)
                rx.vstack(
                    dual_progress_bar(booked_pct, completed_pct, height="8px"),
                    rx.hstack(
                        rx.hstack(
                            rx.box(
                                width="8px", height="3px",
                                border_radius="2px",
                                background=ACCENT_GRADIENT_H,
                            ),
                            rx.text(completed_all, " completed", size="1", color=SUBTEXT),
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
                # -- Today's activity pills
                rx.hstack(
                    rx.center(
                        rx.text(
                            "Today: ", today_completed, "/", today_total,
                            size="1", weight="medium", color=ACCENT,
                        ),
                        padding="2px 8px",
                        border_radius=RADIUS_SM,
                        background=ACCENT_SOFT,
                    ),
                    rx.cond(
                        today_in_progress > 0,
                        rx.hstack(
                            rx.box(
                                width="5px", height="5px",
                                border_radius="50%", bg=AMBER,
                            ),
                            rx.text(
                                today_in_progress, " active",
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
            border=BORDER,
            backdrop_filter="blur(16px) saturate(180%)",
            box_shadow=SHADOW_SM,
            min_height="260px",
            overflow="hidden",
            transition=TRANSITION,
            cursor="pointer",
            _hover={
                **HOVER_LIFT,
                "border_color": rx.color_mode_cond(
                    light="rgba(99,102,241,0.18)",
                    dark="rgba(139,92,246,0.25)",
                ),
            },
        ),
        href="/campaign/" + cid,
        _hover={"text_decoration": "none"},
        text_decoration="none",
    )
