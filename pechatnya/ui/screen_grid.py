"""Экран 04 — шаблоны сетки полосы: шаг 2 из 2 и смена сетки у готовой полосы."""

from __future__ import annotations

import flet as ft

from .. import storage
from ..models import PAGE_FORMATS
from ..presets import GRID_TEMPLATES, apply_template, new_project
from . import common as c
from . import theme as t
from . import thumbs
from .state import AppState

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
                app.project.repair_continuations()
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
                        thumbs.frame_thumb(template.build(), masthead=template.kind != "inner"),
                        t.text(template.name, size=13, color=t.TEXT_PRIMARY, weight="500"),
                        t.hint(template.description, size=11, color=t.TEXT_MUTED),
                    ],
                    spacing=8,
                ),
                active=template.id == current,
                on_click=choose(template.id),
            )
        )

    for saved in storage.user_templates():
        if page_kind == "inner" and saved.kind == "front":
            continue
        cards.append(
            c.card(
                ft.Column(
                    [
                        thumbs.frame_thumb(saved.root, masthead=saved.kind != "inner"),
                        ft.Row(
                            [
                                t.text(saved.name, size=13, color=t.TEXT_PRIMARY, weight="500",
                                       expand=True, max_lines=1,
                                       overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Container(
                                    ft.Icon(ft.Icons.CLOSE, size=12, color=t.TEXT_FAINT),
                                    on_click=(lambda key: lambda _e: _drop_template(app, key))(
                                        saved.id
                                    ),
                                    padding=4,
                                    ink=True,
                                    tooltip="Удалить свой шаблон",
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        t.hint(f"своя сетка · блоков: {saved.blocks}", size=11, color=t.TEXT_MUTED),
                    ],
                    spacing=8,
                ),
                active=current == f"user:{saved.id}",
                on_click=(lambda key: lambda _e: _use_template(app, key, in_wizard))(saved.id),
            )
        )

    grid = ft.GridView(
        controls=cards, runs_count=3, max_extent=320, spacing=16, run_spacing=16,
        child_aspect_ratio=0.92, expand=True,
    )

    # ---------------------------------------------------------------- правая панель
    def set_format(value: str) -> None:
        project.page_format = value
        app.touch(rebuild=True, immediate=True)

    def set_orientation(value: str) -> None:
        project.orientation = value
        app.touch(rebuild=True, immediate=True)

    def set_custom(index: int):
        def handler(value: str) -> None:
            try:
                project.custom_size_mm[index] = float(value.replace(",", "."))
            except (ValueError, IndexError):
                return
            app.touch(immediate=True)

        return handler

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
            publication = (
                storage.publication(app.wizard.publication_id)
                if app.wizard.publication_id
                else None
            )
            app.set_project(
                new_project(app.wizard.issue, publication, template_id=app.wizard.template_id)
            )
            app.wizard.reset()
        app.navigate("layout")
        app.refresh_preview(immediate=True)

    panel = ft.Container(
        content=ft.Column(
            [
                c.panel_section(
                    "Формат листа",
                    c.select("", project.page_format, list(PAGE_FORMATS) + ["Свой размер"],
                             set_format),
                    c.segment(
                        [("portrait", "Портрет"), ("landscape", "Альбом")],
                        project.orientation,
                        set_orientation,
                    ),
                    *(
                        [
                            ft.Row(
                                [
                                    ft.Container(
                                        c.field("Ширина, мм", f"{project.custom_size_mm[0]:g}",
                                                set_custom(0), height=30),
                                        expand=True,
                                    ),
                                    ft.Container(
                                        c.field("Высота, мм", f"{project.custom_size_mm[1]:g}",
                                                set_custom(1), height=30),
                                        expand=True,
                                    ),
                                ],
                                spacing=8,
                            )
                        ]
                        if project.page_format not in PAGE_FORMATS
                        else []
                    ),
                    t.hint(
                        f"{project.sheet_mm()[0]:.0f} × {project.sheet_mm()[1]:.0f} мм · "
                        f"{project.sheet_px()[0]} × {project.sheet_px()[1]} px при 96 dpi",
                        size=11,
                    ),
                    spacing=10,
                ),
                c.panel_section(
                    "Поля, мм",
                    ft.Row(
                        [margin_field(0, "верх"), margin_field(1, "низ"),
                         margin_field(2, "лево"), margin_field(3, "право")],
                        spacing=8,
                    ),
                    spacing=8,
                ),
                c.panel_section(
                    "Модульная сетка",
                    c.stepper(
                        "Колонок",
                        project.grid_columns,
                        lambda value: (setattr(project, "grid_columns", int(value)), app.touch())[0],
                        minimum=2,
                        maximum=12,
                        width=110,
                    ),
                    c.stepper(
                        "Средник, мм",
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
                    "Назад",
                    lambda _: app.navigate("issue" if in_wizard else "layout"),
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
                                t.text("Шаблон сетки полосы", size=24, color=t.TEXT_PRIMARY, weight="600"),
                                t.hint(
                                    "Стартовое деление полосы на блоки — границы потом тянутся мышью.",
                                    size=13,
                                    color=t.TEXT_MUTED,
                                ),
                            ],
                            spacing=4,
                        ),
                        ft.Row(
                            [
                                c.chip_row(
                                    KINDS,
                                    page_kind,
                                    lambda key: _set_page_kind(app, key),
                                    height=30,
                                ),
                                *(
                                    []
                                    if in_wizard
                                    else [
                                        c.secondary_button(
                                            "Сохранить эту сетку",
                                            lambda _e: app.save_page_as_template(),
                                            height=30,
                                        )
                                    ]
                                ),
                            ],
                            spacing=10,
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


def _use_template(app: AppState, template_id: str, in_wizard: bool) -> None:
    """Применяет свою сетку: в мастере — к будущей полосе, иначе — к текущей."""
    if in_wizard:
        app.wizard.template_id = f"user:{template_id}"
        app.rebuild()
        return
    app.apply_user_template(template_id)


def _drop_template(app: AppState, template_id: str) -> None:
    storage.delete_user_template(template_id)
    app.rebuild()
