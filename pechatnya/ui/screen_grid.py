"""Экран 04 — шаблоны сетки полосы: шагъ 2 изъ 2 и смена сетки у готовой полосы."""

from __future__ import annotations

import flet as ft

from ..presets import GRID_TEMPLATES, apply_template, new_project
from . import common as c
from . import theme as t
from . import thumbs
from .state import AppState

# Схемы миниатюр: (подпись, строка, весъ)
TEMPLATE_THUMBS = {
    "front-main-side": [("ШАПКА", 0, 1), ("ГЛАВНАЯ", 1, 2), ("БОКЪ", 1, 1),
                        ("ПОДВАЛЪ", 2, 1), ("ПОДВАЛЪ", 2, 1)],
    "front-three-columns": [("ШАПКА", 0, 1), ("КОЛОНКА", 1, 1), ("КОЛОНКА", 1, 1),
                            ("КОЛОНКА", 1, 1)],
    "photo-lead": [("ШАПКА", 0, 1), ("ФОТО", 1, 1), ("ТЕКСТЪ", 2, 2), ("ВРЕЗКА", 2, 1)],
    "vertical-masthead": [("ЛОГО", 1, 1), ("ГЛАВНАЯ", 1, 2), ("ВРЕЗКИ", 1, 1),
                          ("ПОДВАЛЪ", 2, 2), ("ПОДВАЛЪ", 2, 1)],
    "quadrants": [("ШАПКА", 0, 1), ("КВАДРАНТЪ", 1, 1), ("КВАДРАНТЪ", 1, 1),
                  ("КВАДРАНТЪ", 2, 1), ("КВАДРАНТЪ", 2, 1)],
    "blank": [("ПУСТО", 1, 1)],
}

KINDS = [("front", "Передняя полоса"), ("inner", "Внутренняя")]


def build(app: AppState) -> ft.Control:
    in_wizard = app.route == "grid"
    project = app.project
    page_kind = "front" if in_wizard else app.page_model.kind
    current = app.wizard.template_id if in_wizard else app.page_model.template_id

    def choose(template_id: str):
        def handler(_event) -> None:
            if in_wizard:
                app.wizard.template_id = template_id
                app.rebuild()
            else:
                apply_template(app.page_model, template_id)
                app.selected_block_id = None
                app.touch(rebuild=True, immediate=True)

        return handler

    cards = []
    for template in GRID_TEMPLATES:
        if page_kind == "inner" and template.kind == "front":
            continue
        cards.append(
            c.card(
                ft.Column(
                    [
                        thumbs.grid_thumb(TEMPLATE_THUMBS[template.id]),
                        t.text(template.name, size=13, color=t.TEXT_PRIMARY, weight="500"),
                        t.hint(template.description, size=11, color=t.TEXT_MUTED),
                    ],
                    spacing=8,
                ),
                active=template.id == current,
                on_click=choose(template.id),
            )
        )

    grid = ft.GridView(
        controls=cards, runs_count=3, max_extent=320, spacing=16, run_spacing=16,
        child_aspect_ratio=0.92, expand=True,
    )

    # ---------------------------------------------------------------- правая панель
    def set_format(value: str) -> None:
        project.page_format = value.split(",")[0].strip()
        project.orientation = "portrait" if "портретъ" in value else "landscape"
        app.touch()

    def margin_field(index: int, label: str) -> ft.Control:
        def handler(value: str) -> None:
            try:
                project.margins_mm[index] = float(value.replace(",", "."))
            except ValueError:
                return
            app.touch()

        return ft.Container(
            c.field(label, f"{project.margins_mm[index]:g}", handler, height=30), expand=True
        )

    pages_thumbs = ft.Row(
        [
            ft.Container(
                thumbs.page_thumb(index == app.current_page, index + 1, width=52, height=74),
                on_click=(lambda index: lambda _e: _go_page(app, index))(index),
            )
            for index in range(len(project.pages))
        ]
        + [
            ft.Container(
                content=ft.Text("+", size=16, color=t.TEXT_SECONDARY),
                width=52,
                height=74,
                border=ft.Border.all(1, t.BORDER_STRONG),
                border_radius=2,
                alignment=ft.Alignment.CENTER,
                on_click=lambda _e: _add_page(app),
                ink=True,
            )
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )

    def assemble(_event) -> None:
        if in_wizard:
            project = new_project(
                app.wizard.issue,
                preset_id=app.wizard.preset_id,
                template_id=app.wizard.template_id,
                brand=app.wizard.brand,
            )
            app.set_project(project)
            app.wizard.reset()
        app.navigate("layout")
        app.refresh_preview(immediate=True)

    panel = ft.Container(
        content=ft.Column(
            [
                c.panel_section(
                    "Форматъ",
                    c.select(
                        "",
                        f"{project.page_format}, портретъ",
                        [f"{name}, портретъ" for name in ("A3", "A4")],
                        set_format,
                    ),
                    spacing=8,
                ),
                c.panel_section(
                    "Поля, мм",
                    ft.Row(
                        [margin_field(0, "верхъ"), margin_field(1, "низъ"),
                         margin_field(2, "лево"), margin_field(3, "право")],
                        spacing=8,
                    ),
                    spacing=8,
                ),
                c.panel_section(
                    "Модульная сетка",
                    c.stepper(
                        "Колонокъ",
                        project.grid_columns,
                        lambda value: (setattr(project, "grid_columns", int(value)), app.touch())[0],
                        minimum=2,
                        maximum=12,
                        width=110,
                    ),
                    c.stepper(
                        "Средникъ, мм",
                        project.grid_gutter_mm,
                        lambda value: (setattr(project, "grid_gutter_mm", value), app.touch())[0],
                        step=0.5,
                        decimals=1,
                        minimum=0,
                        maximum=20,
                        width=110,
                    ),
                    spacing=10,
                ),
                c.panel_section("Полосы выпуска", pages_thumbs, spacing=10),
                ft.Container(expand=True),
                c.primary_button("Собрать полосу", assemble, width=268),
                c.secondary_button(
                    "Назадъ",
                    lambda _: app.navigate("presets" if in_wizard else "layout"),
                    width=268,
                ),
            ],
            spacing=20,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        width=300,
        bgcolor=t.BG_RAIL,
        border=ft.Border.only(left=ft.BorderSide(1, t.BORDER_PANEL)),
        padding=ft.Padding.symmetric(vertical=20, horizontal=16),
    )

    left = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                t.text("Шаблонъ сетки полосы", size=24, color=t.TEXT_PRIMARY, weight="600"),
                                t.hint(
                                    "Стартовое деленiе полосы на блоки — границы потомъ тянутся мышью.",
                                    size=13,
                                    color=t.TEXT_MUTED,
                                ),
                            ],
                            spacing=4,
                        ),
                        c.chip_row(
                            KINDS,
                            page_kind,
                            lambda key: _set_page_kind(app, key),
                            height=30,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                grid,
            ],
            spacing=20,
            expand=True,
        ),
        padding=ft.Padding.symmetric(vertical=30, horizontal=32),
        expand=True,
    )
    return ft.Row([left, panel], spacing=0, expand=True)


def _set_page_kind(app: AppState, kind: str) -> None:
    if app.route == "grid":
        return
    page = app.page_model
    page.kind = kind
    page.show_masthead = kind == "front"
    app.touch(rebuild=True)


def _go_page(app: AppState, index: int) -> None:
    app.current_page = index
    app.selected_block_id = None
    app.rebuild()
    app.refresh_preview(immediate=True)


def _add_page(app: AppState) -> None:
    from ..presets import build_page

    app.project.pages.append(build_page("quadrants", "inner"))
    app.project.issue.pages_count = len(app.project.pages)
    app.touch(rebuild=True)
