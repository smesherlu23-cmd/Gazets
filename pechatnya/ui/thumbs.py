"""Наборные миниатюры: карточки проектов, пресетов, шаблонов сетки, брендов.

В макете это маленькие «полосы», нарисованные полосками и плашками, — рендерить
ради них настоящий PDF-движок незачем, поэтому миниатюры собраны из контейнеров.
"""

from __future__ import annotations

import flet as ft

from . import theme as t

PAPER = "#f1ece0"
INK = "#15120e"
RULE = "#b6ae9c"
HALFTONE = "#d5cdba"


def _rule(height: float = 1, color: str = RULE, width=None) -> ft.Control:
    return ft.Container(height=height, bgcolor=color, width=width, expand=width is None)


def _lines(count: int, width=None, spacing: float = 3, color: str = RULE) -> ft.Control:
    return ft.Column(
        [ft.Container(height=1.5, bgcolor=color) for _ in range(count)],
        spacing=spacing,
        width=width,
    )


def _columns(count: int, lines: int, spacing: int = 6) -> ft.Control:
    return ft.Row(
        [ft.Container(content=_lines(lines), expand=True) for _ in range(count)],
        spacing=spacing,
        vertical_alignment=ft.CrossAxisAlignment.START,
        expand=True,
    )


def paper_thumb(
    height: int = 190,
    logo: str = "ВЕСТНИКЪ",
    logo_font: str = "Old Standard TT Bold",
    logo_size: float = 15,
    paper: str = PAPER,
    columns: int = 3,
    rules: int = 2,
    halftone: bool = True,
    boxed: bool = False,
    invert: bool = False,
    accent: str = INK,
) -> ft.Control:
    """Миниатюра полосы для карточек — бумага, шапка, линейки, колонки."""
    masthead: list[ft.Control] = [
        ft.Row(
            [
                ft.Container(height=2, bgcolor=RULE, expand=True),
            ],
            spacing=4,
        ),
        ft.Container(
            content=ft.Text(
                logo,
                size=logo_size,
                color=paper if invert else accent,
                font_family=logo_font,
                text_align=ft.TextAlign.CENTER,
                no_wrap=True,
            ),
            alignment=ft.Alignment.CENTER,
            bgcolor=accent if invert else None,
            padding=ft.Padding.symmetric(vertical=2, horizontal=4),
        ),
    ]
    for index in range(rules):
        masthead.append(ft.Container(height=2.5 if index == 0 else 1, bgcolor=accent))

    body: list[ft.Control] = [
        _lines(2, color=accent),
        ft.Container(height=2),
        _columns(columns, 22),
    ]
    if halftone:
        body.append(ft.Container(height=26, bgcolor=HALFTONE, margin=ft.Margin.only(top=4)))
    if boxed:
        body.append(
            ft.Container(
                content=_lines(2, color=accent, spacing=2),
                border=ft.Border.all(1, accent),
                padding=4,
                margin=ft.Margin.only(top=4),
            )
        )

    return ft.Container(
        content=ft.Column(masthead + body, spacing=3, expand=True),
        height=height,
        bgcolor=paper,
        padding=8,
        border_radius=4,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def grid_thumb(blocks: list[tuple[str, int, int]], height: int = 168) -> ft.Control:
    """Схема шаблона сетки: подписанные прямоугольники.

    ``blocks`` — список ``(подпись, номер строки, вес)``; строки собираются
    по порядку, вес задаёт долю ширины.
    """
    rows: dict[int, list[tuple[str, int]]] = {}
    for label, row, weight in blocks:
        rows.setdefault(row, []).append((label, weight))
    controls = []
    for row_index in sorted(rows):
        cells = []
        for label, weight in rows[row_index]:
            cells.append(
                ft.Container(
                    content=ft.Text(
                        label,
                        size=8,
                        color="#6b6354",
                        font_family=t.MONO,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    bgcolor="#ddd6c6" if row_index == 0 else "#e6e0d1",
                    alignment=ft.Alignment.CENTER,
                    expand=weight,
                    padding=2,
                )
            )
        controls.append(ft.Row(cells, spacing=4, expand=row_index != 0, height=14 if row_index == 0 else None))
    return ft.Container(
        content=ft.Column(controls, spacing=4, expand=True),
        height=height,
        bgcolor=PAPER,
        padding=8,
        border_radius=4,
    )


def page_thumb(active: bool, number: int, width: int = 44, height: int = 62) -> ft.Control:
    """Миниатюра полосы в левой панели вёрстки."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(height=6, bgcolor=INK),
                _lines(3, color=RULE, spacing=2),
                ft.Container(
                    content=ft.Text(str(number), size=8, color="#6b6354", font_family=t.MONO),
                    alignment=ft.Alignment.BOTTOM_CENTER,
                    expand=True,
                ),
            ],
            spacing=3,
        ),
        width=width,
        height=height,
        bgcolor=PAPER,
        padding=4,
        border=ft.Border.all(1, t.ACCENT if active else t.BORDER_SUBTLE),
        border_radius=2,
    )


def masthead_preview(
    title: str,
    motto: str,
    number: str,
    city: str,
    date: str,
    price: str,
    rules_style: str = "bold_thin",
    logo_font: str = "Old Standard TT Bold",
    width: int = 640,
) -> ft.Control:
    """Живой показ шапки на бумаге — набирается теми же гарнитурами, что и полоса."""
    service = ft.Row(
        [
            ft.Text(f"№ {number}", size=11, color="#3a3227", font_family="PT Serif"),
            ft.Text(f"{city} · {date}", size=11, color="#3a3227", font_family="PT Serif"),
            ft.Text(price, size=11, color="#3a3227", font_family="PT Serif"),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    rules: list[ft.Control] = []
    if rules_style == "single":
        rules.append(ft.Container(height=1, bgcolor="#181410"))
    elif rules_style == "ornament":
        rules.extend(
            [
                ft.Container(height=1, bgcolor="#181410"),
                ft.Container(
                    content=ft.Text("✦ ✦ ✦", size=9, color="#8d8271", font_family="PT Sans Narrow"),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=1, bgcolor="#181410"),
            ]
        )
    else:
        rules.extend(
            [
                ft.Container(height=2, bgcolor="#181410"),
                ft.Container(height=1, bgcolor="#181410", margin=ft.Margin.only(top=2)),
            ]
        )

    filler = ft.Row(
        [
            ft.Container(
                content=ft.Text(
                    "Редакцiя принимаетъ объявленiя ежедневно съ девяти часовъ утра. "
                    "Рукописи не возвращаются.",
                    size=10,
                    color="#3a3227",
                    font_family="PT Serif",
                    text_align=ft.TextAlign.JUSTIFY,
                ),
                expand=True,
            )
            for _ in range(3)
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    return ft.Container(
        content=ft.Column(
            [
                service,
                ft.Container(height=1, bgcolor="#3a3227"),
                ft.Container(
                    content=ft.Text(
                        title,
                        size=44,
                        color="#181410",
                        font_family=logo_font,
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=True,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.only(top=10, bottom=4),
                ),
                ft.Container(
                    content=ft.Text(
                        motto,
                        size=14,
                        color="#3a3227",
                        font_family="Old Standard TT",
                        italic=True,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=ft.Padding.only(bottom=8),
                ),
                *rules,
                ft.Container(height=10),
                filler,
            ],
            spacing=4,
        ),
        width=width,
        bgcolor="#f2ede1",
        padding=ft.Padding.symmetric(vertical=30, horizontal=34),
        border_radius=2,
    )
