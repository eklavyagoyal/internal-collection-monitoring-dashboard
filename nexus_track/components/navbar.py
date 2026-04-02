"""Top navigation - compact bar with lightweight status and shortcuts."""

import reflex as rx

from .design_tokens import (
    ACCENT_GRADIENT,
    ACCENT_SOFT,
    AMBER,
    BORDER,
    HEADING,
    MAX_WIDTH,
    RADIUS_MD,
    RADIUS_SM,
    SUBTEXT,
    ghost_icon_btn,
)
from ..state import NexusState


def navbar(breadcrumb: str = "") -> rx.Component:
    """Sticky top bar. Pass breadcrumb='Campaign Name' for deeper pages."""
    return rx.box(
        rx.hstack(
            # -- Logo
                rx.link(
                    rx.hstack(
                        rx.center(
                            rx.icon("radio", size=16, color="white"),
                            width="30px",
                            height="30px",
                            border_radius=RADIUS_SM,
                            background=ACCENT_GRADIENT,
                            flex_shrink="0",
                        ),
                        rx.text(
                            "Nexus",
                            size="3",
                            weight="bold",
                            color=HEADING,
                            letter_spacing="-0.04em",
                        ),
                        rx.text(
                            "Track",
                            size="3",
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
                # Admin badge
                rx.cond(
                    NexusState.admin_mode,
                    rx.hstack(
                        rx.box(
                            width="5px", height="5px",
                            border_radius="50%", bg=AMBER,
                        ),
                        rx.text(
                            "Admin", size="1", weight="medium",
                            color=AMBER,
                        ),
                        spacing="2", align="center",
                        cursor="pointer",
                        on_click=NexusState.logout_admin,
                        title="Click to logout",
                    ),
                ),
                # New campaign shortcut
                rx.link(
                    ghost_icon_btn("plus", icon_size=16, button_size="2"),
                    href="/new",
                    title="New Campaign",
                    display="flex",
                    align_items="center",
                ),
                # Settings link
                rx.link(
                    ghost_icon_btn("settings", icon_size=16, button_size="2"),
                    href="/settings",
                    title="Settings",
                    display="flex",
                    align_items="center",
                ),
                # Theme toggle
                rx.icon_button(
                    rx.color_mode_cond(
                        light=rx.icon("moon", size=16),
                        dark=rx.icon("sun", size=16),
                    ),
                    on_click=rx.toggle_color_mode,
                    variant="ghost",
                    size="2",
                    cursor="pointer",
                    color=SUBTEXT,
                    _hover={
                        "background": ACCENT_SOFT,
                    },
                    border_radius=RADIUS_MD,
                ),
                spacing="2", align="center",
            ),
            justify="between",
            align="center",
            width="100%",
            max_width=MAX_WIDTH,
            margin_x="auto",
            padding_x="20px",
        ),
        height="54px",
        display="flex",
        align_items="center",
        background=rx.color_mode_cond(
            light="rgba(255,255,255,0.92)",
            dark="rgba(11,15,26,0.94)",
        ),
        backdrop_filter="blur(6px) saturate(115%)",
        border_bottom=BORDER,
        width="100%",
        position="sticky",
        top="0",
        z_index="50",
    )
