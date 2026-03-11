"""
Nexus-Track — app registration, routing & global design tokens.

Pages:
  /                                    Dashboard (campaign grid)
  /campaign/[campaign_id]              Campaign detail (participant list)
  /campaign/[campaign_id]/edit         Edit campaign form
  /new                                 New-campaign form
  /settings                            Label editor & calendar discovery
"""

import reflex as rx

from .state import NexusState
from .pages.dashboard import dashboard_page
from .pages.campaign_detail import campaign_detail_page
from .pages.edit_campaign import edit_campaign_page
from .pages.new_campaign import new_campaign_page
from .pages.settings import settings_page

# ── Global CSS ────────────────────────────────────────────────────────────
_GLOBAL_STYLE: dict = {
    "body": {
        "font_family": (
            "'Inter', -apple-system, BlinkMacSystemFont, "
            "'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
        ),
        "-webkit-font-smoothing": "antialiased",
        "-moz-osx-font-smoothing": "grayscale",
        # dot-grid background pattern
        "background_image": (
            "radial-gradient(circle at 1px 1px, "
            "rgba(99,102,241,0.04) 1px, transparent 0)"
        ),
        "background_size": "32px 32px",
    },
    "::selection": {
        "background_color": "rgba(99,102,241,0.18)",
    },
    # radial spotlight behind the page content
    ".page-content::before": {
        "content": '""',
        "position": "fixed",
        "top": "0",
        "left": "50%",
        "transform": "translateX(-50%)",
        "width": "800px",
        "height": "600px",
        "background": (
            "radial-gradient(ellipse at center, "
            "rgba(99,102,241,0.06) 0%, transparent 70%)"
        ),
        "pointer_events": "none",
        "z_index": "-1",
    },
    # pulse animation for the live dot
    "@keyframes pulse": {
        "0%, 100%": {"opacity": "1", "transform": "scale(1)"},
        "50%": {"opacity": "0.45", "transform": "scale(0.85)"},
    },
    ".pulse-dot": {
        "animation": "pulse 2.4s cubic-bezier(0.4,0,0.6,1) infinite",
    },
    # gentle fade-in for pages
    "@keyframes fadeIn": {
        "from": {"opacity": "0", "transform": "translateY(6px)"},
        "to": {"opacity": "1", "transform": "translateY(0)"},
    },
    ".page-content": {
        "animation": "fadeIn 0.35s ease-out",
        "position": "relative",
    },
    # smooth shimmer for progress bars
    "@keyframes shimmer": {
        "0%": {"background_position": "-200% 0"},
        "100%": {"background_position": "200% 0"},
    },
}

# ── App ───────────────────────────────────────────────────────────────────
app = rx.App(
    theme=rx.theme(
        appearance="inherit",
        accent_color="iris",
        gray_color="slate",
        radius="large",
        scaling="100%",
    ),
    style=_GLOBAL_STYLE,
)

app.add_page(
    dashboard_page,
    route="/",
    title="Nexus-Track",
    on_load=[NexusState.load_campaigns, NexusState.start_auto_refresh],
)
app.add_page(
    campaign_detail_page,
    route="/campaign/[campaign_id]",
    title="Campaign · Nexus-Track",
    on_load=[NexusState.load_campaign_detail, NexusState.start_auto_refresh],
)
app.add_page(
    edit_campaign_page,
    route="/campaign/[campaign_id]/edit",
    title="Edit Campaign · Nexus-Track",
    on_load=NexusState.load_edit_campaign,
)
app.add_page(
    new_campaign_page,
    route="/new",
    title="New Campaign · Nexus-Track",
    on_load=NexusState.clear_form,
)
app.add_page(
    settings_page,
    route="/settings",
    title="Settings · Nexus-Track",
    on_load=NexusState.load_settings,
)
