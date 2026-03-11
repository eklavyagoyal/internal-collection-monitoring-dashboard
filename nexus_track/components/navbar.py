"""Top navigation - frosted-glass bar with logo, nav, breadcrumb support."""

import reflex as rx

from .design_tokens import (
    ACCENT,
    ACCENT_GRADIENT,
    ACCENT_SOFT,
    BG,
    BORDER,
    HEADING,
    RADIUS_MD,
    RADIUS_SM,
    SHADOW_SM,
    SUBTEXT,
    TRANSITION_FAST,
    ghost_icon_btn,
)


def navbar(breadcrumb: str = "") -> rx.Component:
    """Sticky top bar. Pass breadcrumb='Campaign Name' for deeper pages."""
    return rx.box(
        rx.hstack(
            # -- Logo
            rx.link(
                rx.hstack(
                    # gradient icon badge
                    rx.center(
                        rx.icon("radio", size=16, color="white"),
                        width="32px",
                        height="32px",
                        border_radius=RADIUS_SM,
                        background=ACCENT_GRADIENT,
                        box_shadow="0 2px 8px rgba(99,102,241,0.25)",
                        flex_shrink="0",
                    ),
                    rx.text(
                        "Nexus",
                        size="4",
                        weight="bold",
                        color=HEADING,
                        letter_spacing="-0.04em",
                    ),
                    rx.text(
                        "Track",
                        size="4",
                        weight="medium",
                        color=SUBTEXT,
                        letter_spacing="-0.04em",
                    ),
                    spacing="2",
                    align="center",
                ),
                href="/",
                _hover={"text_decoration": "none", "opacity": "0.82"},
                transition="opacity 0.15s ease",
            ),
            # -- Breadcrumb (optional)
            rx.cond(
                breadcrumb != "",
                rx.hstack(
                    rx.icon("chevron-right", size=14, color=SUBTEXT),
                    rx.text(
                        breadcrumb,
                        size="2",
                        color=SUBTEXT,
                        weight="medium",
                        max_width="200px",
                        overflow="hidden",
                        text_overflow="ellipsis",
                        white_space="nowrap",
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.fragment(),
            ),
            rx.spacer(),
            # -- Right controls
            rx.hstack(
                # Live indicator
                rx.hstack(
                    rx.box(
                        width="6px", height="6px",
                        border_radius="50%", bg="#22c55e",
                        class_name="pulse-dot",
                    ),
                    rx.text(
                        "Live", size="1", weight="medium",
                        color=SUBTEXT,
                    ),
                    spacing="2", align="center",
                ),
                # New campaign shortcut
                rx.link(
                    ghost_icon_btn("plus"),
                    href="/new",
                    title="New Campaign",
                ),
                # Settings link
                rx.link(
                    ghost_icon_btn("settings"),
                    href="/settings",
                    title="Settings",
                ),
                # Theme toggle
                rx.icon_button(
                    rx.color_mode_cond(
                        light=rx.icon("moon", size=14),
                        dark=rx.icon("sun", size=14),
                    ),
                    on_click=rx.toggle_color_mode,
                    variant="ghost",
                    size="1",
                    cursor="pointer",
                    color=SUBTEXT,
                    _hover={
                        "background": ACCENT_SOFT,
                    },
                    border_radius=RADIUS_SM,
                ),
                spacing="3", align="center",
            ),
            justify="between",
            align="center",
            width="100%",
            max_width="1200px",
            margin_x="auto",
            padding_x="24px",
        ),
        # -- Outer bar
        height="60px",
        display="flex",
        align_items="center",
        background=rx.color_mode_cond(
            light="rgba(255,255,255,0.72)",
            dark="rgba(11,15,26,0.72)",
        ),
        backdrop_filter="blur(20px) saturate(180%)",
        border_bottom=BORDER,
        width="100%",
        position="sticky",
        top="0",
        z_index="50",
    )
