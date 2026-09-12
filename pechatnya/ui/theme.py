"""Токены интерфейса из README-хендофа (тёмный графит) и мелкие помощники."""

from __future__ import annotations

import flet as ft

from .. import fonts

# ---------------------------------------------------------------------- цвета
BG_WINDOW = "#17181a"
BG_TITLEBAR = "#121314"
BG_RAIL = "#141516"
BG_CANVAS = "#101112"
BG_FIELD = "#151617"
BG_CONTROL = "#1b1d1f"
BG_CARD = "#1e2022"
BG_ROW_HOVER = "#232628"

BORDER_STRONG = "#3a3d41"
BORDER_BASE = "#303337"
BORDER_SUBTLE = "#2b2e31"
BORDER_PANEL = "#26282b"
BORDER_ROW = "#222426"
BORDER_WINDOW = "#2e3134"

TEXT_PRIMARY = "#f2f0ec"
TEXT_BODY = "#dcdad6"
TEXT_SECONDARY = "#b3b6b9"
TEXT_MUTED = "#8d9095"
TEXT_FAINT = "#6f7275"
TEXT_FAINTER = "#5c5f62"

ACCENT = "#C05B42"
ACCENT_HOVER = "#d9765d"
ACCENT_TEXT = "#f0cfc6"
ACCENT_TINT = "#1f2223"  # подложка активных чипов (rgba(192,91,66,.12) на графите)
WARN = "#e08b73"
OK_BAR = "#5f8f6a"
OK_TEXT = "#9dbf9f"

PAPER = "#efe7d4"

# --------------------------------------------------------------------- шрифты
UI = "IBM Plex Sans"
UI_MEDIUM = "IBM Plex Sans Medium"
UI_SEMI = "IBM Plex Sans SemiBold"
MONO = "IBM Plex Mono"
MONO_SEMI = "IBM Plex Mono SemiBold"

RADIUS_CONTROL = 3
RADIUS_WINDOW = 6
RADIUS_PILL = 99


def tint(opacity: float = 0.12) -> str:
    return ft.Colors.with_opacity(opacity, ACCENT)


def text(
    value: str,
    size: float = 13,
    color: str = TEXT_BODY,
    weight: str | None = None,
    font: str | None = None,
    tracking: float | None = None,
    italic: bool = False,
    **kwargs,
) -> ft.Text:
    style = ft.TextStyle(letter_spacing=tracking) if tracking is not None else None
    return ft.Text(
        value,
        size=size,
        color=color,
        font_family=font or (UI_SEMI if weight == "600" else UI_MEDIUM if weight == "500" else UI),
        italic=italic,
        style=style,
        **kwargs,
    )


def caps(value: str, size: float = 10, color: str = TEXT_MUTED, tracking: float = 1.4) -> ft.Text:
    """Лейбл секции: капс, трекинг 0.14em (README, шкала UI)."""
    return text(value.upper(), size=size, color=color, weight="500", tracking=tracking)


def screen_title(value: str) -> ft.Text:
    return text(value, size=24, color=TEXT_PRIMARY, weight="600", tracking=-0.24)


def hint(value: str, size: float = 11, color: str = TEXT_FAINT) -> ft.Text:
    return ft.Text(value, size=size, color=color, font_family=UI, no_wrap=False)


def divider(vertical: bool = False, color: str = BORDER_PANEL) -> ft.Container:
    return ft.Container(
        width=1 if vertical else None,
        height=None if vertical else 1,
        bgcolor=color,
        expand=vertical is False,
    )


def apply_theme(page: ft.Page) -> None:
    page.title = "Печатня — конструктор газет"
    page.bgcolor = BG_WINDOW
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    page.fonts = fonts.flet_fonts()
    page.theme = ft.Theme(
        font_family=UI,
        color_scheme=ft.ColorScheme(primary=ACCENT, surface=BG_WINDOW, on_surface=TEXT_PRIMARY),
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=BORDER_STRONG, track_color=BG_CANVAS, thickness=6, radius=3
        ),
    )
