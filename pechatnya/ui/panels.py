"""Правая колонка вёрстки: вкладки «Стиль | Типографика | Блокъ | Бумага».

Панели живут внутри главного экрана (README, экран 07): полоса остаётся видимой,
любое измененiе применяется сразу и уходитъ въ пересборку превью.
"""

from __future__ import annotations

import pathlib

import flet as ft

from .. import fonts, storage
from ..models import ImageRef
from ..presets import MODULE_TITLES, STYLE_PRESETS, apply_preset
from . import common as c
from . import theme as t
from .state import AppState

TABS = [("style", "Стиль"), ("typography", "Типографика"), ("block", "Блокъ"), ("paper", "Бумага")]

INK_SWATCHES = ["#15120e", "#1f2a44", "#6b3226", "#2a3a2c"]
PAPER_SWATCHES = ["#efe7d4", "#f1ece0", "#eae5d9", "#f0eee6", "#e8e0cd", "#e4ded0"]


def build(app: AppState) -> ft.Control:
    tabs = ft.Row(
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            content=t.text(
                                label,
                                size=12,
                                color=t.TEXT_PRIMARY if key == app.panel_tab else t.TEXT_MUTED,
                                weight="500" if key == app.panel_tab else None,
                            ),
                            alignment=ft.Alignment.CENTER,
                            expand=True,
                        ),
                        ft.Container(
                            height=2,
                            bgcolor=t.ACCENT if key == app.panel_tab else "transparent",
                        ),
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

    body = {
        "style": _style_panel,
        "typography": _typography_panel,
        "block": _block_panel,
        "paper": _paper_panel,
    }[app.panel_tab](app)

    return ft.Container(
        content=ft.Column(
            [
                tabs,
                ft.Container(height=1, bgcolor=t.BORDER_PANEL),
                ft.Container(
                    content=ft.Column([body], scroll=ft.ScrollMode.AUTO, expand=True),
                    padding=ft.Padding.symmetric(vertical=16, horizontal=16),
                    expand=True,
                ),
                ft.Container(height=1, bgcolor=t.BORDER_PANEL),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                c.secondary_button("Сохранить", lambda _e: _save(app)),
                                expand=True,
                            ),
                            ft.Container(
                                c.primary_button("Экспортъ…", lambda _e: app.navigate("export")),
                                expand=True,
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
        width=312,
        bgcolor=t.BG_RAIL,
        border=ft.Border.only(left=ft.BorderSide(1, t.BORDER_PANEL)),
    )


def _set_tab(app: AppState, key: str) -> None:
    app.panel_tab = key
    app.rebuild()


def _save(app: AppState) -> None:
    app.save()
    app.rebuild()


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


# ------------------------------------------------------------------------ стиль


def _style_panel(app: AppState) -> ft.Control:
    project = app.project
    style = project.style

    def pick_preset(preset_id: str) -> None:
        apply_preset(project, preset_id)
        app.touch(rebuild=True)

    def set_value(field: str, value) -> None:
        setattr(style, field, value)
        app.touch(rebuild=True)

    return ft.Column(
        [
            c.panel_section(
                "Пресетъ полосы",
                c.chip_row(
                    [(preset.id, preset.name) for preset in STYLE_PRESETS],
                    style.preset_id,
                    pick_preset,
                    height=28,
                ),
                spacing=10,
            ),
            c.panel_section("Бумага", _swatches(PAPER_SWATCHES, style.paper_color,
                                                lambda value: set_value("paper_color", value)),
                            spacing=10),
            c.panel_section("Краска", _swatches(INK_SWATCHES, style.ink_color,
                                                lambda value: _set_ink(app, value)), spacing=10),
            c.panel_section(
                "Рамка шапки",
                c.segment(
                    [("none", "Нѣтъ"), ("double_rule", "Линейка"), ("ornament", "Орнаментъ")],
                    style.masthead_frame,
                    lambda value: set_value("masthead_frame", value),
                ),
                spacing=10,
            ),
            c.panel_section(
                "Приёмы набора",
                c.toggle("Межколоночныя линейки", style.column_rules,
                         lambda value: set_value("column_rules", value)),
                c.toggle("Растеканiе краски", style.ink_spread,
                         lambda value: set_value("ink_spread", value)),
                c.toggle("Заголовки капителью", style.uppercase_headlines,
                         lambda value: set_value("uppercase_headlines", value)),
                c.toggle("Рубрики вывороткой", style.invert_rubrics,
                         lambda value: set_value("invert_rubrics", value)),
                spacing=12,
            ),
            c.panel_section(
                "Шапка",
                c.secondary_button("Экранъ бренда изданiя", lambda _e: app.navigate("brand")),
                spacing=10,
            ),
        ],
        spacing=22,
    )


def _set_ink(app: AppState, value: str) -> None:
    app.project.style.ink_color = value
    app.project.brand.ink = value
    app.touch(rebuild=True)


# ------------------------------------------------------------------ типографика


def _typography_panel(app: AppState) -> ft.Control:
    typo = app.project.typography
    families = fonts.available_families()

    def set_font(field: str):
        def handler(value: str) -> None:
            setattr(typo, field, value)
            app.touch(rebuild=True)

        return handler

    def size_field(label: str, field: str, step: float = 0.5, decimals: int = 1) -> ft.Control:
        return c.stepper(
            label,
            getattr(typo, field),
            lambda value: (setattr(typo, field, value), app.touch())[0],
            step=step,
            minimum=4,
            maximum=140,
            decimals=decimals,
            width=92,
        )

    warn = [
        name
        for name in (typo.heading_font, typo.body_font, typo.caption_font)
        if not fonts.supports_cyrillic(name)
    ]
    note = (
        f"Въ гарнитуре «{warn[0]}» нѣтъ кириллицы — она подменяется "
        f"на {fonts.FALLBACK_FOR_CYRILLIC}."
        if warn
        else "Списокъ — встроенныя гарнитуры и установленныя въ системе."
    )

    sample = ft.Container(
        content=ft.Row(
            [
                ft.Text("Н", size=40, color="#15120e", font_family=f"{typo.heading_font} Bold"),
                ft.Container(
                    ft.Text(
                        "очью, около половины перваго, въ третьемъ пролёте Нижняго дока "
                        "обрушилась часть кровли.",
                        size=11,
                        color="#1c1812",
                        font_family=typo.body_font,
                        text_align=ft.TextAlign.JUSTIFY,
                    ),
                    expand=True,
                ),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=app.project.style.paper_color,
        padding=10,
        border_radius=4,
    )

    return ft.Column(
        [
            c.panel_section(
                "Гарнитуры",
                c.select("Заголовки", typo.heading_font, families, set_font("heading_font")),
                c.select("Основной текстъ", typo.body_font, families, set_font("body_font")),
                c.select("Рубрики и подписи", typo.caption_font, families, set_font("caption_font")),
                t.hint(note, size=11, color=t.TEXT_FAINTER),
                spacing=12,
            ),
            c.panel_section(
                "Кегли, пт",
                size_field("Названiе изданiя", "masthead_pt"),
                size_field("Главный заголовокъ", "lead_headline_pt"),
                size_field("Заголовокъ статьи", "article_headline_pt"),
                size_field("Основной текстъ", "body_pt", step=0.1, decimals=1),
                c.stepper(
                    "Интерлиньяжъ",
                    typo.leading,
                    lambda value: (setattr(typo, "leading", value), app.touch())[0],
                    step=0.02,
                    minimum=1.0,
                    maximum=2.4,
                    decimals=2,
                    width=92,
                ),
                spacing=12,
            ),
            c.panel_section("Образецъ", sample, spacing=10),
        ],
        spacing=22,
    )


# ------------------------------------------------------------------------ блокъ


def _block_panel(app: AppState) -> ft.Control:
    block = app.selected_block
    if block is None:
        return ft.Column(
            [
                t.caps("Блокъ не выбранъ"),
                t.hint(
                    "Щёлкните по блоку на полосе — здесь появятся колонки, выключка, "
                    "буквица и картинка. Двойной щелчокъ открываетъ редакторъ статьи.",
                    size=12,
                ),
            ],
            spacing=10,
        )

    fit = app.fit_of(block.id)
    percent = fit.percent if fit else 0.0
    article = app.project.article(block.article_id)

    def set_value(field: str, value) -> None:
        setattr(block, field, value)
        app.touch(rebuild=True)

    caption = (
        f"{percent:.0f} % высоты блока"
        if percent <= 100
        else f"не помещается: {fit.overflow_chars if fit else 0} зн."
    )
    selection_card = c.card(
        ft.Column(
            [
                t.text(block.label, size=13, color=t.TEXT_PRIMARY, weight="500"),
                t.hint(
                    f"{'Статья' if article else 'Модули' if block.modules else 'Пустой блокъ'}"
                    f" · {block.columns} кол. · {int(fit.width) if fit else 0}×{int(fit.height) if fit else 0} px",
                    size=11,
                    color=t.TEXT_MUTED,
                ),
                c.fill_bar(percent),
                t.hint(caption, size=11, color=t.OK_TEXT if percent <= 100 else t.WARN),
                *(
                    [
                        c.secondary_button(
                            "Править статью",
                            lambda _e, article_id=article.id: _edit_article(app, article_id),
                            height=30,
                        )
                    ]
                    if article
                    else []
                ),
            ],
            spacing=8,
        )
    )

    image_section: list[ft.Control] = []
    if article is not None:
        image = article.image
        if image is not None:
            image_section = [
                c.panel_section(
                    "Изображенiе",
                    ft.Row(
                        [
                            ft.Container(
                                content=(
                                    ft.Image(
                                        src=str(_image_path(app, image)),
                                        width=64,
                                        height=46,
                                        fit=ft.BoxFit.COVER,
                                    )
                                    if _image_path(app, image)
                                    else ft.Text("нѣтъ", size=10, color=t.TEXT_FAINT)
                                ),
                                width=64,
                                height=46,
                                bgcolor=t.BG_CONTROL,
                                alignment=ft.Alignment.CENTER,
                                border_radius=2,
                            ),
                            ft.Column(
                                [
                                    t.text(
                                        pathlib.Path(image.path).name or "не выбрано",
                                        size=12,
                                        font=t.MONO,
                                        color=t.TEXT_SECONDARY,
                                    ),
                                    t.hint(f"высота въ блоке {image.height_px} px", size=11),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    c.chip_row(
                        [("halftone", "Полутонъ"), ("sepia", "Сепiя"), ("bw", "Ч/Б"), ("none", "Безъ")],
                        image.filter,
                        lambda value: _set_image_filter(app, value),
                        height=28,
                    ),
                    c.stepper(
                        "Высота, px",
                        image.height_px,
                        lambda value: _set_image_height(app, int(value)),
                        step=8,
                        minimum=40,
                        maximum=420,
                        width=110,
                    ),
                    c.field(
                        "Подпись",
                        image.caption,
                        lambda value: _set_image_caption(app, value),
                    ),
                    c.ghost_button("Убрать снимокъ", lambda _e: _drop_image(app)),
                    spacing=10,
                )
            ]
        else:
            image_section = [
                c.panel_section(
                    "Изображенiе",
                    c.secondary_button("Вставить фото…", lambda _e: app.page.run_task(_pick_image, app)),
                    spacing=10,
                )
            ]

    modules_section: list[ft.Control] = []
    if not article:
        modules_section = [
            c.panel_section(
                "Модули въ блоке",
                ft.Column(
                    [
                        ft.Row(
                            [
                                t.text(MODULE_TITLES.get(module.kind, module.kind), size=12,
                                       color=t.TEXT_SECONDARY, expand=True),
                                ft.Container(
                                    ft.Icon(ft.Icons.CLOSE, size=13, color=t.TEXT_FAINT),
                                    on_click=(lambda index: lambda _e: _remove_module(app, index))(index),
                                    padding=4,
                                    ink=True,
                                ),
                            ]
                        )
                        for index, module in enumerate(block.modules)
                    ],
                    spacing=6,
                )
                if block.modules
                else t.hint("Пусто — добавьте модуль изъ левой панели", size=11),
                spacing=8,
            )
        ]

    return ft.Column(
        [
            selection_card,
            c.panel_section(
                "Наборъ",
                c.stepper(
                    "Колонокъ въ блоке",
                    block.columns,
                    lambda value: set_value("columns", int(value)),
                    minimum=1,
                    maximum=6,
                    width=110,
                ),
                c.toggle("Буквица у лида", block.drop_cap, lambda value: set_value("drop_cap", value)),
                c.toggle("Межколоночныя линейки", block.column_rules,
                         lambda value: set_value("column_rules", value)),
                c.toggle("Переносы словъ", block.hyphens, lambda value: set_value("hyphens", value)),
                spacing=12,
            ),
            c.panel_section(
                "Выключка",
                c.segment(
                    [("left", "Влево"), ("justify", "По ширине"), ("center", "Центръ")],
                    block.align,
                    lambda value: set_value("align", value),
                ),
                spacing=10,
            ),
            c.panel_section(
                "Заголовокъ",
                c.stepper(
                    "Масштабъ кегля",
                    block.headline_scale,
                    lambda value: set_value("headline_scale", value),
                    step=0.05,
                    minimum=0.2,
                    maximum=2.0,
                    decimals=2,
                    width=110,
                ),
                spacing=10,
            ),
            *image_section,
            *modules_section,
            *(
                [
                    c.panel_section(
                        "Статья",
                        c.secondary_button(
                            "Открыть редакторъ",
                            lambda _e: _edit_article(app, article.id),
                        ),
                        c.ghost_button("Снять съ полосы", lambda _e: _detach(app, article.id)),
                        spacing=10,
                    )
                ]
                if article
                else []
            ),
        ],
        spacing=22,
    )


def _image_path(app: AppState, image: ImageRef):
    if not image.path:
        return None
    path = pathlib.Path(image.path)
    if not path.is_absolute() and app.project_dir:
        path = app.project_dir / path
    return path if path.exists() else None


def _set_image_filter(app: AppState, value: str) -> None:
    article = app.project.article(app.selected_block.article_id) if app.selected_block else None
    if article and article.image:
        article.image.filter = value
        app.touch(rebuild=True)


def _set_image_height(app: AppState, value: int) -> None:
    article = app.project.article(app.selected_block.article_id) if app.selected_block else None
    if article and article.image:
        article.image.height_px = value
        app.touch()


def _set_image_caption(app: AppState, value: str) -> None:
    article = app.project.article(app.selected_block.article_id) if app.selected_block else None
    if article and article.image:
        article.image.caption = value
        app.touch()


def _drop_image(app: AppState) -> None:
    article = app.project.article(app.selected_block.article_id) if app.selected_block else None
    if article:
        article.image = None
        app.touch(rebuild=True)


async def _pick_image(app: AppState) -> None:
    files = await app.file_picker().pick_files(
        dialog_title="Выберите изображенiе",
        allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
    )
    if not files:
        return
    block = app.selected_block
    article = app.project.article(block.article_id) if block else None
    if article is None:
        return
    relative = storage.import_image(pathlib.Path(files[0].path), app.project_path)
    article.image = ImageRef(path=relative, caption="", height_px=96)
    app.touch(rebuild=True)


def _remove_module(app: AppState, index: int) -> None:
    block = app.selected_block
    if block and 0 <= index < len(block.modules):
        block.modules.pop(index)
        if not block.modules:
            block.kind = "empty"
        app.touch(rebuild=True)


def _edit_article(app: AppState, article_id: str) -> None:
    app.editing_article_id = article_id
    app.navigate("article")


def _detach(app: AppState, article_id: str) -> None:
    app.project.detach(article_id)
    app.touch(rebuild=True, immediate=True)


# ----------------------------------------------------------------------- бумага


def _paper_panel(app: AppState) -> ft.Control:
    paper = app.project.paper

    def set_value(field: str, value) -> None:
        setattr(paper, field, value)
        app.touch(rebuild=True)

    def set_intensity(value: float) -> None:
        paper.intensity = int(value)
        app.touch()

    sample = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "ПРОБА ОТТИСКА",
                    size=10,
                    color="#15120e",
                    font_family="PT Sans Narrow Bold",
                ),
                ft.Text(
                    "Рукописи не возвращаются. Подписка на мѣсяцъ — одинъ рубль двадцать копеекъ.",
                    size=10,
                    color="#1c1812",
                    font_family="PT Serif",
                    text_align=ft.TextAlign.JUSTIFY,
                ),
            ],
            spacing=6,
        ),
        bgcolor=app.project.style.paper_color,
        padding=10,
        height=132,
        border_radius=4,
        opacity=1 - (paper.intensity / 100 * 0.25 if paper.enabled else 0),
    )

    return ft.Column(
        [
            c.toggle("Состариванiе", paper.enabled, lambda value: set_value("enabled", value)),
            c.panel_section(
                "Интенсивность",
                c.slider(paper.intensity, set_intensity, 0, 100, divisions=100),
                ft.Row(
                    [
                        t.hint("0 — чистый листъ", size=11, color=t.TEXT_FAINTER),
                        t.hint("100 — потрёпанный", size=11, color=t.TEXT_FAINTER),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                spacing=6,
            ),
            c.panel_section(
                "Составляющiя",
                c.checkbox("Желтизна и сепiя", paper.yellowing, lambda v: set_value("yellowing", v)),
                c.checkbox("Пятна и разводы", paper.stains, lambda v: set_value("stains", v)),
                c.checkbox("Неравномерность печати", paper.unevenness,
                           lambda v: set_value("unevenness", v)),
                c.checkbox("Заломы и сгибы", paper.folds, lambda v: set_value("folds", v)),
                c.checkbox("Зерно скана", paper.grain, lambda v: set_value("grain", v)),
                spacing=4,
            ),
            c.panel_section("Проба", sample, spacing=10),
            t.hint(
                "Эффектъ применяется ко всей полосе, включая изображенiя, "
                "и учитывается при экспорте.",
                size=11,
                color=t.TEXT_FAINTER,
            ),
        ],
        spacing=22,
    )
