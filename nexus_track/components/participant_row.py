"""Participant row - dense working row for the campaign workspace."""

import reflex as rx

from ..state import NexusState
from ..components.design_tokens import (
    ACCENT,
    ACCENT_SOFT,
    AMBER,
    AMBER_SOFT,
    BORDER,
    BORDER_SUBTLE,
    CARD_BG,
    HEADING,
    RADIUS_MD,
    RADIUS_SM,
    RED_SOFT,
    SHADOW_SM,
    SUBTEXT,
    TEXT,
    TRANSITION_FAST,
)


_NOTES_INPUT_STYLE = {
    "width": "100%",
    "padding": "6px 10px",
    "border_radius": RADIUS_SM,
    "border": "1px solid rgba(255,255,255,0.06)",
    "font_size": "12px",
    "outline": "none",
    "background": "rgba(255,255,255,0.02)",
    "color": "inherit",
}


def participant_row(p: dict) -> rx.Component:
    eid = p["google_event_id"].to(str)
    has_issue = p["_has_issue"]
    issue_preview = p["_issue_preview"].to(str)
    is_selected = p["_is_selected"]
    name = p["name"].to(str)
    email = p["email"].to(str)
    time = p["appointment_time"].to(str)
    date = p["appointment_date"].to(str)
    platform = p["platform"].to(str)
    model_tag = p["model_tag"].to(str)
    status = p["status"].to(str)
    notes = p["notes"].to(str)
    save_state = p["_save_state"].to(str)

    is_completed = status == "Completed"

    return rx.box(
        rx.box(
            rx.box(
                rx.hstack(
                    rx.checkbox(
                        checked=is_selected,
                        on_change=lambda _v: NexusState.toggle_select(eid),
                        size="1",
                        color_scheme="iris",
                        cursor="pointer",
                        flex_shrink="0",
                    ),
                    rx.checkbox(
                        checked=is_completed,
                        on_change=lambda _v: NexusState.toggle_completed(eid),
                        size="2",
                        color_scheme="green",
                        cursor="pointer",
                        flex_shrink="0",
                    ),
                    rx.center(
                        rx.text(
                            rx.cond(time != "", date + " " + time, date),
                            size="1",
                            weight="bold",
                            color=ACCENT,
                            font_variant_numeric="tabular-nums",
                            white_space="nowrap",
                        ),
                        padding="4px 8px",
                        border_radius=RADIUS_SM,
                        background=ACCENT_SOFT,
                        min_width="118px",
                        flex_shrink="0",
                    ),
                    spacing="2",
                    align="center",
                    min_width="0",
                    width="100%",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            name,
                            size="2",
                            weight="medium",
                            color=rx.cond(is_completed, SUBTEXT, HEADING),
                            text_decoration=rx.cond(is_completed, "line-through", "none"),
                            white_space="nowrap",
                            overflow="hidden",
                            text_overflow="ellipsis",
                            max_width="100%",
                            min_width="0",
                            flex_shrink="1",
                        ),
                        rx.cond(
                            has_issue,
                            rx.badge(
                                "Issue",
                                size="1",
                                variant="soft",
                                color_scheme="amber",
                            ),
                            rx.fragment(),
                        ),
                        rx.cond(
                            save_state == "saving",
                            rx.badge(
                                "Saving",
                                color_scheme="blue",
                                size="1",
                                variant="soft",
                            ),
                            rx.cond(
                                save_state == "saved",
                                rx.badge(
                                    "Saved",
                                    color_scheme="green",
                                    size="1",
                                    variant="soft",
                                ),
                                rx.fragment(),
                            ),
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                        min_width="0",
                        flex_wrap="wrap",
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
                    spacing="1",
                    min_width="0",
                    width="100%",
                    align="start",
                ),
                rx.box(
                    rx.el.input(
                        default_value=notes,
                        placeholder="Add notes...",
                        on_blur=lambda e: NexusState.set_notes(eid, e),
                        style=_NOTES_INPUT_STYLE,
                    ),
                    width="100%",
                ),
                rx.select(
                    NexusState.platforms,
                    value=platform,
                    placeholder="Platform",
                    on_change=lambda v: NexusState.set_platform(eid, v),
                    size="1",
                    variant="soft",
                    width=rx.breakpoints(initial="100%", lg="110px"),
                    flex_shrink="0",
                ),
                rx.select(
                    NexusState.all_model_tags,
                    value=model_tag,
                    placeholder="Model",
                    on_change=lambda v: NexusState.set_model_tag(eid, v),
                    size="1",
                    variant="soft",
                    width=rx.breakpoints(initial="100%", lg="108px"),
                    flex_shrink="0",
                ),
                rx.flex(
                    rx.icon_button(
                        rx.icon("triangle-alert", size=13),
                        size="1",
                        variant=rx.cond(has_issue, "soft", "ghost"),
                        color_scheme="amber",
                        on_click=NexusState.open_issue_editor(eid),
                        cursor="pointer",
                        flex_shrink="0",
                        _hover={"background": AMBER_SOFT},
                    ),
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
                    rx.cond(
                        NexusState.admin_mode,
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
                        rx.fragment(),
                    ),
                    gap="2",
                    wrap="wrap",
                    justify="end",
                    align="center",
                    width=rx.breakpoints(initial="100%", lg="auto"),
                ),
                display="grid",
                grid_template_columns=rx.breakpoints(
                    initial="1fr",
                    lg="180px minmax(0,1.55fr) minmax(180px,1fr) 112px 110px auto",
                ),
                gap="10px",
                align_items="center",
                width="100%",
            ),
            width="100%",
        ),
        rx.cond(
            has_issue,
            rx.box(
                rx.flex(
                    rx.hstack(
                        rx.icon("triangle-alert", size=12, color=AMBER),
                        rx.text(
                            issue_preview,
                            size="1",
                            color=TEXT,
                            line_height="1.45",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.hstack(
                        rx.button(
                            "Edit",
                            size="1",
                            variant="ghost",
                            color_scheme="amber",
                            on_click=NexusState.open_issue_editor(eid),
                            cursor="pointer",
                        ),
                        rx.button(
                            "Resolve",
                            size="1",
                            variant="ghost",
                            color_scheme="gray",
                            on_click=NexusState.clear_issue(eid),
                            cursor="pointer",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    direction=rx.breakpoints(initial="column", md="row"),
                    justify="between",
                    align=rx.breakpoints(initial="start", md="center"),
                    gap="2",
                    width="100%",
                ),
                padding="7px 10px",
                margin_top="8px",
                border_radius=RADIUS_SM,
                background=AMBER_SOFT,
                border=BORDER_SUBTLE,
            ),
            rx.fragment(),
        ),
        padding="10px 12px",
        width="100%",
        border_radius=RADIUS_MD,
        background=CARD_BG,
        border=rx.cond(has_issue, f"1px solid {AMBER}", BORDER),
        box_shadow=SHADOW_SM,
        transition=TRANSITION_FAST,
        _hover={"border_color": "rgba(99,102,241,0.16)"},
        overflow="hidden",
    )
