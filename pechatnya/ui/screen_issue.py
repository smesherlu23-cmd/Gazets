"""Шаг 1 создания выпуска: издание и данные номера."""

from __future__ import annotations

import flet as ft

from .. import storage
from . import common as c
from . import theme as t
from . import thumbs
from .screen_publication import publication_cards
from .state import AppState

FRAMES = [("none", "Без рамки"), ("double_rule", "Двойная линейка"), ("ornament", "Орнамент")]


def build(app: AppState) -> ft.Control:
    in_wizard = app.route == "issue"
    issue = app.wizard.issue if in_wizard else app.project.issue
    publication_id = app.wizard.publication_id if in_wizard else app.project.publication_id
    publication = storage.publication(publication_id) if publication_id else None

    if in_wizard and publication is not None:
        # данные издания подставляются в номер, но остаются правимыми
        issue.title = issue.title or publication.display_name
        issue.city = issue.city or publication.city
        issue.price = issue.price or publication.price
        issue.year_line = issue.year_line or publication.year_line

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

    def pick_publication(item) -> None:
        app.wizard.publication_id = item.id
        issue.title = item.display_name
        issue.city = item.city
        issue.price = item.price
        issue.year_line = item.year_line
        app.rebuild()

    def next_step(_event) -> None:
        if not issue.title.strip():
            return
        if in_wizard:
            app.navigate("grid")
        else:
            app.project.title = (
                f"{issue.title}, № {issue.number}" if issue.number.strip() else issue.title
            )
            app.touch(immediate=True)
            app.navigate("layout")

    ready = bool(issue.title.strip())

    publication_block: list[ft.Control] = []
    if in_wizard:
        publication_block = [
            c.panel_section(
                "Издание",
                publication_cards(app, publication_id, pick_publication),
                t.hint(
                    "Выпуск наследует облик издания: логотип, шрифты, краски. "
                    "Без издания номер тоже соберётся — оформление можно задать позже.",
                    size=11,
                    color=t.TEXT_FAINTER,
                ),
                spacing=10,
            )
        ]

    form = ft.Container(
        content=ft.Column(
            [
                ft.Column(
                    [
                        t.text("Новый выпуск", size=24, color=t.TEXT_PRIMARY, weight="600"),
                        ft.Container(
                            t.hint(
                                "Данные номера печатаются в служебных строках шапки. "
                                "Всё поля произвольные.",
                                size=13,
                                color=t.TEXT_MUTED,
                            ),
                            width=440,
                        ),
                    ],
                    spacing=8,
                ),
                *publication_block,
                c.field("Название издания", issue.title, edit("title"),
                        hint="как оно печатается в шапке"),
                ft.Row(
                    [
                        ft.Container(c.field("Номер", issue.number, edit("number"), hint="14"),
                                     expand=True),
                        ft.Container(c.field("Дата", issue.date, edit("date"),
                                             hint="среда, 12 июня"), expand=True),
                        ft.Container(c.field("Цена", issue.price, edit("price"), hint="5 копеек"),
                                     expand=True),
                    ],
                    spacing=12,
                ),
                ft.Row(
                    [
                        ft.Container(c.field("Город", issue.city, edit("city"),
                                             hint="место издания"), expand=True),
                        ft.Container(
                            ft.Column(
                                [
                                    t.text("Полос в выпуске", size=12, color=t.TEXT_SECONDARY),
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
                        t.text("Рамка шапки", size=12, color=t.TEXT_SECONDARY),
                        c.chip_row(FRAMES, issue.masthead_frame, set_frame, height=32),
                    ],
                    spacing=8,
                ),
                ft.Container(expand=True),
                ft.Row(
                    [
                        ft.Container(
                            t.hint(
                                "Проект сохранится одним JSON-файлом, картинки — в папке рядом."
                                if ready
                                else "Заполните название издания, чтобы продолжить.",
                                size=11,
                                color=t.TEXT_FAINTER if ready else t.WARN,
                            ),
                            expand=True,
                        ),
                        c.secondary_button(
                            "Отмена", lambda _: app.navigate("start" if in_wizard else "layout")
                        ),
                        c.primary_button(
                            "Далее: сетка полосы" if in_wizard else "Применить", next_step
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=22,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        width=660,
        padding=ft.Padding.symmetric(vertical=32, horizontal=36),
    )

    preview = ft.Container(
        content=ft.Column(
            [
                thumbs.masthead_preview(
                    issue.title or "Название издания",
                    issue.motto or (publication.brand.motto if publication else ""),
                    issue.number or "—",
                    issue.city,
                    issue.date,
                    issue.price,
                    rules_style=(publication.brand.rules_style if publication else "bold_thin")
                    if issue.masthead_frame != "ornament"
                    else "ornament",
                    logo_font=(
                        f"{publication.typography.heading_font} Bold" if publication
                        else "Old Standard TT Bold"
                    ),
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
