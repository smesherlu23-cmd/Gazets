"""Экран 03 — пресеты оформления: пять стартовыхъ стилей полосы."""

from __future__ import annotations

import flet as ft

from .. import storage
from ..presets import STYLE_PRESETS, apply_preset
from . import common as c
from . import theme as t
from . import thumbs
from .state import AppState

# Как выглядит миниатюра каждого пресета (значения — из README, экран 03).
THUMB_STYLE = {
    "classic": dict(paper="#f1ece0", logo="ВЕСТНИКЪ", logo_font="Old Standard TT Bold",
                    logo_size=15, columns=3, rules=2, halftone=True, boxed=True),
    "tabloid": dict(paper="#eae5d9", logo="ТАБЛОИДЪ", logo_font="Oswald Bold", logo_size=19,
                    columns=2, rules=1, halftone=True, boxed=False, accent="#141210"),
    "bulletin": dict(paper="#f0eee6", logo="ВѢСТНИКЪ УПРАВЫ", logo_font="PT Sans Narrow Bold",
                     logo_size=12, columns=2, rules=2, halftone=False, boxed=True, accent="#23221e"),
    "agitprop": dict(paper="#e8e0cd", logo="ГОЛОСЪ ДОКА", logo_font="Oswald Bold", logo_size=16,
                     columns=2, rules=1, halftone=False, boxed=True, invert=True, accent="#8a2a1c"),
    "underground": dict(paper="#e4ded0", logo="ЛИСТОКЪ", logo_font="IBM Plex Mono SemiBold",
                        logo_size=12, columns=1, rules=1, halftone=False, boxed=False,
                        accent="#221f1a"),
}


def build(app: AppState) -> ft.Control:
    in_wizard = app.route == "presets"
    current = app.wizard.preset_id if in_wizard else app.project.style.preset_id

    def choose(preset_id: str):
        def handler(_event) -> None:
            if in_wizard:
                app.wizard.preset_id = preset_id
            else:
                apply_preset(app.project, preset_id)
                app.touch(rebuild=True)
                return
            app.rebuild()

        return handler

    cards = []
    for preset in STYLE_PRESETS:
        cards.append(
            ft.Container(
                content=c.card(
                    ft.Column(
                        [
                            thumbs.paper_thumb(height=300, **THUMB_STYLE[preset.id]),
                            t.text(preset.name, size=14, color=t.TEXT_PRIMARY, weight="500"),
                            t.hint(preset.description, size=11, color=t.TEXT_MUTED),
                        ],
                        spacing=8,
                    ),
                    active=preset.id == current,
                    on_click=choose(preset.id),
                ),
                expand=True,
            )
        )

    saved = storage.user_presets()
    saved_row: list[ft.Control] = []
    if saved:
        saved_row = [
            t.caps("Свои пресеты"),
            ft.Row(
                [
                    c.chip(item.name, False, lambda _e, item=item: _apply_user_preset(app, item))
                    for item in saved
                ],
                spacing=8,
                wrap=True,
            ),
        ]

    def save_own(_event) -> None:
        preset = storage.UserPreset(
            name=f"{app.project.issue.title} — оформленiе",
            description="Сохранено изъ текущаго выпуска",
            style=app.project.style,
            typography=app.project.typography,
        )
        storage.save_user_preset(preset)
        app.rebuild()

    def go_next(_event) -> None:
        app.navigate("grid")

    footer = (
        ft.Row(
            [
                ft.Container(expand=True),
                c.secondary_button("Назадъ", lambda _: app.navigate("issue")),
                c.primary_button("Далее: сетка полосы", go_next),
            ],
            spacing=12,
        )
        if in_wizard
        else ft.Row(
            [
                ft.Container(expand=True),
                c.secondary_button("Къ вёрстке", lambda _: app.navigate("layout")),
            ]
        )
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                t.text("Пресеты оформленiя", size=24, color=t.TEXT_PRIMARY, weight="600"),
                                t.hint(
                                    "Стартовый наборъ гарнитуръ, линеекъ и кеглей. "
                                    "Всё правится потомъ вручную.",
                                    size=13,
                                    color=t.TEXT_MUTED,
                                ),
                            ],
                            spacing=4,
                        ),
                        c.secondary_button("Сохранить свой пресетъ", save_own),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(cards, spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
                *saved_row,
                footer,
            ],
            spacing=22,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=ft.Padding.symmetric(vertical=30, horizontal=32),
        expand=True,
    )


def _apply_user_preset(app: AppState, preset: storage.UserPreset) -> None:
    app.project.style = preset.style
    app.project.typography = preset.typography
    app.touch(rebuild=True)
