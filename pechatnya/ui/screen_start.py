"""Экран 01 — старт: недавние выпуски, издания, таблица номеров."""

from __future__ import annotations

import datetime as dt
import pathlib

import flet as ft

from .. import storage
from ..presets import demo_project
from . import common as c
from . import theme as t
from . import thumbs
from .state import AppState


def _format_stamp(value: str) -> str:
    try:
        stamp = dt.datetime.fromisoformat(value)
    except ValueError:
        return value or "—"
    today = dt.date.today()
    if stamp.date() == today:
        return f"сегодня, {stamp:%H:%M}"
    if (today - stamp.date()).days == 1:
        return f"вчера, {stamp:%H:%M}"
    return f"{stamp:%d.%m.%Y}"


def build(app: AppState) -> ft.Control:
    recents = storage.recent_projects()
    titles: list[str] = []
    for entry in recents:
        if entry.issue and entry.issue not in titles:
            titles.append(entry.issue)

    # ---------------------------------------------------------------- левая панель
    library_rows = [
        ("Все выпуски", len(recents)),
        ("Недавние", min(len(recents), 8)),
        ("Автосохранения", len(list((storage.app_dir() / "autosave").glob("*.json")))),
    ]
    library = ft.Column(
        [
            t.caps("Библиотека / Library"),
            *[
                c.list_row(
                    ft.Row(
                        [
                            t.text(name, size=13, color=t.TEXT_BODY if index == 0 else t.TEXT_SECONDARY),
                            t.text(str(count), size=12, color=t.TEXT_MUTED),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    active=index == 0,
                )
                for index, (name, count) in enumerate(library_rows)
            ],
        ],
        spacing=6,
    )
    title_rows: list[ft.Control] = [
        c.list_row(t.text(name, size=12, color=t.TEXT_SECONDARY), height=28) for name in titles[:6]
    ] or [t.hint("Сохранённыхъ изданiй пока нетъ")]
    titles_column = ft.Column([t.caps("Издания / Titles"), *title_rows], spacing=6)
    rail = c.rail(
        ft.Column(
            [
                library,
                ft.Container(height=10),
                titles_column,
                ft.Container(expand=True),
                t.hint(f"Проекты лежат в\n{storage.documents_dir()}", size=11, color=t.TEXT_FAINTER),
            ],
            spacing=12,
            expand=True,
        ),
        width=230,
    )

    # ------------------------------------------------------------------- карточки
    def open_entry(path: str):
        def handler(_event):
            try:
                app.open(pathlib.Path(path))
            except OSError as error:
                app.preview_error = str(error)
                storage.forget_recent(path)
                app.rebuild()

        return handler

    cards: list[ft.Control] = []
    for entry in recents[:7]:
        cards.append(
            c.card(
                ft.Column(
                    [
                        thumbs.paper_thumb(height=190, logo=entry.issue.upper()[:14] or "ВЫПУСКЪ"),
                        t.text(entry.title or entry.issue, size=13, color=t.TEXT_PRIMARY, weight="500"),
                        t.hint(
                            f"№ {entry.number} · {entry.date} · {_format_stamp(entry.modified)}",
                            size=12,
                            color=t.TEXT_MUTED,
                        ),
                    ],
                    spacing=8,
                ),
                on_click=open_entry(entry.path),
            )
        )

    def start_new(_event=None) -> None:
        app.navigate("issue")

    cards.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Text("+", size=18, color=t.TEXT_SECONDARY),
                        width=34,
                        height=34,
                        border=ft.Border.all(1, t.BORDER_STRONG),
                        border_radius=99,
                        alignment=ft.Alignment.CENTER,
                    ),
                    t.text("Новый выпускъ", size=13, color=t.TEXT_SECONDARY),
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            height=246,
            border=ft.Border.all(1, t.BORDER_STRONG),
            border_radius=t.RADIUS_CONTROL,
            on_click=start_new,
            ink=True,
        )
    )

    grid = ft.GridView(
        controls=cards,
        runs_count=4,
        max_extent=300,
        spacing=18,
        run_spacing=18,
        child_aspect_ratio=0.86,
        height=560,
    )

    # -------------------------------------------------------------------- таблица
    header = ft.Row(
        [
            ft.Container(t.caps("№", size=10, tracking=1.2), width=80),
            ft.Container(t.caps("Выпускъ", size=10, tracking=1.2), expand=True),
            ft.Container(t.caps("Дата", size=10, tracking=1.2), width=160),
            ft.Container(t.caps("Полосъ", size=10, tracking=1.2), width=120),
            ft.Container(t.caps("Измененъ", size=10, tracking=1.2), width=130),
        ],
        spacing=0,
    )
    rows: list[ft.Control] = [header]
    for entry in recents[:8]:
        rows.append(ft.Container(height=1, bgcolor=t.BORDER_ROW))
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            t.text(f"№ {entry.number}", size=13, color=t.ACCENT, weight="500"), width=80
                        ),
                        ft.Container(t.text(entry.title or entry.issue, size=13), expand=True),
                        ft.Container(t.text(entry.date, size=13, color=t.TEXT_SECONDARY), width=160),
                        ft.Container(t.text("—", size=13, color=t.TEXT_MUTED), width=120),
                        ft.Container(
                            t.text(_format_stamp(entry.modified), size=13, color=t.TEXT_MUTED), width=130
                        ),
                    ]
                ),
                height=34,
                on_click=open_entry(entry.path),
                ink=True,
            )
        )

    async def open_file(_event) -> None:
        files = await app.file_picker().pick_files(
            dialog_title="Открыть проектъ «Печатни»",
            allowed_extensions=["json"],
            initial_directory=str(storage.documents_dir()),
        )
        if files:
            app.open(pathlib.Path(files[0].path))

    def open_demo(_event) -> None:
        app.set_project(demo_project())
        app.navigate("layout")
        app.refresh_preview(immediate=True)

    content = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                t.text("Проекты", size=26, color=t.TEXT_PRIMARY, weight="600"),
                                t.hint("Последнее измененiе — сверху", size=13, color=t.TEXT_MUTED),
                            ],
                            spacing=4,
                        ),
                        ft.Row(
                            [
                                c.secondary_button("Демо-выпускъ", open_demo),
                                c.secondary_button("Открыть файлъ…", open_file),
                                c.primary_button("Новый выпускъ", start_new, icon=ft.Icons.ADD),
                            ],
                            spacing=10,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                grid,
                ft.Column(rows, spacing=0),
            ],
            spacing=26,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=ft.Padding.symmetric(vertical=32, horizontal=36),
        expand=True,
    )

    return ft.Row([rail, content], spacing=0, expand=True)
