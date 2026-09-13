"""Экран 01 — старт: недавние выпуски, издания, таблица номеров."""

from __future__ import annotations

import datetime as dt
import pathlib

import flet as ft

from .. import storage
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
    publications = storage.publications()
    active_filter = app.start_filter
    if active_filter:
        recents = [entry for entry in recents if entry.publication_id == active_filter]

    # ---------------------------------------------------------------- левая панель
    def filter_row(label: str, key: str, count: int) -> ft.Control:
        return c.list_row(
            ft.Row(
                [
                    t.text(label, size=12,
                           color=t.TEXT_BODY if key == active_filter else t.TEXT_SECONDARY),
                    t.text(str(count), size=12, color=t.TEXT_MUTED),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            active=key == active_filter,
            on_click=(lambda key: lambda _e: _set_filter(app, key))(key),
            height=30,
        )

    all_recents = storage.recent_projects(99)
    rows = [filter_row("Все выпуски", "", len(all_recents))]
    for item in publications:
        count = len([entry for entry in all_recents if entry.publication_id == item.id])
        rows.append(filter_row(item.display_name, item.id, count))

    rail = c.rail(
        ft.Column(
            [
                t.caps("Издания"),
                ft.Column(rows, spacing=4),
                ft.Container(
                    content=t.text("Редактировать издания", size=12, color=t.TEXT_SECONDARY),
                    height=32,
                    alignment=ft.Alignment.CENTER,
                    border=ft.Border.all(1, t.BORDER_STRONG),
                    border_radius=t.RADIUS_CONTROL,
                    on_click=lambda _e: app.open_publications("start"),
                    ink=True,
                ),
                ft.Container(expand=True),
                t.hint(f"Проекты лежат в\n{storage.documents_dir()}", size=11,
                       color=t.TEXT_FAINTER),
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
                        thumbs.paper_thumb(height=190, logo=entry.issue.upper()[:14] or "ВЫПУСК"),
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
                    t.text("Новый выпуск", size=13, color=t.TEXT_SECONDARY),
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
            ft.Container(t.caps("Выпуск", size=10, tracking=1.2), expand=True),
            ft.Container(t.caps("Дата", size=10, tracking=1.2), width=160),
            ft.Container(t.caps("Полос", size=10, tracking=1.2), width=120),
            ft.Container(t.caps("Изменен", size=10, tracking=1.2), width=130),
        ],
        spacing=0,
    )
    rows: list[ft.Control] = [header] if recents else []
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
                        ft.Container(
                            t.text(str(entry.pages or "—"), size=13, color=t.TEXT_MUTED), width=120
                        ),
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
            dialog_title="Открыть проект «Печатни»",
            allowed_extensions=["json"],
            initial_directory=str(storage.documents_dir()),
        )
        if files:
            app.open(pathlib.Path(files[0].path))

    content = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                t.text("Проекты", size=26, color=t.TEXT_PRIMARY, weight="600"),
                                t.hint(
                                    "Последнее изменение — сверху"
                                    if recents
                                    else "Здесь появятся ваши выпуски",
                                    size=13,
                                    color=t.TEXT_MUTED,
                                ),
                            ],
                            spacing=4,
                        ),
                        ft.Row(
                            [
                                c.secondary_button("Открыть файл…", open_file),
                                c.primary_button("Новый выпуск", start_new, icon=ft.Icons.ADD),
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


def _set_filter(app: AppState, key: str) -> None:
    app.start_filter = key
    app.rebuild()
