"""Reusable stat card — fixed height, design-token styling."""

import reflex as rx

from .design_tokens import (
    ACCENT_SOFT,
    BORDER,
    CARD_BG,
    HEADING,
    RADIUS_LG,
    RADIUS_MD,
    SHADOW_SM,
    SUBTEXT,
    TRANSITION,
)


def stat_card(
    label: str,
    value,
    icon_name: str,
    accent: str = "#6366f1",
) -> rx.Component:
    """Compact stat card — use in a grid(columns='4') parent."""
    return rx.box(
        rx.hstack(
            # ── icon circle ───────────────────────────────────
            rx.center(
                rx.icon(icon_name, size=18, color=accent),
                width="40px",
                height="40px",
                border_radius=RADIUS_MD,
                background=ACCENT_SOFT,
                flex_shrink="0",
            ),
            # ── value / label ─────────────────────────────────
            rx.vstack(
                rx.text(
                    value,
                    size="5",
                    weight="bold",
                    color=HEADING,
                    font_variant_numeric="tabular-nums",
                    line_height="1",
                ),
                rx.text(
                    label,
                    size="1",
                    color=SUBTEXT,
                    weight="medium",
                    text_transform="uppercase",
                    letter_spacing="0.04em",
                ),
                spacing="1",
            ),
            spacing="3",
            align="center",
        ),
        padding="18px 20px",
        height="96px",
        display="flex",
        align_items="center",
        border_radius=RADIUS_LG,
        background=CARD_BG,
        border=BORDER,
        backdrop_filter="blur(16px) saturate(180%)",
        box_shadow=SHADOW_SM,
        transition=TRANSITION,
        flex="1",
        min_width="0",
    )
