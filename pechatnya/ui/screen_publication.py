"""Издания: библиотека и редактор облика газеты.

Издание — постоянный облик: логотип, девиз, рубрикатор, служебные строки шапки,
шрифты, кегли и краски. Выпуски его наследуют, поэтому оформление правится
здесь, а не в каждом номере.
"""

from __future__ import annotations

import flet as ft

from .. import fonts, storage
from ..presets import STYLE_PRESETS, PRESETS_BY_ID
from . import common as c
from . import theme as t
from . import thumbs
from .state import AppState

LOGO_PRESETS = [
    ("antiqua", "Антиква", "Old Standard TT"),
    ("gothic", "Готический", "UnifrakturMaguntia"),
    ("modern", "Новая антиква", "Bodoni Moda"),
    ("narrow", "Узкий гротеск", "Oswald"),
    ("framed", "В рамке", "PT Sans Narrow"),
]
RULE_STYLES = [("single", "Одна"), ("bold_thin", "Жирная и тонкая"), ("ornament", "Орнамент")]
INKS = ["#15120e", "#1f2a44", "#6b3226", "#2a3a2c"]
PAPERS = ["#efe7d4", "#f1ece0", "#eae5d9", "#f0eee6", "#e8e0cd", "#e4ded0"]
TABS = [("logo", "Логотип"), ("sections", "Рубрики и шапка"), ("design", "Оформление")]


def build(app: AppState) -> ft.Control:
    item = app.editing_publication
    if item is None:
        item = app.start_editing_publication()
    tab = app.publication_tab
    brand = item.brand

    def touch(rebuild: bool = True) -> None:
        app.publication_dirty = True
        if rebuild:
            app.rebuild()

    def brand_field(name: str):
        def handler(value) -> None:
            setattr(brand, name, value)
            app.publication_dirty = True

        return handler

    def brand_toggle(name: str):
        def handler(value) -> None:
            setattr(brand, name, value)
            touch()

        return handler

    def pub_field(name: str):
        def handler(value) -> None:
            setattr(item, name, value)
            app.publication_dirty = True

        return handler

    # ------------------------------------------------------------ левая панель
    counts = {
        entry.publication_id: 0 for entry in storage.recent_projects(99)
    }
    for entry in storage.recent_projects(99):
        counts[entry.publication_id] = counts.get(entry.publication_id, 0) + 1

    rows = []
    for saved in app.publications:
        issues = counts.get(saved.id, 0)
        rows.append(
            c.list_row(
                ft.Column(
                    [
                        t.text(saved.display_name, size=12, color=t.TEXT_PRIMARY),
                        t.hint(
                            f"{saved.brand.logo_font} · выпусков: {issues}",
                            size=10,
                            color=t.TEXT_FAINTER,
                        ),
                    ],
                    spacing=2,
                ),
                active=saved.id == item.id,
                on_click=(lambda saved: lambda _e: app.edit_publication(saved.id))(saved),
                height=52,
            )
        )

    rail = c.rail(
        ft.Column(
            [
                t.caps("Издания"),
                ft.Column(rows, spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
                if rows
                else ft.Container(
                    t.hint("Пока ни одного издания.", size=11), padding=ft.Padding.only(top=6)
                ),
                ft.Container(
                    content=t.text("+ Новое издание", size=12, color=t.TEXT_SECONDARY),
                    height=40,
                    alignment=ft.Alignment.CENTER,
                    border=ft.Border.all(1, t.BORDER_STRONG),
                    border_radius=t.RADIUS_CONTROL,
                    on_click=lambda _e: app.new_publication(),
                    ink=True,
                ),
                t.hint(
                    "Издание задаёт постоянный облик газеты. Все его выпуски наследуют "
                    "шапку, шрифты и краски: правка здесь меняет их во всех номерах, "
                    "вёрстка остаётся.",
                    size=11,
                    color=t.TEXT_FAINTER,
                ),
            ],
            spacing=12,
            expand=True,
        ),
        width=256,
    )

    # ----------------------------------------------------------------- центр
    logo_font = fonts.resolve_for_text(brand.logo_font, brand.display_name)
    masthead = thumbs.masthead_preview(
        brand.display_name or "Название издания",
        brand.motto if brand.motto_enabled else "",
        "1",
        item.city,
        "дата выпуска",
        item.price,
        rules_style=brand.rules_style,
        logo_font=f"{logo_font} Bold" if logo_font != "UnifrakturMaguntia" else logo_font,
        width=700,
    )

    preset_cards = ft.Row(
        [
            ft.Container(
                content=c.card(
                    ft.Column(
                        [
                            thumbs.paper_thumb(
                                height=118,
                                logo=(brand.display_name or "ИЗДАНИЕ").upper()[:14],
                                logo_font=f"{preset.typography.heading_font} Bold",
                                logo_size=11,
                                paper=preset.style.paper_color,
                                columns=3 if preset.style.column_rules else 1,
                                rules=1 if preset.style.masthead_rule_weight < 2 else 2,
                                halftone=False,
                                invert=preset.style.invert_rubrics,
                                accent=preset.style.accent_ink
                                if preset.style.invert_rubrics
                                else preset.style.ink_color,
                            ),
                            t.text(preset.name, size=12, color=t.TEXT_PRIMARY, weight="500"),
                            t.hint(preset.description, size=10, color=t.TEXT_MUTED),
                        ],
                        spacing=6,
                    ),
                    active=item.style.preset_id == preset.id,
                    on_click=(lambda key: lambda _e: _apply_preset(app, key))(preset.id),
                    padding=10,
                ),
                expand=True,
            )
            for index, preset in enumerate(STYLE_PRESETS)
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    center = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                t.text("Облик издания", size=20, color=t.TEXT_PRIMARY, weight="600"),
                                t.hint("Так шапка встанет на полосу", size=12, color=t.TEXT_MUTED),
                            ],
                            spacing=4,
                        ),
                        t.hint(
                            "изменения сохраняются кнопкой внизу справа",
                            size=11,
                            color=t.TEXT_FAINTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                masthead,
                c.panel_section("Готовые наборы оформления", preset_cards, spacing=12),
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=ft.Padding.symmetric(vertical=24, horizontal=26),
        expand=True,
    )

    # ------------------------------------------------------------ правая панель
    if tab == "logo":
        warn = (
            t.hint(
                f"В гарнитуре «{brand.logo_font}» нет кириллицы — кириллическое название "
                f"будет набрано шрифтом {fonts.FALLBACK_FOR_CYRILLIC}.",
                size=11,
                color=t.WARN,
            )
            if not fonts.supports_cyrillic(brand.logo_font)
            else t.hint("Гарнитура содержит кириллицу.", size=11, color=t.TEXT_FAINTER)
        )
        panel_body = ft.Column(
            [
                c.field("Название издания", brand.name_cyrillic, brand_field("name_cyrillic"),
                        hint="Например: Голос дока"),
                c.field("Название латиницей", brand.name_latin, brand_field("name_latin"),
                        hint="не обязательно"),
                c.toggle("Набирать кириллицей", brand.use_cyrillic, brand_toggle("use_cyrillic")),
                c.panel_section(
                    "Шрифт логотипа",
                    c.chip_row(
                        [(key, label) for key, label, _ in LOGO_PRESETS],
                        brand.logo_font_preset,
                        lambda key: _set_logo_preset(app, key),
                        height=28,
                    ),
                    c.select("", brand.logo_font, fonts.available_families(),
                             lambda value: _set_logo_font(app, value)),
                    warn,
                    spacing=10,
                ),
                c.stepper("Кегль логотипа, пт", brand.logo_size_pt,
                          lambda value: (setattr(brand, "logo_size_pt", value), touch(False))[0],
                          step=1, minimum=10, maximum=160, decimals=1, width=110),
                c.stepper("Разрядка, ‰", brand.tracking_permille,
                          lambda value: (setattr(brand, "tracking_permille", int(value)),
                                         touch(False))[0],
                          step=5, minimum=-50, maximum=400, width=110),
                c.toggle("Строка над названием", brand.superline_enabled,
                         brand_toggle("superline_enabled")),
                *([c.field("", brand.superline, brand_field("superline"),
                           hint="например: ВЕЧЕРНИЙ")]
                  if brand.superline_enabled else []),
                c.toggle("Девиз под названием", brand.motto_enabled, brand_toggle("motto_enabled")),
                *([c.field("", brand.motto, brand_field("motto"), hint="девиз издания")]
                  if brand.motto_enabled else []),
                c.panel_section(
                    "Линейки под шапкой",
                    c.chip_row(RULE_STYLES, brand.rules_style,
                               lambda value: (setattr(brand, "rules_style", value), touch())[0],
                               height=28),
                    spacing=10,
                ),
            ],
            spacing=14,
        )
    elif tab == "sections":
        panel_body = ft.Column(
            [
                c.field("Рубрики под шапкой", "\n".join(brand.rubricator),
                        lambda value: _set_rubricator(app, value), multiline=True,
                        hint="по одной в строке"),
                c.field("Левый блок шапки", item.masthead_left, pub_field("masthead_left"),
                        hint="подписка|1 р. 20 к.|с доставкой"),
                c.field("Правый блок шапки", item.masthead_right, pub_field("masthead_right"),
                        hint="объявления|8 к. за строку|позади текста"),
                t.hint("Три части через вертикальную черту: заголовок | крупная строка | пояснение",
                       size=11, color=t.TEXT_FAINTER),
                c.field("Год издания", item.year_line, pub_field("year_line"),
                        hint="например: год издания шестой"),
                c.field("Город", item.city, pub_field("city")),
                c.field("Цена по умолчанию", item.price, pub_field("price")),
                c.field("Выходные сведения", brand.imprint, brand_field("imprint"), multiline=True,
                        hint="адрес редакции, типография"),
            ],
            spacing=14,
        )
    else:
        typo = item.typography
        families = fonts.available_families()

        def set_font(name: str):
            def handler(value: str) -> None:
                setattr(typo, name, value)
                touch()

            return handler

        def size(label: str, name: str, step: float = 0.5) -> ft.Control:
            return c.stepper(
                label, getattr(typo, name),
                lambda value: (setattr(typo, name, value), touch(False))[0],
                step=step, minimum=4, maximum=140, decimals=1, width=92,
            )

        panel_body = ft.Column(
            [
                c.panel_section("Бумага", _swatches(PAPERS, item.style.paper_color,
                                                    lambda value: _set_style(app, "paper_color", value)),
                                spacing=10),
                c.panel_section("Краска", _swatches(INKS, item.style.ink_color,
                                                    lambda value: _set_ink(app, value)), spacing=10),
                c.panel_section(
                    "Гарнитуры",
                    c.select("Заголовки", typo.heading_font, families, set_font("heading_font")),
                    c.select("Основной текст", typo.body_font, families, set_font("body_font")),
                    c.select("Рубрики и подписи", typo.caption_font, families,
                             set_font("caption_font")),
                    spacing=10,
                ),
                c.panel_section(
                    "Кегли, пт",
                    size("Главный заголовок", "lead_headline_pt"),
                    size("Заголовок статьи", "article_headline_pt"),
                    size("Основной текст", "body_pt", step=0.1),
                    c.stepper("Интерлиньяж", typo.leading,
                              lambda value: (setattr(typo, "leading", value), touch(False))[0],
                              step=0.02, minimum=1.0, maximum=2.4, decimals=2, width=92),
                    spacing=10,
                ),
                c.panel_section(
                    "Наборная типографика",
                    c.toggle("Кавычки-ёлочки, тире, неразрывные пробелы",
                             item.style.typography_polish,
                             lambda value: _set_style(app, "typography_polish", value)),
                    c.toggle("Не обрезать строку пополам", item.style.trim_partial_lines,
                             lambda value: _set_style(app, "trim_partial_lines", value)),
                    t.hint(
                        "Текст в статьях остаётся как набран — правки делаются только "
                        "при вёрстке полосы.",
                        size=11,
                    ),
                    spacing=12,
                ),
                c.panel_section(
                    "Приёмы набора",
                    c.toggle("Межколоночные линейки", item.style.column_rules,
                             lambda value: _set_style(app, "column_rules", value)),
                    c.toggle("Растекание краски", item.style.ink_spread,
                             lambda value: _set_style(app, "ink_spread", value)),
                    c.toggle("Заголовки прописными", item.style.uppercase_headlines,
                             lambda value: _set_style(app, "uppercase_headlines", value)),
                    c.toggle("Рубрики вывороткой", item.style.invert_rubrics,
                             lambda value: _set_style(app, "invert_rubrics", value)),
                    spacing=12,
                ),
            ],
            spacing=20,
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

    saved_hint = (
        t.hint("есть несохранённые изменения", size=11, color=t.WARN)
        if app.publication_dirty
        else t.hint("сохранено", size=11, color=t.TEXT_FAINTER)
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
                    content=ft.Column(
                        [
                            saved_hint,
                            ft.Row(
                                [
                                    ft.Container(
                                        c.secondary_button("Дублировать",
                                                           lambda _e: app.duplicate_publication()),
                                        expand=True,
                                    ),
                                    ft.Container(
                                        c.primary_button("Сохранить издание",
                                                         lambda _e: app.save_publication()),
                                        expand=True,
                                    ),
                                ],
                                spacing=10,
                            ),
                            ft.Row(
                                [
                                    c.ghost_button("Удалить издание",
                                                   lambda _e: app.delete_publication()),
                                    ft.Container(expand=True),
                                    c.ghost_button(app.publication_back_label,
                                                   lambda _e: app.leave_publications()),
                                ]
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=ft.Padding.symmetric(vertical=12, horizontal=16),
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


def _swatches(values: list[str], current: str, on_pick) -> ft.Control:
    return ft.Row(
        [
            ft.Container(
                width=26,
                height=26,
                bgcolor=value,
                border=ft.Border.all(2 if value == current else 1,
                                     t.ACCENT if value == current else t.BORDER_BASE),
                border_radius=2,
                on_click=(lambda value: lambda _e: on_pick(value))(value),
                ink=True,
            )
            for value in values
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )


def _set_tab(app: AppState, key: str) -> None:
    app.publication_tab = key
    app.rebuild()


def _apply_preset(app: AppState, preset_id: str) -> None:
    preset = PRESETS_BY_ID.get(preset_id)
    item = app.editing_publication
    if preset is None or item is None:
        return
    item.style = type(preset.style)(**vars(preset.style))
    item.typography = type(preset.typography)(**vars(preset.typography))
    item.brand.logo_font = preset.typography.heading_font
    item.brand.ink = preset.style.ink_color
    app.publication_dirty = True
    app.rebuild()


def _set_logo_preset(app: AppState, key: str) -> None:
    item = app.editing_publication
    if item is None:
        return
    item.brand.logo_font_preset = key
    item.brand.logo_font = next(font for code, _, font in LOGO_PRESETS if code == key)
    app.publication_dirty = True
    app.rebuild()


def _set_logo_font(app: AppState, value: str) -> None:
    item = app.editing_publication
    if item is None:
        return
    item.brand.logo_font = value
    app.publication_dirty = True
    app.rebuild()


def _set_rubricator(app: AppState, value: str) -> None:
    item = app.editing_publication
    if item is None:
        return
    item.brand.rubricator = [line.strip() for line in value.splitlines() if line.strip()]
    app.publication_dirty = True


def _set_style(app: AppState, name: str, value) -> None:
    item = app.editing_publication
    if item is None:
        return
    setattr(item.style, name, value)
    app.publication_dirty = True
    app.rebuild()


def _set_ink(app: AppState, value: str) -> None:
    item = app.editing_publication
    if item is None:
        return
    item.style.ink_color = value
    item.brand.ink = value
    app.publication_dirty = True
    app.rebuild()


def publication_cards(app: AppState, current_id: str, on_pick) -> ft.Control:
    """Ряд изданий для выбора в мастере выпуска."""
    cards: list[ft.Control] = []
    for item in app.publications:
        cards.append(
            ft.Container(
                content=c.card(
                    ft.Column(
                        [
                            thumbs.paper_thumb(
                                height=96,
                                logo=(item.brand.display_name or "ИЗДАНИЕ").upper()[:16],
                                logo_font=f"{item.typography.heading_font} Bold",
                                logo_size=11,
                                paper=item.style.paper_color,
                                columns=3,
                                halftone=False,
                                accent=item.style.ink_color,
                            ),
                            t.text(item.display_name, size=12, color=t.TEXT_PRIMARY, weight="500"),
                        ],
                        spacing=6,
                    ),
                    active=item.id == current_id,
                    on_click=(lambda item: lambda _e: on_pick(item))(item),
                    padding=10,
                ),
                width=170,
            )
        )
    cards.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("+", size=18, color=t.TEXT_SECONDARY),
                    t.text("Новое издание", size=12, color=t.TEXT_SECONDARY),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            width=170,
            height=152,
            border=ft.Border.all(1, t.BORDER_STRONG),
            border_radius=t.RADIUS_CONTROL,
            on_click=lambda _e: app.new_publication(from_wizard=True),
            ink=True,
        )
    )
    return ft.Row(cards, spacing=12, wrap=True, run_spacing=12)
