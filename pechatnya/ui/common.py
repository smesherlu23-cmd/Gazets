"""Элементы интерфейса «Печатни»: поля, чипы, степперы, кнопки, панели.

Все размеры — из раздела «Размеры и радиусы» README: поле 32, компактное 28,
строка списка 30, вкладка панели 38, кнопка 32–34, радиус контролов 3.
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional

import flet as ft

from . import theme as t


def primary_button(label: str, on_click: Callable, icon: Optional[str] = None, width=None) -> ft.Control:
    return ft.ElevatedButton(
        content=ft.Row(
            [
                *( [ft.Icon(icon, size=14, color="#ffffff")] if icon else [] ),
                t.text(label, size=13, color="#ffffff", weight="500"),
            ],
            spacing=8,
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        on_click=on_click,
        width=width,
        height=34,
        style=ft.ButtonStyle(
            bgcolor=t.ACCENT,
            color="#ffffff",
            overlay_color=ft.Colors.with_opacity(0.12, "#ffffff"),
            shape=ft.RoundedRectangleBorder(radius=t.RADIUS_CONTROL),
            padding=ft.Padding.symmetric(vertical=0, horizontal=18),
            elevation=0,
        ),
    )


def secondary_button(label: str, on_click: Callable, width=None, height: int = 34) -> ft.Control:
    return ft.OutlinedButton(
        content=t.text(label, size=13, color=t.TEXT_SECONDARY),
        on_click=on_click,
        width=width,
        height=height,
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, t.BORDER_STRONG),
            shape=ft.RoundedRectangleBorder(radius=t.RADIUS_CONTROL),
            padding=ft.Padding.symmetric(vertical=0, horizontal=14),
            overlay_color=ft.Colors.with_opacity(0.06, "#ffffff"),
        ),
    )


def ghost_button(label: str, on_click: Callable) -> ft.Control:
    return ft.TextButton(
        content=t.text(label, size=12, color=t.TEXT_MUTED),
        on_click=on_click,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=t.RADIUS_CONTROL),
            padding=ft.Padding.symmetric(vertical=0, horizontal=10),
            overlay_color=ft.Colors.with_opacity(0.06, "#ffffff"),
        ),
    )


def field(
    label: str,
    value: str,
    on_change: Callable[[str], None],
    hint: str = "",
    multiline: bool = False,
    height: Optional[int] = 32,
    expand: bool = False,
    text_size: float = 13,
    font: Optional[str] = None,
) -> ft.Control:
    control = ft.TextField(
        value=value,
        hint_text=hint,
        on_change=lambda event: on_change(event.control.value),
        multiline=multiline,
        min_lines=None if not multiline else 3,
        expand=multiline and expand,
        border_radius=t.RADIUS_CONTROL,
        border_color=t.BORDER_BASE,
        focused_border_color=t.ACCENT,
        bgcolor=t.BG_FIELD,
        color=t.TEXT_BODY,
        cursor_color=t.ACCENT,
        cursor_width=1,
        cursor_height=17,
        selection_color=ft.Colors.with_opacity(0.22, t.ACCENT),
        text_size=text_size,
        text_style=ft.TextStyle(font_family=font or t.UI, height=1.5 if multiline else None),
        content_padding=ft.Padding.symmetric(vertical=6 if not multiline else 10, horizontal=11),
        height=None if multiline else height,
        dense=True,
    )
    if not label:
        return control
    return ft.Column(
        [t.text(label, size=12, color=t.TEXT_SECONDARY), control],
        spacing=6,
        expand=expand,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )


def stepper(
    label: str,
    value: float,
    on_change: Callable[[float], None],
    step: float = 1,
    minimum: float = 0,
    maximum: float = 999,
    suffix: str = "",
    decimals: int = 0,
    width: Optional[int] = None,
) -> ft.Control:
    """Поле со стрелками «−/+» внутри — как в карточке издания и панели блока."""
    display = ft.Text(
        f"{value:.{decimals}f}{suffix}",
        size=13,
        color=t.TEXT_BODY,
        font_family=t.MONO,
    )
    state = {"value": float(value)}

    def shift(delta: float) -> None:
        new = max(minimum, min(maximum, round(state["value"] + delta, 3)))
        state["value"] = new
        display.value = f"{new:.{decimals}f}{suffix}"
        display.update()
        on_change(new)

    def arrow(symbol: str, delta: float) -> ft.Control:
        return ft.Container(
            content=ft.Text(symbol, size=13, color=t.TEXT_SECONDARY),
            width=24,
            height=26,
            alignment=ft.Alignment.CENTER,
            on_click=lambda _: shift(delta),
            border_radius=2,
            ink=True,
        )

    box = ft.Container(
        content=ft.Row(
            [arrow("−", -step), ft.Container(display, expand=True, alignment=ft.Alignment.CENTER),
             arrow("+", step)],
            spacing=0,
        ),
        bgcolor=t.BG_CONTROL,
        border=ft.Border.all(1, t.BORDER_BASE),
        border_radius=t.RADIUS_CONTROL,
        height=32,
        width=width,
        padding=ft.Padding.symmetric(vertical=0, horizontal=3),
    )
    if not label:
        return box
    return ft.Row(
        [t.text(label, size=12, color=t.TEXT_SECONDARY, expand=True), box],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def chip(label: str, active: bool, on_click: Callable, height: int = 30) -> ft.Control:
    # без alignment: иначе Container растягивается на всю ширину панели
    return ft.Container(
        content=ft.Row(
            [
                t.text(
                    label,
                    size=12,
                    color=t.ACCENT_TEXT if active else t.TEXT_SECONDARY,
                    weight="500" if active else None,
                )
            ],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        height=height,
        padding=ft.Padding.symmetric(vertical=0, horizontal=12),
        bgcolor=t.tint(0.14) if active else t.BG_CONTROL,
        border=ft.Border.all(1, t.ACCENT if active else t.BORDER_BASE),
        border_radius=t.RADIUS_CONTROL,
        on_click=on_click,
        ink=True,
    )


def chip_row(
    options: Iterable[tuple[str, str]],
    value: str,
    on_change: Callable[[str], None],
    height: int = 30,
    spacing: int = 8,
    wrap: bool = True,
) -> ft.Control:
    controls = [
        chip(label, key == value, (lambda key: lambda _: on_change(key))(key), height=height)
        for key, label in options
    ]
    return ft.Row(controls, spacing=spacing, wrap=wrap, run_spacing=8)


def segment(
    options: Iterable[tuple[str, str]],
    value: str,
    on_change: Callable[[str], None],
    height: int = 30,
) -> ft.Control:
    """Сегментированный переключатель (Влево / По ширине / Центр)."""
    cells = []
    for key, label in options:
        active = key == value
        cells.append(
            ft.Container(
                content=t.text(
                    label,
                    size=12,
                    color=t.ACCENT_TEXT if active else t.TEXT_SECONDARY,
                    weight="500" if active else None,
                ),
                expand=True,
                height=height,
                alignment=ft.Alignment.CENTER,
                bgcolor=t.tint(0.14) if active else "transparent",
                on_click=(lambda key: lambda _: on_change(key))(key),
                ink=True,
            )
        )
    return ft.Container(
        content=ft.Row(cells, spacing=0),
        bgcolor=t.BG_CONTROL,
        border=ft.Border.all(1, t.BORDER_BASE),
        border_radius=t.RADIUS_CONTROL,
        height=height,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def toggle(label: str, value: bool, on_change: Callable[[bool], None], hint_text: str = "") -> ft.Control:
    switch = ft.Switch(
        value=value,
        on_change=lambda event: on_change(event.control.value),
        active_color=t.ACCENT,
        inactive_track_color=t.BG_CONTROL,
        inactive_thumb_color=t.TEXT_FAINT,
        scale=0.75,
    )
    left = [t.text(label, size=12, color=t.TEXT_SECONDARY)]
    if hint_text:
        left.append(t.hint(hint_text, size=10, color=t.TEXT_FAINTER))
    return ft.Row(
        [ft.Column(left, spacing=2, expand=True), switch],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def checkbox(label: str, value: bool, on_change: Callable[[bool], None]) -> ft.Control:
    return ft.Row(
        [
            ft.Checkbox(
                value=value,
                on_change=lambda event: on_change(event.control.value),
                active_color=t.ACCENT,
                check_color="#ffffff",
                border_side=ft.BorderSide(1, t.BORDER_STRONG),
                scale=0.8,
            ),
            t.text(label, size=12, color=t.TEXT_SECONDARY),
        ],
        spacing=2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def select(
    label: str,
    value: str,
    options: Iterable[str],
    on_change: Callable[[str], None],
    width: Optional[int] = None,
) -> ft.Control:
    dropdown = ft.Dropdown(
        value=value,
        options=[ft.dropdown.Option(item) for item in options],
        on_select=lambda event: on_change(event.control.value),
        border_radius=t.RADIUS_CONTROL,
        border_color=t.BORDER_BASE,
        focused_border_color=t.ACCENT,
        bgcolor=t.BG_CONTROL,
        color=t.TEXT_BODY,
        text_size=13,
        content_padding=ft.Padding.symmetric(vertical=4, horizontal=11),
        width=width,
        dense=True,
        expand=width is None,
    )
    if not label:
        return dropdown
    return ft.Column(
        [t.text(label, size=12, color=t.TEXT_SECONDARY), dropdown],
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )


def slider(
    value: float,
    on_change: Callable[[float], None],
    minimum: float = 0,
    maximum: float = 100,
    divisions: Optional[int] = None,
) -> ft.Control:
    return ft.Slider(
        value=value,
        min=minimum,
        max=maximum,
        divisions=divisions,
        on_change=lambda event: on_change(event.control.value),
        active_color=t.ACCENT,
        inactive_color=t.BORDER_PANEL,
        thumb_color=t.TEXT_PRIMARY,
        expand=True,
    )


def panel_section(label: str, *controls: ft.Control, spacing: int = 12) -> ft.Control:
    return ft.Column([t.caps(label), *controls], spacing=spacing)


def fill_bar(percent: float, height: int = 4) -> ft.Control:
    """Полоса заполнения блока: зелёная до 100 %, тревожная — после."""
    filled = max(1, min(100, int(round(percent))))
    color = t.OK_BAR if percent <= 100 else t.WARN
    parts: list[ft.Control] = [ft.Container(bgcolor=color, height=height, expand=filled)]
    if filled < 100:
        parts.append(ft.Container(bgcolor=t.BORDER_PANEL, height=height, expand=100 - filled))
    return ft.Container(
        content=ft.Row(parts, spacing=0),
        height=height,
        border_radius=2,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def dot(color: str, size: int = 6) -> ft.Control:
    return ft.Container(width=size, height=size, bgcolor=color, border_radius=size)


def card(content: ft.Control, active: bool = False, on_click: Optional[Callable] = None, padding=12) -> ft.Control:
    return ft.Container(
        content=content,
        bgcolor=t.BG_CARD,
        border=ft.Border.all(1, t.ACCENT if active else t.BORDER_SUBTLE),
        border_radius=t.RADIUS_CONTROL,
        padding=padding,
        on_click=on_click,
        ink=on_click is not None,
    )


def rail(content: ft.Control, width: int = 256) -> ft.Control:
    return ft.Container(
        content=content,
        width=width,
        bgcolor=t.BG_RAIL,
        border=ft.Border.only(right=ft.BorderSide(1, t.BORDER_PANEL)),
        padding=ft.Padding.symmetric(vertical=20, horizontal=16),
    )


def list_row(
    content: ft.Control,
    active: bool = False,
    on_click: Optional[Callable] = None,
    height: int = 30,
    warn: bool = False,
) -> ft.Control:
    background = t.BG_ROW_HOVER if active else (ft.Colors.with_opacity(0.07, t.ACCENT) if warn else None)
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(width=2, bgcolor=t.ACCENT if active else "transparent", height=height),
                ft.Container(content, expand=True, padding=ft.Padding.only(left=8, right=8)),
            ],
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=background,
        height=height,
        on_click=on_click,
        ink=on_click is not None,
        border_radius=2,
    )
