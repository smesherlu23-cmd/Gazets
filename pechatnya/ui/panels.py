"""Правая колонка вёрстки: вкладки «Стиль | Типографика | Блок | Бумага».

Панели живут внутри главного экрана (README, экран 07): полоса остаётся видимой,
любое изменение применяется сразу и уходит в пересборку превью.
"""

from __future__ import annotations

import pathlib

import flet as ft

from .. import storage
from ..models import ImageRef
from ..presets import MODULE_HINTS, MODULE_TITLES
from . import common as c
from . import theme as t
from .state import AppState

TABS = [("block", "Блок"), ("paper", "Бумага")]

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

    body = {"block": _block_panel, "paper": _paper_panel}.get(app.panel_tab, _block_panel)(app)

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
                                c.primary_button("Экспорт…", lambda _e: app.navigate("export")),
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


# ------------------------------------------------------------------------ блок


def _block_panel(app: AppState) -> ft.Control:
    block = app.selected_block
    if block is None:
        return ft.Column(
            [
                t.caps("Блок не выбран"),
                t.hint(
                    "Щёлкните по блоку на полосе — здесь появятся колонки, выключка, "
                    "буквица и картинка. Двойной щелчок открывает редактор статьи.",
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
    if block.article_part == 1 and article is not None:
        source = app.project.page_of_article(article.id, part=0)
        caption += f" · продолжение со стр. {source + 1}" if source is not None else ""
    selection_card = c.card(
        ft.Column(
            [
                t.text(block.label, size=13, color=t.TEXT_PRIMARY, weight="500"),
                t.hint(
                    f"{'Статья' if article else 'Модули' if block.modules else 'Пустой блок'}"
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
                    "Изображение",
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
                                    else ft.Text("нет", size=10, color=t.TEXT_FAINT)
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
                                    t.hint(f"высота в блоке {image.height_px} px", size=11),
                                ],
                                spacing=4,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    c.chip_row(
                        [("halftone", "Полутон"), ("sepia", "Сепия"), ("bw", "Ч/Б"), ("none", "Без")],
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
                    c.ghost_button("Убрать снимок", lambda _e: _drop_image(app)),
                    spacing=10,
                )
            ]
        else:
            image_section = [
                c.panel_section(
                    "Изображение",
                    c.secondary_button("Вставить фото…", lambda _e: app.page.run_task(_pick_image, app)),
                    spacing=10,
                )
            ]

    modules_section: list[ft.Control] = []
    if not article:
        editors: list[ft.Control] = []
        for index, module in enumerate(block.modules):
            editors.append(_module_editor(app, index, module))
        modules_section = [
            c.panel_section(
                "Модули в блоке",
                ft.Column(editors, spacing=14)
                if editors
                else t.hint("Пусто — добавьте модуль из левой панели", size=11),
                spacing=10,
            )
        ]

    grid_section = c.panel_section(
        "Сетка",
        ft.Row(
            [
                _grid_button(app, "Разделить вертикально", "columns",
                             lambda: app.split_block(block.id, "row")),
                _grid_button(app, "Разделить горизонтально", "rows",
                             lambda: app.split_block(block.id, "column")),
            ],
            spacing=8,
        ),
        ft.Row(
            [
                c.chip("Сдвинуть назад", False, lambda _e: app.move_block(block.id, -1),
                       height=28),
                c.chip("Сдвинуть вперёд", False, lambda _e: app.move_block(block.id, 1),
                       height=28),
                c.chip("Удалить блок", False, lambda _e: app.remove_block(block.id), height=28),
            ],
            spacing=8,
            wrap=True,
            run_spacing=8,
        ),
        t.hint(
            "Блок делится пополам, соседи занимают освободившееся место. "
            "Границы тянутся мышью прямо на полосе.",
            size=11,
        ),
        spacing=10,
    )

    style_section = c.panel_section(
        "Оформление блока",
        c.segment(
            [("none", "Без рамки"), ("hairline", "Тонкая"), ("double", "Двойная"),
             ("bold", "Жирная")],
            block.frame,
            lambda value: set_value("frame", value),
        ),
        c.toggle("Плашка-подложка", block.tint, lambda value: set_value("tint", value)),
        c.stepper(
            "Отступ внутри, px",
            block.padding,
            lambda value: set_value("padding", value),
            step=2,
            minimum=0,
            maximum=40,
            width=104,
        ),
        c.stepper(
            "Кегль текста",
            block.body_scale,
            lambda value: set_value("body_scale", value),
            step=0.05,
            minimum=0.6,
            maximum=1.8,
            decimals=2,
            width=104,
        ),
        c.stepper(
            "Средник, px",
            block.column_gap,
            lambda value: set_value("column_gap", value),
            step=1,
            minimum=4,
            maximum=40,
            width=104,
        ),
        spacing=10,
    )

    return ft.Column(
        [
            selection_card,
            grid_section,
            c.panel_section(
                "Набор",
                c.stepper(
                    "Колонок в блоке",
                    block.columns,
                    lambda value: set_value("columns", int(value)),
                    minimum=1,
                    maximum=6,
                    width=110,
                ),
                c.toggle("Буквица у лида", block.drop_cap, lambda value: set_value("drop_cap", value)),
                c.toggle("Межколоночныя линейки", block.column_rules,
                         lambda value: set_value("column_rules", value)),
                c.toggle("Переносы слов", block.hyphens, lambda value: set_value("hyphens", value)),
                spacing=12,
            ),
            c.panel_section(
                "Выключка",
                c.segment(
                    [("left", "Влево"), ("justify", "По ширине"), ("center", "Центр")],
                    block.align,
                    lambda value: set_value("align", value),
                ),
                spacing=10,
            ),
            c.panel_section(
                "Заголовок",
                c.stepper(
                    "Масштаб кегля",
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
            style_section,
            *(_continuation_section(app, article, block) if article else []),
            *(
                [
                    c.panel_section(
                        "Статья",
                        c.secondary_button(
                            "Открыть редактор",
                            lambda _e: _edit_article(app, article.id),
                        ),
                        c.ghost_button("Снять с полосы", lambda _e: _detach(app, article.id)),
                        spacing=10,
                    )
                ]
                if article
                else []
            ),
        ],
        spacing=22,
    )


def _grid_button(app: AppState, label: str, glyph: str, action) -> ft.Control:
    """Кнопка деления блока с маленькой схемой того, что получится."""
    if glyph == "columns":
        icon = ft.Row(
            [
                ft.Container(width=8, height=18, bgcolor=t.BORDER_STRONG),
                ft.Container(width=8, height=18, bgcolor=t.ACCENT),
            ],
            spacing=2,
        )
    else:
        icon = ft.Column(
            [
                ft.Container(width=18, height=8, bgcolor=t.BORDER_STRONG),
                ft.Container(width=18, height=8, bgcolor=t.ACCENT),
            ],
            spacing=2,
        )
    return ft.Container(
        content=ft.Row([icon], tight=True, alignment=ft.MainAxisAlignment.CENTER),
        width=64,
        height=40,
        alignment=ft.Alignment.CENTER,
        bgcolor=t.BG_CONTROL,
        border=ft.Border.all(1, t.BORDER_BASE),
        border_radius=t.RADIUS_CONTROL,
        on_click=lambda _e: action(),
        ink=True,
        tooltip=label,
    )


def _continuation_section(app: AppState, article, block) -> list[ft.Control]:
    """Перенос остатка статьи на другую полосу — там, где видно переполнение."""
    if block.article_part == 1:
        return [
            c.panel_section(
                "Продолжение",
                t.hint(
                    "Это окончание статьи. Текст делится автоматически: правьте начало "
                    "на исходной полосе, остаток подтянется сюда.",
                    size=11,
                ),
                c.ghost_button("Убрать перенос", lambda _e: app.drop_split(article.id)),
                spacing=10,
            )
        ]

    pages = len(app.project.pages)
    current_page = app.project.page_of_article(article.id, part=0)
    target = app.continuation_target or (
        article.continued_on or min(pages, (current_page or 0) + 2)
    )
    controls: list[ft.Control] = [
        c.stepper(
            "Полоса",
            target,
            lambda value: _set_target(app, int(value)),
            minimum=1,
            maximum=max(1, pages),
            width=104,
        ),
        c.secondary_button(
            "Перенести остаток",
            lambda _e: app.split_article(article.id, int(target) - 1),
            height=30,
        ),
    ]
    if article.split_at is not None:
        if article.split_is_stale:
            controls.append(
                t.hint(
                    "Текст правили после переноса — точку разрыва надо пересчитать.",
                    size=11,
                    color=t.WARN,
                )
            )
            controls.append(
                c.secondary_button(
                    "Подогнать перенос",
                    lambda _e: app.split_article(article.id, (article.continued_on or 1) - 1),
                    height=30,
                )
            )
        else:
            controls.append(
                t.hint(
                    f"Перенесено {len(article.part_text(1))} зн. на стр. {article.continued_on}",
                    size=11,
                    color=t.OK_TEXT,
                )
            )
        controls.append(c.ghost_button("Убрать перенос", lambda _e: app.drop_split(article.id)))
    else:
        controls.append(
            t.hint(
                "Программа подберёт точку разрыва так, чтобы начало влезло в блок, "
                "и поставит строки «продолжение на стр.» и «начало на стр.».",
                size=11,
            )
        )
    return [c.panel_section("Продолжение на другой полосе", *controls, spacing=10)]


def _set_target(app: AppState, value: int) -> None:
    app.continuation_target = value


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
        dialog_title="Выберите изображение",
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


def _module_editor(app: AppState, index: int, module) -> ft.Control:
    """Карточка модуля: заголовок и содержимое правятся прямо здесь."""

    def field(name: str):
        def handler(value) -> None:
            setattr(module, name, value)
            app.touch()

        return handler

    def set_row(row_index: int, cell: int):
        def handler(value) -> None:
            while len(module.rows) <= row_index:
                module.rows.append(["", ""])
            row = module.rows[row_index]
            while len(row) < 2:
                row.append("")
            row[cell] = value
            app.touch()

        return handler

    controls: list[ft.Control] = [
        ft.Row(
            [
                t.caps(MODULE_TITLES.get(module.kind, module.kind), size=10),
                ft.Container(
                    ft.Icon(ft.Icons.CLOSE, size=13, color=t.TEXT_FAINT),
                    on_click=lambda _e: _remove_module(app, index),
                    padding=4,
                    ink=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    ]
    if module.kind != "quote":
        controls.append(c.field("", module.title, field("title"), hint="заголовок модуля",
                                height=30))
    if module.kind in ("rates", "schedule", "list"):
        hints = {
            "rates": ("статья расхода", "цена"),
            "schedule": ("время", "событие"),
            "list": ("пункт перечня", ""),
        }[module.kind]
        rows = module.rows or [["", ""], ["", ""], ["", ""]]
        for row_index, row in enumerate(rows):
            left = c.field("", row[0] if row else "", set_row(row_index, 0),
                           hint=hints[0], height=30)
            if module.kind == "list":
                controls.append(
                    ft.Row(
                        [
                            ft.Container(left, expand=True),
                            _row_remove(app, module, row_index),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
                continue
            controls.append(
                ft.Row(
                    [
                        ft.Container(left, expand=3 if module.kind == "rates" else 2),
                        ft.Container(
                            c.field("", row[1] if len(row) > 1 else "", set_row(row_index, 1),
                                    hint=hints[1], height=30),
                            expand=2 if module.kind == "rates" else 3,
                        ),
                        _row_remove(app, module, row_index),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        controls.append(c.ghost_button("+ строка", lambda _e: _add_rate_row(app, module)))
    elif module.kind == "photo":
        controls.append(
            c.secondary_button("Выбрать снимок…",
                               lambda _e: app.page.run_task(_pick_module_image, app, module),
                               height=30)
        )
        if module.image is not None:
            controls.append(c.field("", module.image.caption, _module_caption(app, module),
                                    hint="подпись под снимком", height=30))
    else:
        controls.append(
            c.field("", module.text, field("text"), multiline=True,
                    hint=MODULE_HINTS.get(module.kind, "текст модуля"))
        )
    if module.kind == "quote":
        controls.append(c.field("", module.attribution, field("attribution"),
                                hint="кто сказал", height=30))
    if module.kind in ("ad", "weather"):
        controls.append(c.toggle("В рамке", module.framed, _module_framed(app, module)))
    return c.card(ft.Column(controls, spacing=8), padding=10)


def _module_framed(app: AppState, module):
    def handler(value: bool) -> None:
        module.framed = value
        app.touch(rebuild=True)

    return handler


def _module_caption(app: AppState, module):
    def handler(value: str) -> None:
        if module.image is not None:
            module.image.caption = value
            app.touch()

    return handler


def _row_remove(app: AppState, module, index: int) -> ft.Control:
    """Крестик у строки модуля — убрать её из перечня или таблицы."""
    return ft.Container(
        content=ft.Icon(ft.Icons.CLOSE, size=12, color=t.TEXT_FAINT),
        on_click=lambda _e: _drop_row(app, module, index),
        padding=4,
        ink=True,
        tooltip="Убрать строку",
    )


def _drop_row(app: AppState, module, index: int) -> None:
    if 0 <= index < len(module.rows):
        module.rows.pop(index)
        app.touch(rebuild=True)


def _add_rate_row(app: AppState, module) -> None:
    module.rows.append([""] if module.kind == "list" else ["", ""])
    app.touch(rebuild=True)


async def _pick_module_image(app: AppState, module) -> None:
    files = await app.file_picker().pick_files(
        dialog_title="Изображение для модуля",
        allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
    )
    if not files:
        return
    relative = storage.import_image(pathlib.Path(files[0].path), app.project_path)
    module.image = ImageRef(path=relative, caption="", height_px=120)
    app.touch(rebuild=True)


def _remove_module(app: AppState, index: int) -> None:
    block = app.selected_block
    if block and 0 <= index < len(block.modules):
        block.modules.pop(index)
        if not block.modules:
            block.kind = "empty"
        app.touch(rebuild=True)


def _edit_article(app: AppState, article_id: str) -> None:
    app.edit_article(article_id)


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
                    "Рукописи не возвращаются. Подписка на месяц — один рубль двадцать копеек.",
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
            c.toggle("Состаривание", paper.enabled, lambda value: set_value("enabled", value)),
            c.panel_section(
                "Интенсивность",
                c.slider(paper.intensity, set_intensity, 0, 100, divisions=100),
                ft.Row(
                    [
                        t.hint("0 — чистый лист", size=11, color=t.TEXT_FAINTER),
                        t.hint("100 — потрёпанный", size=11, color=t.TEXT_FAINTER),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                spacing=6,
            ),
            c.panel_section(
                "Составляющия",
                c.checkbox("Желтизна и сепия", paper.yellowing, lambda v: set_value("yellowing", v)),
                c.checkbox("Пятна и разводы", paper.stains, lambda v: set_value("stains", v)),
                c.checkbox("Неравномерность печати", paper.unevenness,
                           lambda v: set_value("unevenness", v)),
                c.checkbox("Заломы и сгибы", paper.folds, lambda v: set_value("folds", v)),
                c.checkbox("Зерно скана", paper.grain, lambda v: set_value("grain", v)),
                spacing=4,
            ),
            c.panel_section("Проба", sample, spacing=10),
            t.hint(
                "Эффект применяется ко всей полосе, включая изображения, "
                "и учитывается при экспорте.",
                size=11,
                color=t.TEXT_FAINTER,
            ),
        ],
        spacing=22,
    )
