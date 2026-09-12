"""Экран 02 — карточка издания: метаданные номера, шаг 1 из 2."""

from __future__ import annotations

import flet as ft

from . import common as c
from . import theme as t
from . import thumbs
from .state import AppState

FRAMES = [("none", "Безъ рамки"), ("double_rule", "Двойная линейка"), ("ornament", "Орнаментъ")]


def build(app: AppState) -> ft.Control:
    in_wizard = app.route == "issue"
    issue = app.wizard.issue if in_wizard else app.project.issue

    def edit(field: str):
        def handler(value) -> None:
            setattr(issue, field, value)
            if not in_wizard:
                app.touch()

        return handler

    def set_frame(key: str) -> None:
        issue.masthead_frame = key
        if in_wizard:
            app.rebuild()
        else:
            app.project.style.masthead_frame = key
            app.touch(rebuild=True)

    def next_step(_event) -> None:
        if not issue.title.strip():
            return
        if in_wizard:
            app.navigate("presets")
        else:
            app.project.title = f"{issue.title}, № {issue.number}"
            app.touch(immediate=True)
            app.navigate("layout")

    form = ft.Container(
        content=ft.Column(
            [
                ft.Column(
                    [
                        t.text("Изданiе и выпускъ", size=24, color=t.TEXT_PRIMARY, weight="600"),
                        ft.Container(
                            t.hint(
                                "Всё, что попадётъ въ шапку полосы. Поля произвольныя: "
                                "эпоха, городъ и цена — на ваше усмотренiе.",
                                size=13,
                                color=t.TEXT_MUTED,
                            ),
                            width=440,
                        ),
                    ],
                    spacing=8,
                ),
                c.field("Названiе изданiя", issue.title, edit("title")),
                c.field("Слоганъ / девизъ", issue.motto, edit("motto")),
                ft.Row(
                    [
                        ft.Container(c.field("Номеръ", issue.number, edit("number")), expand=True),
                        ft.Container(c.field("Дата", issue.date, edit("date")), expand=True),
                        ft.Container(c.field("Цена", issue.price, edit("price")), expand=True),
                    ],
                    spacing=12,
                ),
                ft.Row(
                    [
                        ft.Container(c.field("Городъ", issue.city, edit("city")), expand=True),
                        ft.Container(
                            ft.Column(
                                [
                                    t.text("Полосъ въ выпуске", size=12, color=t.TEXT_SECONDARY),
                                    c.stepper(
                                        "",
                                        issue.pages_count,
                                        lambda value: setattr(issue, "pages_count", int(value)),
                                        minimum=1,
                                        maximum=32,
                                    ),
                                ],
                                spacing=6,
                            ),
                            expand=True,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Column(
                    [
                        t.text("Декоративная рамка шапки", size=12, color=t.TEXT_SECONDARY),
                        c.chip_row(FRAMES, issue.masthead_frame, set_frame, height=32),
                    ],
                    spacing=8,
                ),
                ft.Container(expand=True),
                ft.Row(
                    [
                        ft.Container(
                            t.hint(
                                "Проектъ сохранится однимъ JSON-файломъ, картинки — въ папке рядомъ.",
                                size=11,
                                color=t.TEXT_FAINTER,
                            ),
                            expand=True,
                        ),
                        c.secondary_button(
                            "Отмена",
                            lambda _: app.navigate("start" if in_wizard else "layout"),
                        ),
                        c.primary_button(
                            "Далее: пресетъ" if in_wizard else "Применить", next_step
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=24,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        width=620,
        padding=ft.Padding.symmetric(vertical=32, horizontal=36),
    )

    preview = ft.Container(
        content=ft.Column(
            [
                thumbs.masthead_preview(
                    issue.title or "Названiе",
                    issue.motto,
                    issue.number,
                    issue.city,
                    issue.date,
                    issue.price,
                    rules_style="bold_thin" if issue.masthead_frame != "ornament" else "ornament",
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        ),
        bgcolor=t.BG_TITLEBAR,
        expand=True,
        padding=30,
    )

    return ft.Row([form, preview], spacing=0, expand=True)
