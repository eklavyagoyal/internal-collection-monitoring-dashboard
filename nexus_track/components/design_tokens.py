"""
Nexus-Track — Centralized Design Tokens.

Every colour, radius, shadow, spacing, and glass-card style lives here.
Import from this module instead of defining ad-hoc rgba() strings.
"""

import reflex as rx

# ═══════════════════════════════════════════════════════════════════════════
# COLOUR PALETTE
# ═══════════════════════════════════════════════════════════════════════════

# ── Page backgrounds ──────────────────────────────────────────────────────
BG = rx.color_mode_cond(light="#f8fafc", dark="#0b0f1a")
BG_SUBTLE = rx.color_mode_cond(light="#f1f5f9", dark="#111827")

# ── Card / surface backgrounds ────────────────────────────────────────────
CARD_BG = rx.color_mode_cond(
    light="rgba(255,255,255,0.78)", dark="rgba(22,27,45,0.72)",
)
CARD_BG_SOLID = rx.color_mode_cond(light="white", dark="#161b2d")
CARD_BG_HOVER = rx.color_mode_cond(
    light="rgba(255,255,255,0.95)", dark="rgba(30,35,55,0.85)",
)

# ── Borders ───────────────────────────────────────────────────────────────
BORDER = rx.color_mode_cond(
    light="1px solid rgba(0,0,0,0.06)", dark="1px solid rgba(255,255,255,0.06)",
)
BORDER_SUBTLE = rx.color_mode_cond(
    light="1px solid rgba(0,0,0,0.03)", dark="1px solid rgba(255,255,255,0.03)",
)
BORDER_ACCENT = rx.color_mode_cond(
    light="1px solid rgba(99,102,241,0.2)", dark="1px solid rgba(139,92,246,0.25)",
)

# ── Text colours ──────────────────────────────────────────────────────────
HEADING = rx.color_mode_cond(light="#0f172a", dark="#f1f5f9")
TEXT = rx.color_mode_cond(light="#334155", dark="#cbd5e1")
SUBTEXT = rx.color_mode_cond(light="#94a3b8", dark="#64748b")
MUTED = rx.color_mode_cond(light="#cbd5e1", dark="#334155")

# ── Accent colours ────────────────────────────────────────────────────────
ACCENT = "#6366f1"
ACCENT_LIGHT = "#818cf8"
ACCENT_DARK = "#4f46e5"
ACCENT_SOFT = rx.color_mode_cond(
    light="rgba(99,102,241,0.08)", dark="rgba(99,102,241,0.15)",
)
ACCENT_GRADIENT = "linear-gradient(135deg, #6366f1 0%, #a78bfa 100%)"
ACCENT_GRADIENT_H = "linear-gradient(90deg, #6366f1, #a78bfa)"

# ── Status colours ────────────────────────────────────────────────────────
GREEN = "#22c55e"
GREEN_SOFT = rx.color_mode_cond(
    light="rgba(34,197,94,0.08)", dark="rgba(34,197,94,0.15)",
)
AMBER = "#f59e0b"
AMBER_SOFT = rx.color_mode_cond(
    light="rgba(245,158,11,0.08)", dark="rgba(245,158,11,0.15)",
)
RED = "#ef4444"
RED_SOFT = rx.color_mode_cond(
    light="rgba(239,68,68,0.08)", dark="rgba(239,68,68,0.15)",
)
BLUE = "#3b82f6"
BLUE_SOFT = rx.color_mode_cond(
    light="rgba(59,130,246,0.08)", dark="rgba(59,130,246,0.15)",
)
VIOLET = "#8b5cf6"
VIOLET_SOFT = rx.color_mode_cond(
    light="rgba(139,92,246,0.08)", dark="rgba(139,92,246,0.15)",
)

# ═══════════════════════════════════════════════════════════════════════════
# SHADOWS
# ═══════════════════════════════════════════════════════════════════════════

SHADOW_SM = rx.color_mode_cond(
    light="0 1px 3px rgba(0,0,0,0.04)", dark="0 1px 3px rgba(0,0,0,0.2)",
)
SHADOW_MD = rx.color_mode_cond(
    light="0 4px 16px rgba(0,0,0,0.06)", dark="0 4px 16px rgba(0,0,0,0.3)",
)
SHADOW_LG = rx.color_mode_cond(
    light="0 12px 36px rgba(0,0,0,0.08)", dark="0 12px 36px rgba(0,0,0,0.4)",
)
SHADOW_ACCENT = rx.color_mode_cond(
    light="0 4px 20px rgba(99,102,241,0.12)",
    dark="0 4px 20px rgba(99,102,241,0.2)",
)

# ═══════════════════════════════════════════════════════════════════════════
# RADII  &  SPACING
# ═══════════════════════════════════════════════════════════════════════════

RADIUS_SM = "8px"
RADIUS_MD = "12px"
RADIUS_LG = "16px"
RADIUS_XL = "20px"
RADIUS_FULL = "9999px"

MAX_WIDTH = "1200px"
MAX_WIDTH_NARROW = "720px"
PAGE_PADDING_X = "24px"
PAGE_PADDING_TOP = "100px"
PAGE_PADDING_BOTTOM = "80px"

# ═══════════════════════════════════════════════════════════════════════════
# TRANSITION
# ═══════════════════════════════════════════════════════════════════════════

TRANSITION = "all 0.2s cubic-bezier(0.4,0,0.2,1)"
TRANSITION_SLOW = "all 0.35s cubic-bezier(0.4,0,0.2,1)"
TRANSITION_FAST = "all 0.12s ease"

# ═══════════════════════════════════════════════════════════════════════════
# HOVER STYLES  (dict — spread into _hover)
# ═══════════════════════════════════════════════════════════════════════════

HOVER_LIFT = {
    "transform": "translateY(-3px)",
    "box_shadow": SHADOW_LG,
}

HOVER_GLOW = {
    "box_shadow": SHADOW_ACCENT,
}

HOVER_SUBTLE = {
    "background": rx.color_mode_cond(
        light="rgba(0,0,0,0.02)", dark="rgba(255,255,255,0.03)",
    ),
}

# ═══════════════════════════════════════════════════════════════════════════
# GLASS CARD  (reusable component)
# ═══════════════════════════════════════════════════════════════════════════


def glass_card(*children, **overrides) -> rx.Component:
    """Frosted-glass card — pass children + any prop overrides."""
    props = dict(
        padding="24px",
        border_radius=RADIUS_LG,
        background=CARD_BG,
        border=BORDER,
        backdrop_filter="blur(16px) saturate(180%)",
        box_shadow=SHADOW_SM,
        transition=TRANSITION,
    )
    props.update(overrides)
    return rx.box(*children, **props)


# ═══════════════════════════════════════════════════════════════════════════
# SHARED FORM HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def section_header(icon: str, title: str, subtitle: str) -> rx.Component:
    """Re-usable section header: icon badge + title + subtitle."""
    return rx.hstack(
        rx.center(
            rx.icon(icon, size=18, color=ACCENT),
            width="40px",
            height="40px",
            border_radius=RADIUS_MD,
            background=ACCENT_SOFT,
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(title, size="3", weight="bold", color=HEADING),
            rx.text(subtitle, size="2", color=SUBTEXT),
            spacing="1",
        ),
        spacing="3",
        align="center",
        margin_bottom="16px",
    )


def form_field(
    label: str, value, on_change, placeholder: str = "",
    area: bool = False, helper: str = "",
) -> rx.Component:
    """Shared form field with label, input/textarea, optional helper text."""
    inp = (
        rx.text_area(
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            size="2",
            resize="vertical",
            min_height="80px",
            border_radius=RADIUS_MD,
            variant="surface",
            width="100%",
        )
        if area
        else rx.input(
            value=value,
            on_change=on_change,
            placeholder=placeholder,
            size="2",
            variant="surface",
            border_radius=RADIUS_MD,
            width="100%",
        )
    )
    children: list[rx.Component] = [
        rx.text(label, size="2", weight="medium", color=SUBTEXT),
        inp,
    ]
    if helper:
        children.append(
            rx.text(helper, size="1", color=MUTED, font_style="italic")
        )
    return rx.vstack(*children, spacing="1", width="100%")


# ═══════════════════════════════════════════════════════════════════════════
# GHOST ICON BUTTON
# ═══════════════════════════════════════════════════════════════════════════

_GHOST_BTN_COLOR = rx.color_mode_cond(light="#64748b", dark="#94a3b8")
_GHOST_BTN_HOVER = {
    "background": rx.color_mode_cond(
        light="rgba(0,0,0,0.05)", dark="rgba(255,255,255,0.06)",
    ),
}


def ghost_icon_btn(icon_name: str, size: int = 14, **props) -> rx.Component:
    """Consistent ghost icon button."""
    return rx.icon_button(
        rx.icon(icon_name, size=size),
        variant="ghost",
        size="1",
        cursor="pointer",
        color=_GHOST_BTN_COLOR,
        _hover=_GHOST_BTN_HOVER,
        border_radius=RADIUS_SM,
        **props,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PROGRESS BAR
# ═══════════════════════════════════════════════════════════════════════════


def progress_bar(pct, height: str = "6px") -> rx.Component:
    """Gradient progress bar taking a Var[int] 0-100."""
    return rx.box(
        rx.box(
            width=pct.to(str) + "%",
            height="100%",
            border_radius=RADIUS_SM,
            background=ACCENT_GRADIENT_H,
            transition="width 0.7s cubic-bezier(0.4,0,0.2,1)",
        ),
        width="100%",
        height=height,
        border_radius=RADIUS_SM,
        overflow="hidden",
        background=rx.color_mode_cond(
            light="rgba(0,0,0,0.05)", dark="rgba(255,255,255,0.06)",
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# STATUS HELPERS
# ═══════════════════════════════════════════════════════════════════════════


def status_dot(status, size: str = "8px") -> rx.Component:
    """Tiny coloured dot with glow for active states."""
    return rx.box(
        width=size,
        height=size,
        border_radius="50%",
        flex_shrink="0",
        bg=rx.match(
            status,
            ("Completed", GREEN),
            ("In-Progress", AMBER),
            "#cbd5e1",
        ),
        box_shadow=rx.match(
            status,
            ("Completed", f"0 0 6px rgba(34,197,94,0.35)"),
            ("In-Progress", f"0 0 6px rgba(245,158,11,0.35)"),
            "none",
        ),
    )


def campaign_status_indicator(status) -> rx.Component:
    """Status dot + label for campaign cards."""
    return rx.match(
        status,
        (
            "active",
            rx.hstack(
                rx.box(
                    width="6px", height="6px",
                    border_radius="50%", bg=GREEN,
                    box_shadow=f"0 0 6px rgba(34,197,94,0.35)",
                ),
                rx.text("Active", size="1", weight="medium", color=GREEN),
                spacing="2", align="center",
            ),
        ),
        (
            "paused",
            rx.hstack(
                rx.box(
                    width="6px", height="6px",
                    border_radius="50%", bg=AMBER,
                ),
                rx.text("Paused", size="1", weight="medium", color=AMBER),
                spacing="2", align="center",
            ),
        ),
        (
            "archived",
            rx.hstack(
                rx.box(
                    width="6px", height="6px",
                    border_radius="50%", bg="#94a3b8",
                ),
                rx.text("Archived", size="1", weight="medium", color="#94a3b8"),
                spacing="2", align="center",
            ),
        ),
        rx.hstack(
            rx.box(
                width="6px", height="6px",
                border_radius="50%", bg="#94a3b8",
            ),
            rx.text(status, size="1", weight="medium", color="#94a3b8"),
            spacing="2", align="center",
        ),
    )
