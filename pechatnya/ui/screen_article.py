"""Экран 06 — редактор статьи: тексты слева, живое превью блока справа.

Превью пересобирается по паузе в наборе (debounce в PreviewController), а не
на каждый символ, поэтому набирать можно спокойно.
"""

from __future__ import annotations

import pathlib

import flet as ft

from .. import storage
from ..models import ImageRef
from . import common as c
from . import theme as t
from .preview import PreviewResult
from .state import AppState


class ArticleScreen:
    def __init__(self, app: AppState) -> None:
        self.app = app
        self.article = app.project.article(app.editing_article_id)
        self.preview = ft.Image(
            src=app.preview_b64,
            width=406,
            fit=ft.BoxFit.FIT_WIDTH,
            gapless_playback=True,
        )
        self.counter = ft.Text("", size=11, color=t.TEXT_MUTED, font_family=t.MONO)
        self.fit_line = ft.Row([], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.body_field: ft.TextField | None = None
        self.selection: tuple[int, int] | None = None
        app.add_preview_listener(self._on_preview)

    # ------------------------------------------------------------------ превью
    def _on_preview(self, result: PreviewResult) -> None:
        if result.image_b64:
            self.preview.src = result.image_b64
        self._update_counters()
        try:
            self.app.page.update()
        except Exception:
            pass

    def _update_counters(self) -> None:
        article = self.article
        if article is None:
            return
        self.counter.value = f"{article.char_count} знаков · {article.word_count} слов"
        fit = self.app.article_fit(article.id)
        if fit is None:
            self.fit_line.controls = [t.hint("Статья не размещена на полосе", size=12)]
        elif fit.overflows:
            self.fit_line.controls = [
                c.dot(t.WARN),
                t.text(
                    f"Не помещается: {fit.overflow_chars} зн. — сократите текст "
                    f"или включите «продолжение на стр.»",
                    size=12,
                    color=t.WARN,
                ),
            ]
        else:
            self.fit_line.controls = [
                c.dot(t.OK_BAR),
                t.text(f"Помещается в блок: {fit.percent:.0f} % высоты", size=12, color=t.OK_TEXT),
            ]

    # ------------------------------------------------------------------- правка
    def _edit(self, field: str):
        def handler(value) -> None:
            setattr(self.article, field, value)
            self.app.touch()
            self._update_counters()
            try:
                self.counter.update()
                self.fit_line.update()
            except Exception:
                pass

        return handler

    def _remember_selection(self, event) -> None:
        selection = getattr(event.control, "selection", None)
        if selection is None:
            self.selection = None
            return
        start = min(selection.base_offset, selection.extent_offset)
        end = max(selection.base_offset, selection.extent_offset)
        self.selection = (start, end) if end > start else None

    def _wrap_selection(self, marker: str) -> None:
        """Ж/К — оборачивают выделенный фрагмент разметкой."""
        field = self.body_field
        if field is None or self.article is None:
            return
        value = field.value or ""
        if self.selection is None:
            return
        start, end = self.selection
        start, end = max(0, start), min(len(value), end)
        if start >= end:
            return
        new_value = value[:start] + marker + value[start:end] + marker + value[end:]
        field.value = new_value
        self.article.body = new_value
        self.selection = None
        field.update()
        self.app.touch()

    def _insert(self, snippet: str) -> None:
        field = self.body_field
        if field is None or self.article is None:
            return
        field.value = (field.value or "").rstrip() + snippet
        self.article.body = field.value
        field.update()
        self.app.touch()

    async def _pick_photo(self, _event=None) -> None:
        files = await self.app.file_picker().pick_files(
            dialog_title="Иллюстрация к статье",
            allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp"],
        )
        if not files or self.article is None:
            return
        relative = storage.import_image(pathlib.Path(files[0].path), self.app.project_path)
        self.article.image = ImageRef(path=relative, caption="", height_px=96)
        self.app.touch(rebuild=True)

    # -------------------------------------------------------------------- сборка
    def build(self) -> ft.Control:
        app = self.app
        article = self.article
        if article is None:
            return ft.Container(
                content=t.text("Статья не найдена", size=14),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        self._update_counters()

        toolbar = ft.Container(
            content=ft.Row(
                [
                    _tool_button("Ж", lambda _e: self._wrap_selection("**"), font="PT Serif Bold",
                                 tooltip="Выделите фрагмент и нажмите — станет полужирным"),
                    _tool_button("К", lambda _e: self._wrap_selection("*"), italic=True,
                                 tooltip="Выделите фрагмент и нажмите — станет курсивом"),
                    ft.Container(width=1, height=18, bgcolor=t.BORDER_BASE),
                    c.chip("Буквица", article.drop_cap, lambda _e: self._toggle_drop_cap(), height=26),
                    c.chip("Подзаголовок", False, lambda _e: self._insert("\n\n## ПОДЗАГОЛОВОК\n\n"),
                           height=26),
                    c.chip("Врезка-цитата", False, lambda _e: self._insert("\n\n> Цитата\n\n"), height=26),
                    c.chip("Вставить фото…", article.image is not None,
                           lambda _e: app.page.run_task(self._pick_photo), height=26),
                    ft.Container(expand=True),
                    self.counter,
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=44,
            padding=ft.Padding.symmetric(vertical=0, horizontal=16),
            bgcolor=t.BG_WINDOW,
            border=ft.Border.only(bottom=ft.BorderSide(1, t.BORDER_PANEL)),
        )

        self.body_field = ft.TextField(
            value=article.body,
            on_change=lambda event: self._edit("body")(event.control.value),
            on_selection_change=self._remember_selection,
            multiline=True,
            min_lines=12,
            expand=True,
            border_radius=t.RADIUS_CONTROL,
            border_color=t.BORDER_BASE,
            focused_border_color=t.ACCENT,
            bgcolor=t.BG_FIELD,
            color=t.TEXT_BODY,
            cursor_color=t.ACCENT,
            cursor_width=1,
            cursor_height=16,
            selection_color=ft.Colors.with_opacity(0.22, t.ACCENT),
            text_size=14,
            text_style=ft.TextStyle(height=1.7, font_family=t.UI),
            content_padding=ft.Padding.symmetric(vertical=12, horizontal=12),
        )

        editor = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                c.field("Рубрика", article.rubric, self._edit("rubric"),
                                        hint="например: хроника происшествий"),
                                expand=True,
                            ),
                            ft.Container(
                                c.field("Автор", article.author, self._edit("author"),
                                        hint="кто написал"),
                                expand=True,
                            ),
                            ft.Container(
                                c.field("Место и время", article.place_time,
                                        self._edit("place_time"), hint="где и когда"),
                                expand=True,
                            ),
                        ],
                        spacing=12,
                    ),
                    c.field("Заголовок", article.title, self._edit("title"), height=40, text_size=17,
                            hint="о чём материал"),
                    c.field("Подзаголовок", article.subtitle, self._edit("subtitle"),
                            hint="лид — одно-два предложения"),
                    ft.Row(
                        [
                            t.text("Текст статьи", size=12, color=t.TEXT_SECONDARY, expand=True),
                            t.hint("**жирный** · *курсив* · ## подзаголовок · > цитата", size=11,
                                   color=t.TEXT_FAINTER),
                        ]
                    ),
                    self.body_field,
                    ft.Row(
                        [
                            ft.Container(self.fit_line, expand=True),
                            c.ghost_button("Удалить статью", lambda _e: self._delete()),
                            c.secondary_button("Закрыть", lambda _e: app.navigate("layout")),
                            c.primary_button("Применить к полосе",
                                             lambda _e: self._apply()),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=16,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            padding=ft.Padding.symmetric(vertical=18, horizontal=20),
            expand=True,
        )

        pages = len(app.project.pages)
        placed_on = app.project.page_of_article(article.id, part=0)
        target = app.continuation_target or (
            article.continued_on or min(pages, (placed_on or 0) + 2)
        )
        continuation_controls: list[ft.Control] = []
        if placed_on is None:
            continuation_controls.append(
                t.hint("Разместите статью на полосе, чтобы разделить её между полосами.", size=11)
            )
        else:
            continuation_controls.append(
                ft.Row(
                    [
                        c.stepper(
                            "Продолжение на стр.",
                            target,
                            lambda value: setattr(app, "continuation_target", int(value)),
                            minimum=1,
                            maximum=max(1, pages),
                            width=104,
                        ),
                    ],
                    spacing=10,
                )
            )
            continuation_controls.append(
                c.secondary_button(
                    "Перенести остаток",
                    lambda _e: app.split_article(article.id, int(target) - 1),
                    height=30,
                )
            )
            if article.split_at is not None:
                continuation_controls.append(
                    t.hint(
                        f"Остаток {len(article.part_text(1))} зн. стоит на стр. "
                        f"{article.continued_on}",
                        size=11,
                        color=t.OK_TEXT,
                    )
                )
                continuation_controls.append(
                    c.ghost_button("Убрать перенос", lambda _e: app.drop_split(article.id))
                )
            if app.busy_note:
                continuation_controls.append(t.hint(app.busy_note, size=11, color=t.ACCENT_TEXT))
        continuation = ft.Column(continuation_controls, spacing=10)

        side = ft.Container(
            content=ft.Column(
                [
                    self.preview,
                    continuation,
                    t.hint(
                        "Превью пересобирается по паузе в наборе. Если текст не влезает, "
                        "поставьте номер полосы — внизу блока появится строка «продолжение на стр.».",
                        size=11,
                        color=t.TEXT_FAINTER,
                    ),
                ],
                spacing=14,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=470,
            bgcolor=t.BG_CANVAS,
            padding=ft.Padding.symmetric(vertical=18, horizontal=16),
        )

        return ft.Column(
            [toolbar, ft.Row([editor, side], spacing=0, expand=True)],
            spacing=0,
            expand=True,
        )

    def _toggle_drop_cap(self) -> None:
        if self.article is None:
            return
        self.article.drop_cap = not self.article.drop_cap
        self.app.touch(rebuild=True)

    def _apply(self) -> None:
        self.app.touch(immediate=True)
        self.app.navigate("layout")

    def _delete(self) -> None:
        """Убирает статью из выпуска целиком — и с полосы, и из списка."""
        if self.article is None:
            return
        self.app.project.detach(self.article.id)
        self.app.project.articles = [
            item for item in self.app.project.articles if item.id != self.article.id
        ]
        self.app.editing_article_id = None
        self.app.touch(immediate=True)
        self.app.navigate("layout")


def _tool_button(
    label: str, handler, font: str = t.UI, italic: bool = False, tooltip: str = ""
) -> ft.Control:
    return ft.Container(
        tooltip=tooltip or None,
        content=ft.Text(label, size=13, color=t.TEXT_SECONDARY, font_family=font, italic=italic),
        width=28,
        height=26,
        alignment=ft.Alignment.CENTER,
        bgcolor=t.BG_CONTROL,
        border=ft.Border.all(1, t.BORDER_BASE),
        border_radius=t.RADIUS_CONTROL,
        on_click=handler,
        ink=True,
    )
