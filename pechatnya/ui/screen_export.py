"""Экран 08 — экспорт PNG и PDF.

Рендер идёт локально в фоновом потоке; по каждой готовой полосе обновляется
прогресс. Слой состаривания берётся из текущих настроек бумаги.
"""

from __future__ import annotations

import pathlib
import threading

import flet as ft

from .. import storage
from ..render.export import (
    DPI_CHOICES,
    ExportSettings,
    dpi_label,
    estimate_size,
    export,
    planned_names,
)
from . import common as c
from . import theme as t
from .state import AppState


class ExportScreen:
    def __init__(self, app: AppState) -> None:
        self.app = app
        settings = getattr(app, "export_settings", None)
        if settings is None:
            settings = ExportSettings(directory=storage.documents_dir())
            app.export_settings = settings
        self.settings = settings
        self.settings.current_page = app.current_page
        self.settings.range_to = len(app.project.pages)
        self.progress = ft.ProgressBar(value=0, color=t.ACCENT, bgcolor=t.BORDER_PANEL, height=4)
        self.status = ft.Text("", size=11, color=t.TEXT_MUTED, font_family=t.MONO)
        self.busy = False

    # ------------------------------------------------------------------ действия
    def _set(self, field: str, value) -> None:
        setattr(self.settings, field, value)
        self.app.rebuild()

    def _run(self, _event=None) -> None:
        if self.busy:
            return
        self.busy = True
        self.status.value = "готовим рендер…"
        self.progress.value = None
        self.app.page.update()

        def worker() -> None:
            try:
                result = export(
                    self.app.project,
                    self.settings,
                    self.app.project_dir,
                    progress=self._on_progress,
                )
                names = ", ".join(path.name for path in result.files[:3])
                self.status.value = f"готово: {names} ({result.size_label})"
                self.progress.value = 1.0
            except Exception as error:
                self.status.value = f"ошибка: {error}"
                self.progress.value = 0
            finally:
                self.busy = False
                try:
                    self.app.page.update()
                except Exception:
                    pass

        threading.Thread(target=worker, name="pechatnya-export", daemon=True).start()

    def _on_progress(self, done: int, total: int, name: str) -> None:
        self.progress.value = done / max(total, 1)
        self.status.value = f"{done} из {total} · {name}"
        try:
            self.app.page.update()
        except Exception:
            pass

    async def _choose_directory(self, _event=None) -> None:
        path = await self.app.file_picker().get_directory_path(dialog_title="Куда сохранить выпуск")
        if path:
            self.settings.directory = pathlib.Path(path)
            self.app.rebuild()

    # -------------------------------------------------------------------- сборка
    def build(self) -> ft.Control:
        app = self.app
        settings = self.settings
        total_pages = len(app.project.pages)
        names = planned_names(app.project, settings)

        tabs = ft.Row(
            [
                c.chip("PNG для чата", settings.fmt == "png", lambda _e: self._set("fmt", "png"), height=32),
                c.chip("PDF для печати", settings.fmt == "pdf", lambda _e: self._set("fmt", "pdf"), height=32),
            ],
            spacing=8,
        )

        left = ft.Column(
            [
                c.panel_section(
                    "Что выгружаем",
                    c.segment(
                        [("all", "Все полосы"), ("current", "Только текущую"), ("range", "Диапазон")],
                        settings.scope,
                        lambda value: self._set("scope", value),
                    ),
                    *(
                        [
                            ft.Row(
                                [
                                    c.stepper("с", settings.range_from,
                                              lambda value: self._set("range_from", int(value)),
                                              minimum=1, maximum=total_pages, width=100),
                                    c.stepper("по", settings.range_to,
                                              lambda value: self._set("range_to", int(value)),
                                              minimum=1, maximum=total_pages, width=100),
                                ],
                                spacing=12,
                            )
                        ]
                        if settings.scope == "range"
                        else []
                    ),
                    spacing=10,
                ),
                *(
                    [
                        c.panel_section(
                            "Разрешение",
                            c.select(
                                "",
                                dpi_label(settings.dpi, app.project.sheet_px()),
                                [dpi_label(value, app.project.sheet_px()) for value in DPI_CHOICES],
                                lambda value: self._set("dpi", int(value.split()[0])),
                            ),
                            t.hint("96 / 150 / 300 / 600 dpi. Для чата достаточно 150.", size=11),
                            spacing=8,
                        )
                    ]
                    if settings.fmt == "png"
                    else [
                        c.panel_section(
                            "Лист",
                            t.hint(
                                f"Лист — {app.project.page_format}, "
                                f"{'портрет' if app.project.orientation == 'portrait' else 'альбом'}"
                                f" ({app.project.sheet_mm()[0]:.0f}×{app.project.sheet_mm()[1]:.0f} мм). "
                                "Меняется на экране сетки полосы.",
                                size=11,
                            ),
                            spacing=8,
                        )
                    ]
                ),
                c.panel_section(
                    "Опции",
                    c.checkbox(
                        f"Включить эффект бумаги ({app.project.paper.intensity} %)",
                        settings.with_paper,
                        lambda value: self._set("with_paper", value),
                    ),
                    c.checkbox("Метки реза и поля под печать", settings.crop_marks,
                               lambda value: self._set("crop_marks", value)),
                    *(
                        [
                            c.checkbox("Склеить полосы в одну картинку", settings.stitch,
                                       lambda value: self._set("stitch", value))
                        ]
                        if settings.fmt == "png"
                        else []
                    ),
                    spacing=4,
                ),
                c.panel_section(
                    "Куда сохранить",
                    ft.Row(
                        [
                            ft.Container(
                                t.text(str(settings.directory), size=12, font=t.MONO,
                                       color=t.TEXT_SECONDARY, max_lines=2),
                                expand=True,
                            ),
                            c.secondary_button(
                                "Выбрать…", lambda _e: app.page.run_task(self._choose_directory)
                            ),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    spacing=8,
                ),
            ],
            spacing=22,
            expand=True,
        )

        sheets = ft.Row(
            [
                ft.Container(
                    content=ft.Text(str(index + 1), size=10, color="#6b6354", font_family=t.MONO),
                    width=62,
                    height=88,
                    bgcolor="#efe7d4",
                    alignment=ft.Alignment.BOTTOM_CENTER,
                    border_radius=2,
                    padding=4,
                )
                for index in settings.pages(total_pages)[:4]
            ],
            spacing=8,
            wrap=True,
            run_spacing=8,
        )

        right = ft.Container(
            content=ft.Column(
                [
                    sheets,
                    t.text(
                        f"{len(names)} файл{'' if len(names) == 1 else 'а'} "
                        f"{settings.fmt.upper()}",
                        size=13,
                        color=t.TEXT_PRIMARY,
                        weight="500",
                    ),
                    t.hint(estimate_size(app.project, settings) + " всего", size=12, color=t.TEXT_MUTED),
                    t.hint("Имена: " + ", ".join(names[:2]) + (" …" if len(names) > 2 else ""),
                           size=11, color=t.TEXT_FAINTER),
                ],
                spacing=12,
            ),
            width=212,
        )

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    t.text("Экспорт выпуска", size=18, color=t.TEXT_PRIMARY, weight="600"),
                                    t.hint(
                                        f"{app.project.issue.title}, № {app.project.issue.number} · "
                                        f"{total_pages} полос",
                                        size=12,
                                        color=t.TEXT_MUTED,
                                    ),
                                ],
                                spacing=4,
                            ),
                            ft.Container(
                                ft.Icon(ft.Icons.CLOSE, size=16, color=t.TEXT_MUTED),
                                on_click=lambda _e: app.navigate("layout"),
                                padding=8,
                                ink=True,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    tabs,
                    ft.Row([left, right], spacing=28, vertical_alignment=ft.CrossAxisAlignment.START),
                    ft.Column([self.progress, self.status], spacing=8),
                    ft.Row(
                        [
                            ft.Container(
                                t.hint("Рендер идёт локально, сеть не нужна.", size=11,
                                       color=t.TEXT_FAINTER),
                                expand=True,
                            ),
                            c.secondary_button("Закрыть", lambda _e: app.navigate("layout")),
                            c.primary_button(
                                f"Выгрузить {settings.fmt.upper()}", self._run
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=22,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            width=680,
            bgcolor=t.BG_WINDOW,
            border=ft.Border.all(1, t.BORDER_WINDOW),
            border_radius=t.RADIUS_WINDOW,
            padding=ft.Padding.symmetric(vertical=24, horizontal=26),
        )
