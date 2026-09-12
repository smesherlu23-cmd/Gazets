"""«Печатня» — конструкторъ игровыхъ газетъ. Точка входа и маршрутизацiя экрановъ.

Запускъ:

    python -m pechatnya

Интерфейсъ — Flet (десктопное окно), полоса рендерится браузернымъ движкомъ
(см. docs/ARCHITECTURE.md). Приложенiе полностью офлайновое.
"""

from __future__ import annotations

import pathlib
from typing import Callable

import flet as ft

from . import fonts, storage
from .ui import (
    common as c,
    screen_article,
    screen_brand,
    screen_export,
    screen_grid,
    screen_issue,
    screen_layout,
    screen_presets,
    screen_start,
    theme as t,
)
from .ui.state import AppState

ROUTE_TITLES = {
    "start": "Проекты",
    "issue": "Новый выпускъ · шагъ 1",
    "presets": "Новый выпускъ · шагъ 2",
    "grid": "Новый выпускъ · шагъ 3",
    "layout": "Вёрстка",
    "article": "Редакторъ статьи",
    "export": "Экспортъ",
    "brand": "Брендъ изданiя",
    "issue_edit": "Карточка изданiя",
    "presets_edit": "Пресеты оформленiя",
    "grid_edit": "Сетка полосы",
}


def _titlebar(app: AppState) -> ft.Control:
    project_label = app.project.title + (" •" if app.dirty else "")
    return ft.Container(
        content=ft.Row(
            [
                t.text("ПЕЧАТНЯ", size=11, color="#cfd2d4", weight="600", tracking=1.7),
                t.text(ROUTE_TITLES.get(app.route, ""), size=12, color=t.TEXT_FAINT),
                ft.Container(expand=True),
                t.text(project_label, size=12, color=t.TEXT_MUTED),
                ft.Container(width=12),
                c.ghost_button("Сохранить", lambda _e: _save(app)),
                c.ghost_button("Полоса", lambda _e: app.navigate("layout")),
                t.hint(app.engine_note, size=11, color=t.TEXT_FAINTER),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=36,
        bgcolor=t.BG_TITLEBAR,
        border=ft.Border.only(bottom=ft.BorderSide(1, "#2a2c2f")),
        padding=ft.Padding.symmetric(vertical=0, horizontal=14),
    )


def _save(app: AppState) -> None:
    app.save()
    app.rebuild()


def _screen(app: AppState) -> ft.Control:
    """Возвращаетъ контролъ текущаго маршрута, переиспользуя «живые» экраны."""
    route = app.route
    if route in ("layout",):
        screen = app.screens.get("layout")
        if screen is None:
            screen = screen_layout.LayoutScreen(app)
            app.screens["layout"] = screen
        return screen.build()
    if route == "article":
        screen = screen_article.ArticleScreen(app)
        app.screens["article"] = screen
        return screen.build()
    if route == "export":
        screen = app.screens.get("export")
        if screen is None or screen.app is not app:
            screen = screen_export.ExportScreen(app)
            app.screens["export"] = screen
        return ft.Container(
            content=ft.Row([screen.build()], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.Colors.with_opacity(0.66, "#08090a"),
            expand=True,
            padding=24,
            alignment=ft.Alignment.CENTER,
        )
    builders: dict[str, Callable[[AppState], ft.Control]] = {
        "start": screen_start.build,
        "issue": screen_issue.build,
        "issue_edit": screen_issue.build,
        "presets": screen_presets.build,
        "presets_edit": screen_presets.build,
        "grid": screen_grid.build,
        "grid_edit": screen_grid.build,
        "brand": screen_brand.build,
    }
    return builders.get(route, screen_start.build)(app)


def main(page: ft.Page) -> None:
    t.apply_theme(page)
    page.window.width = 1440
    page.window.height = 900
    page.window.min_width = 1100
    page.window.min_height = 700
    page.window.prevent_close = False

    app = AppState(page)
    app.check_engine()

    root = ft.Container(expand=True)
    header = ft.Container()

    def rebuild() -> None:
        header.content = _titlebar(app)
        root.content = _screen(app)
        try:
            page.update()
        except Exception:
            import traceback; traceback.print_exc()

    app.bind_rebuild(rebuild)

    def on_key(event: ft.KeyboardEvent) -> None:
        if not event.ctrl:
            return
        key = (event.key or "").lower()
        if key == "s":
            _save(app)
        elif key == "e":
            app.navigate("export")
        elif key == "n":
            app.navigate("issue")

    page.on_keyboard_event = on_key
    page.on_close = lambda _event: app.shutdown()

    page.add(ft.Column([header, root], spacing=0, expand=True))

    # Открываемъ последнiй проектъ, иначе показываемъ демо-выпускъ.
    recents = storage.recent_projects(1)
    if recents:
        try:
            app.project = storage.load_project(pathlib.Path(recents[0].path))
            app.project_path = pathlib.Path(recents[0].path)
        except OSError:
            pass
    app.navigate("start")
    app.refresh_preview(immediate=True)


def run() -> None:
    ft.run(main, assets_dir=str(fonts.ASSETS))


if __name__ == "__main__":
    run()
