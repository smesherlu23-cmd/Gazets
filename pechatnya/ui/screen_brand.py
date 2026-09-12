"""Экранъ 09 — бренд изданiя: логотипъ, рубрикаторъ, краска.

Бренд наследуется всеми выпусками изданiя: «Применить ко всемъ» перебираетъ
сохранённые проекты того же названiя и обновляетъ въ нихъ шапку, не трогая
вёрстку.
"""

from __future__ import annotations

import pathlib

import flet as ft

from .. import fonts, storage
from ..models import Brand
from . import common as c
from . import theme as t
from . import thumbs
from .state import AppState

DIRECTIONS = [
    ("gothic", "Готическiй", "UnifrakturMaguntia"),
    ("antiqua", "Новая антиква", "Bodoni Moda"),
    ("narrow", "Узкiй гротескъ", "Oswald"),
    ("framed", "Въ рамке", "PT Sans Narrow"),
]
RULE_STYLES = [("single", "Одна"), ("bold_thin", "Жирная + тонкая"), ("ornament", "Орнаментъ")]
INKS = ["#15120e", "#1f2a44", "#6b3226", "#2a3a2c"]
TABS = [("logo", "Логотипъ"), ("rubricator", "Рубрикаторъ"), ("ink", "Краска")]


def build(app: AppState) -> ft.Control:
    brand = app.project.brand
    tab = getattr(app, "brand_tab", "logo")

    def set_value(field: str, value) -> None:
        setattr(brand, field, value)
        app.touch(rebuild=True)

    def set_quiet(field: str, value) -> None:
        setattr(brand, field, value)
        app.touch()

    # ------------------------------------------------------------- левая панель
    brands = storage.saved_brands()
    brand_rows = [
        c.list_row(
            ft.Column(
                [
                    t.text(item.display_name, size=12, color=t.TEXT_PRIMARY),
                    t.hint(item.logo_font, size=10, color=t.TEXT_FAINTER),
                ],
                spacing=2,
            ),
            active=item.id == brand.id,
            on_click=(lambda item: lambda _e: _use_brand(app, item))(item),
            height=52,
        )
        for item in brands
    ]
    rail = c.rail(
        ft.Column(
            [
                t.caps("Бренды / Titles"),
                *brand_rows,
                ft.Container(
                    content=t.text("+ Новый брендъ", size=12, color=t.TEXT_SECONDARY),
                    height=52,
                    alignment=ft.Alignment.CENTER,
                    border=ft.Border.all(1, t.BORDER_STRONG),
                    border_radius=t.RADIUS_CONTROL,
                    on_click=lambda _e: _new_brand(app),
                    ink=True,
                ),
                ft.Container(expand=True),
                t.hint(
                    "Брендъ наследуется всеми выпусками изданiя: правка шапки "
                    "меняетъ её во всехъ номерахъ, вёрстка остаётся.",
                    size=11,
                    color=t.TEXT_FAINTER,
                ),
            ],
            spacing=10,
            expand=True,
        ),
        width=256,
    )

    # ------------------------------------------------------------------- центръ
    logo_font = fonts.resolve_for_text(brand.logo_font, brand.display_name)
    masthead = thumbs.masthead_preview(
        brand.display_name,
        brand.motto if brand.motto_enabled else "",
        app.project.issue.number,
        app.project.issue.city,
        app.project.issue.date,
        app.project.issue.price,
        rules_style=brand.rules_style,
        logo_font=f"{logo_font} Bold" if logo_font != "UnifrakturMaguntia" else logo_font,
        width=700,
    )

    applications = ft.Row(
        [
            c.card(
                ft.Column(
                    [
                        t.caps("Шапка внутренней полосы", size=9),
                        ft.Container(
                            content=ft.Text(
                                brand.display_name.upper(),
                                size=12,
                                color="#15120e",
                                font_family="PT Sans Narrow Bold",
                            ),
                            bgcolor="#efe7d4",
                            padding=8,
                            border_radius=2,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            c.card(
                ft.Column(
                    [
                        t.caps("Штампъ и колонцифра", size=9),
                        ft.Container(
                            content=ft.Container(
                                content=ft.Text("№", size=12, color="#15120e",
                                                font_family="Old Standard TT Bold"),
                                width=52,
                                height=52,
                                border=ft.Border.all(1, "#8e8878"),
                                border_radius=99,
                                alignment=ft.Alignment.CENTER,
                            ),
                            bgcolor="#efe7d4",
                            padding=8,
                            border_radius=2,
                            alignment=ft.Alignment.CENTER,
                        ),
                    ],
                    spacing=8,
                ),
            ),
            c.card(
                ft.Column(
                    [
                        t.caps("Плашки рубрики", size=9),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Container(
                                        content=ft.Text("ХРОНИКА", size=10, color="#efe7d4",
                                                        font_family="PT Sans Narrow Bold"),
                                        bgcolor=brand.ink,
                                        padding=ft.Padding.symmetric(vertical=3, horizontal=6),
                                    ),
                                    ft.Container(height=1, bgcolor="#15120e"),
                                ],
                                spacing=6,
                            ),
                            bgcolor="#efe7d4",
                            padding=8,
                            border_radius=2,
                        ),
                    ],
                    spacing=8,
                ),
            ),
        ],
        spacing=16,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    directions = ft.Row(
        [
            ft.Container(
                content=c.card(
                    ft.Column(
                        [
                            ft.Container(
                                content=ft.Text(
                                    "Gazette" if key in ("gothic", "antiqua") else brand.display_name,
                                    size=16,
                                    color="#15120e",
                                    font_family=font if key != "framed" else "PT Sans Narrow Bold",
                                    no_wrap=True,
                                ),
                                bgcolor="#efe7d4",
                                padding=10,
                                height=56,
                                alignment=ft.Alignment.CENTER,
                                border=ft.Border.all(2, "#15120e") if key == "framed" else None,
                            ),
                            t.text(label, size=12, color=t.TEXT_SECONDARY),
                        ],
                        spacing=8,
                    ),
                    active=brand.logo_direction == key,
                    on_click=(lambda key, font: lambda _e: _set_direction(app, key, font))(key, font),
                ),
                expand=True,
            )
            for key, label, font in DIRECTIONS
        ],
        spacing=12,
    )

    warn = (
        t.hint(
            f"«{brand.logo_font}» безъ кириллицы — кириллическое названiе "
            f"набирается гарнитурой {fonts.FALLBACK_FOR_CYRILLIC}.",
            size=11,
            color=t.WARN,
        )
        if not fonts.supports_cyrillic(brand.logo_font)
        else t.hint("Гарнитура содержитъ кириллицу — подмены не будетъ.", size=11,
                    color=t.TEXT_FAINTER)
    )

    center = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        t.text("Логотипъ и примененiе", size=18, color=t.TEXT_PRIMARY, weight="600"),
                        t.hint("масштабъ по ширине полосы", size=11, color=t.TEXT_MUTED),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                masthead,
                applications,
                c.panel_section("Направленiя логотипа", directions, warn, spacing=12),
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=ft.Padding.symmetric(vertical=24, horizontal=26),
        expand=True,
    )

    # ------------------------------------------------------------- правая панель
    if tab == "logo":
        panel_body = ft.Column(
            [
                c.field("Названiе · латиница", brand.name_latin, lambda v: set_quiet("name_latin", v)),
                c.field("Названiе · кириллица", brand.name_cyrillic,
                        lambda v: set_quiet("name_cyrillic", v)),
                c.toggle("Набирать кириллицей", brand.use_cyrillic,
                         lambda v: set_value("use_cyrillic", v)),
                c.select("Гарнитура логотипа", brand.logo_font, fonts.available_families(),
                         lambda v: set_value("logo_font", v)),
                c.stepper("Кегль логотипа, пт", brand.logo_size_pt,
                          lambda v: set_quiet("logo_size_pt", v), step=1, minimum=10, maximum=160,
                          decimals=1, width=110),
                c.stepper("Трекингъ, ‰", brand.tracking_permille,
                          lambda v: set_quiet("tracking_permille", int(v)), step=5, minimum=-50,
                          maximum=400, width=110),
                c.toggle("Надстрочная строка", brand.superline_enabled,
                         lambda v: set_value("superline_enabled", v)),
                *([c.field("Надстрочная строка", brand.superline, lambda v: set_quiet("superline", v))]
                  if brand.superline_enabled else []),
                c.toggle("Девизъ подъ названiемъ", brand.motto_enabled,
                         lambda v: set_value("motto_enabled", v)),
                *([c.field("Девизъ / Motto", brand.motto, lambda v: set_quiet("motto", v))]
                  if brand.motto_enabled else []),
                c.panel_section(
                    "Линейки подъ шапкой",
                    c.segment(RULE_STYLES, brand.rules_style, lambda v: set_value("rules_style", v)),
                    spacing=10,
                ),
            ],
            spacing=14,
        )
    elif tab == "rubricator":
        panel_body = ft.Column(
            [
                t.hint("Строка рубрикъ подъ линейками шапки. По одной въ строке.", size=11),
                c.field(
                    "",
                    "\n".join(brand.rubricator),
                    lambda v: _set_rubricator(app, v),
                    multiline=True,
                ),
                c.field("Выходныя сведенiя", brand.imprint, lambda v: set_quiet("imprint", v),
                        multiline=True),
            ],
            spacing=14,
        )
    else:
        panel_body = ft.Column(
            [
                t.hint("Одна краска на весь выпускъ.", size=11),
                ft.Row(
                    [
                        ft.Container(
                            width=26,
                            height=26,
                            bgcolor=value,
                            border=ft.Border.all(2 if value == brand.ink else 1,
                                                 t.ACCENT if value == brand.ink else t.BORDER_BASE),
                            border_radius=2,
                            on_click=(lambda value: lambda _e: _set_ink(app, value))(value),
                            ink=True,
                        )
                        for value in INKS
                    ],
                    spacing=8,
                ),
            ],
            spacing=14,
        )

    tabs = ft.Row(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=t.text(label, size=12,
                                           color=t.TEXT_PRIMARY if key == tab else t.TEXT_MUTED,
                                           weight="500" if key == tab else None),
                            alignment=ft.Alignment.CENTER,
                            expand=True,
                        ),
                        ft.Container(height=2, bgcolor=t.ACCENT if key == tab else "transparent"),
                    ],
                    spacing=0,
                ),
                height=38,
                expand=True,
                on_click=(lambda key: lambda _e: _set_tab(app, key))(key),
                ink=True,
            )
            for key, label in TABS
        ],
        spacing=0,
    )

    panel = ft.Container(
        content=ft.Column(
            [
                tabs,
                ft.Container(height=1, bgcolor=t.BORDER_PANEL),
                ft.Container(
                    content=ft.Column([panel_body], scroll=ft.ScrollMode.AUTO, expand=True),
                    padding=16,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(c.secondary_button("Дублировать", lambda _e: _duplicate(app)),
                                         expand=True),
                            ft.Container(c.primary_button("Применить",
                                                          lambda _e: _apply_to_all(app)), expand=True),
                        ],
                        spacing=10,
                    ),
                    padding=ft.Padding.symmetric(vertical=12, horizontal=16),
                ),
                ft.Container(
                    content=c.ghost_button("Вернуться къ вёрстке", lambda _e: app.navigate("layout")),
                    padding=ft.Padding.only(left=10, bottom=10),
                ),
            ],
            spacing=0,
            expand=True,
        ),
        width=340,
        bgcolor=t.BG_RAIL,
        border=ft.Border.only(left=ft.BorderSide(1, t.BORDER_PANEL)),
    )

    return ft.Row([rail, center, panel], spacing=0, expand=True)


def _set_tab(app: AppState, key: str) -> None:
    app.brand_tab = key
    app.rebuild()


def _set_direction(app: AppState, key: str, font: str) -> None:
    brand = app.project.brand
    brand.logo_direction = key
    brand.logo_font = font
    app.touch(rebuild=True)


def _set_ink(app: AppState, value: str) -> None:
    app.project.brand.ink = value
    app.project.style.ink_color = value
    app.touch(rebuild=True)


def _set_rubricator(app: AppState, value: str) -> None:
    app.project.brand.rubricator = [line.strip() for line in value.splitlines() if line.strip()]
    app.touch()


def _use_brand(app: AppState, brand: Brand) -> None:
    app.project.brand = brand
    app.touch(rebuild=True, immediate=True)


def _new_brand(app: AppState) -> None:
    brand = Brand(name_latin="New Title", name_cyrillic="Новое изданiе")
    storage.save_brand(brand)
    app.project.brand = brand
    app.touch(rebuild=True)


def _duplicate(app: AppState) -> None:
    import dataclasses

    from ..models import new_id

    copy = dataclasses.replace(app.project.brand, id=new_id("brand"))
    copy.name_cyrillic = f"{copy.name_cyrillic} (копiя)"
    storage.save_brand(copy)
    app.project.brand = copy
    app.touch(rebuild=True)


def _apply_to_all(app: AppState) -> None:
    """Обновляетъ шапку во всехъ сохранённыхъ номерахъ этого изданiя."""
    brand = app.project.brand
    storage.save_brand(brand)
    updated = 0
    for entry in storage.issues_of_title(app.project.issue.title):
        path = pathlib.Path(entry.path)
        if app.project_path and path == app.project_path:
            continue
        try:
            project = storage.load_project(path)
        except OSError:
            continue
        project.brand = brand
        storage.save_project(project, path)
        updated += 1
    app.autosave_stamp = f"брендъ → {updated} вып."
    app.touch(rebuild=True)
