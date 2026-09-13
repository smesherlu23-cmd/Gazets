"""Экран 05 — главный экран вёрстки: полоса, статьи, панели, статус.

Превью — картинка, отрендеренная браузерным движком; поверх неё интерфейс
кладёт прозрачные слои: зоны выделения блоков, цели для перетаскивания статей
и ручки для растягивания границ. Координаты слоёв приходят из того же
замера, что считает вместимость (см. render.engine.MEASURE_JS).
"""

from __future__ import annotations

import flet as ft

from ..models import Article, Block
from ..presets import MODULE_TITLES, make_module
from . import common as c
from . import panels
from . import theme as t
from . import thumbs
from .preview import PreviewResult
from .state import AppState

HANDLE = 8.0


class LayoutScreen:
    """Держит ссылки на контролы, чтобы обновлять превью без пересборки экрана."""

    def __init__(self, app: AppState) -> None:
        self.app = app
        sheet_w, sheet_h = app.sheet_size()
        self.image = ft.Image(
            src=app.preview_b64,
            width=sheet_w * app.zoom,
            height=sheet_h * app.zoom,
            fit=ft.BoxFit.FILL,
            gapless_playback=True,
        )
        self.overlay = ft.Stack(controls=[], width=sheet_w * app.zoom,
                                height=sheet_h * app.zoom)
        self.status = ft.Row([], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.placeholder = ft.Container(
            content=ft.Column(
                [
                    ft.ProgressRing(width=18, height=18, stroke_width=2, color=t.ACCENT),
                    t.hint("Собираем полосу…", size=12),
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            visible=app.preview_image is None,
            width=sheet_w * app.zoom,
            height=sheet_h * app.zoom,
            bgcolor=t.BG_CANVAS,
        )
        self.left_holder = ft.Container(content=build_left_rail(app))
        self.panel_holder = ft.Container(content=panels.build(app))
        app.add_preview_listener(self._on_preview)

    # ------------------------------------------------------------------ превью
    def _on_preview(self, result: PreviewResult) -> None:
        app = self.app
        if result.image_b64:
            self.image.src = result.image_b64
            self.placeholder.visible = False
        self.overlay.controls = self._overlay_controls()
        self._fill_status()
        self.left_holder.content = build_left_rail(app)
        self.panel_holder.content = panels.build(app)
        try:
            app.page.update()
        except Exception:
            pass

    def _scaled(self, value: float) -> float:
        return value * self.app.zoom

    def _overlay_controls(self) -> list[ft.Control]:
        """Зоны блоков и ручки границ — по дереву сетки, а не по строкам."""
        app = self.app
        controls: list[ft.Control] = []
        page = app.page_model
        for frame in page.leaves():
            block = frame.block
            fit = app.fit_of(block.id) if block else None
            if block is None or fit is None:
                continue
            controls.append(self._block_zone(block, fit))
        for container in page.frames():
            if container.is_leaf:
                continue
            for index in range(len(container.children) - 1):
                before = app.frame_rect(container.children[index].id)
                after = app.frame_rect(container.children[index + 1].id)
                if before is None or after is None:
                    continue
                controls.append(self._handle(container, index, before, after))
        return controls

    def _handle(self, container, index: int, before, after) -> ft.Control:
        """Полоска на стыке соседей: тянется мышью, меняет их доли."""
        horizontal = container.direction == "row"

        def on_update(event: ft.DragUpdateEvent) -> None:
            delta = event.local_delta.x if horizontal else event.local_delta.y
            self._resize_siblings(container, index, delta / max(self.app.zoom, 0.05))

        if horizontal:
            left = self._scaled((before.x + before.width + after.x) / 2) - HANDLE / 2
            top = self._scaled(min(before.y, after.y))
            width, height = HANDLE, self._scaled(max(before.height, after.height))
            cursor = ft.MouseCursor.RESIZE_LEFT_RIGHT
        else:
            left = self._scaled(min(before.x, after.x))
            top = self._scaled((before.y + before.height + after.y) / 2) - HANDLE / 2
            width, height = self._scaled(max(before.width, after.width)), HANDLE
            cursor = ft.MouseCursor.RESIZE_UP_DOWN

        return ft.Container(
            content=ft.GestureDetector(
                content=ft.Container(width=width, height=height, bgcolor="#00000001"),
                on_pan_update=on_update,
                on_pan_end=lambda _e: self.app.touch(immediate=True),
                mouse_cursor=cursor,
            ),
            left=left,
            top=top,
        )

    def _resize_siblings(self, container, index: int, delta: float) -> None:
        """Перераспределяет место между двумя соседями внутри контейнера."""
        app = self.app
        before, after = container.children[index], container.children[index + 1]
        rect_before = app.frame_rect(before.id)
        rect_after = app.frame_rect(after.id)
        if rect_before is None or rect_after is None:
            return
        horizontal = container.direction == "row"
        size_before = rect_before.width if horizontal else rect_before.height
        size_after = rect_after.width if horizontal else rect_after.height

        if before.fixed is not None:
            before.fixed = max(40.0, before.fixed + delta)
        elif after.fixed is not None:
            after.fixed = max(40.0, after.fixed - delta)
        else:
            span = size_before + size_after
            if span <= 0:
                return
            total = before.weight + after.weight
            share = max(0.12, min(0.88, (size_before + delta) / span))
            before.weight = round(total * share, 4)
            after.weight = round(total * (1 - share), 4)
        app.refresh_preview(immediate=True)

    def _block_zone(self, block: Block, fit) -> ft.Control:
        app = self.app
        selected = app.selected_block_id == block.id
        percent = fit.percent
        border_color = t.ACCENT if selected else (
            t.WARN if percent > 100 and app.show_borders else None
        )
        inner: list[ft.Control] = []
        if selected:
            inner.append(
                ft.Container(
                    content=ft.Text(
                        f"{block.label.upper()} · {block.columns} КОЛ. · {percent:.0f} %",
                        size=9,
                        color="#ffffff",
                        font_family=t.UI_MEDIUM,
                    ),
                    bgcolor=t.ACCENT,
                    padding=ft.Padding.symmetric(vertical=3, horizontal=7),
                    right=0,
                    top=0,
                )
            )

        # почти прозрачная заливка обязательна: иначе Flutter не ловит клики по блоку
        surface = ft.Container(
            content=ft.Stack(inner) if inner else None,
            width=self._scaled(fit.width),
            height=self._scaled(fit.height),
            border=ft.Border.all(1.5, border_color) if border_color else None,
            bgcolor=ft.Colors.with_opacity(0.08, t.ACCENT) if percent > 100 else "#01C05B42",
        )

        gesture = ft.GestureDetector(
            content=surface,
            # повторный щелчок по выделенному блоку снимает выделение
            on_tap=lambda _event, block_id=block.id: app.select_block(
                None if app.selected_block_id == block_id else block_id
            ),
            on_double_tap=lambda _e, block=block: self._open_block(block),
            mouse_cursor=ft.MouseCursor.CLICK,
        )
        target = ft.DragTarget(
            group="article",
            content=gesture,
            on_accept=lambda event, block_id=block.id: self._accept_article(event, block_id),
        )
        return ft.Container(content=target, left=self._scaled(fit.x), top=self._scaled(fit.y))

    # ------------------------------------------------------------ манипуляции
    def _accept_article(self, event, block_id: str) -> None:
        article_id = self.app.drag_payload
        if not article_id:
            return
        self.app.project.assign(article_id, block_id)
        self.app.selected_block_id = block_id
        self.app.drag_payload = None
        self.app.touch(rebuild=True, immediate=True)

    def _open_block(self, block: Block) -> None:
        app = self.app
        app.selected_block_id = block.id
        if block.article_id:
            app.editing_article_id = block.article_id
            app.navigate("article")
        else:
            app.rebuild()

    # ------------------------------------------------------------------ статус
    def _fill_status(self) -> None:
        app = self.app
        overflow = app.overflowing_blocks()
        items: list[ft.Control] = [
            t.hint(f"Полоса {app.current_page + 1} из {len(app.project.pages)}", size=11,
                   color=t.TEXT_MUTED),
            t.hint(f"Масштаб {app.zoom * 100:.0f} %", size=11, color=t.TEXT_MUTED),
        ]
        if overflow:
            items.append(
                ft.Row(
                    [c.dot(t.WARN), t.hint(f"Переполнение: {len(overflow)} блок", size=11, color=t.WARN)],
                    spacing=6,
                )
            )
        else:
            items.append(
                ft.Row([c.dot(t.OK_BAR), t.hint("Всё помещается", size=11, color=t.OK_TEXT)], spacing=6)
            )
        if app.busy_note:
            items.append(t.hint(app.busy_note, size=11, color=t.ACCENT_TEXT))
        if app.preview_error:
            items.append(t.hint(f"Рендер: {app.preview_error[:80]}", size=11, color=t.WARN))
        items.append(ft.Container(expand=True))
        items.append(
            t.hint(
                f"Бумага: состаривание {app.project.paper.intensity if app.project.paper.enabled else 0} %",
                size=11,
                color=t.TEXT_MUTED,
            )
        )
        items.append(t.hint(f"Пересборка {app.last_render_ms} мс", size=11, color=t.TEXT_FAINTER))
        items.append(t.hint(f"Автосохранение {app.autosave_stamp}", size=11, color=t.TEXT_MUTED))
        self.status.controls = items

    # -------------------------------------------------------------------- сборка
    def build(self) -> ft.Control:
        app = self.app
        sheet_w, sheet_h = app.sheet_size()
        self.overlay.controls = self._overlay_controls()
        self.overlay.width = sheet_w * app.zoom
        self.overlay.height = sheet_h * app.zoom
        self.image.width = sheet_w * app.zoom
        self.image.height = sheet_h * app.zoom
        self.placeholder.width = sheet_w * app.zoom
        self.placeholder.height = sheet_h * app.zoom
        self.left_holder.content = build_left_rail(app)
        self.panel_holder.content = panels.build(app)
        self._fill_status()

        canvas = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Stack(
                            [
                                ft.Container(
                                    content=self.image,
                                    shadow=ft.BoxShadow(
                                        blur_radius=40,
                                        spread_radius=0,
                                        color=ft.Colors.with_opacity(0.6, "#000000"),
                                        offset=ft.Offset(0, 14),
                                    ),
                                ),
                                self.placeholder,
                                self.overlay,
                                *self._corner_marks(),
                            ]
                        ),
                        margin=ft.Margin.only(top=18, bottom=18),
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            bgcolor=t.BG_CANVAS,
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
        )

        body = ft.Row(
            [self.left_holder, canvas, self.panel_holder],
            spacing=0,
            expand=True,
        )
        return ft.Column(
            [
                _menu_bar(app),
                ft.Container(height=1, bgcolor=t.BORDER_PANEL),
                body,
                ft.Container(height=1, bgcolor=t.BORDER_PANEL),
                ft.Container(
                    content=self.status,
                    height=28,
                    bgcolor=t.BG_TITLEBAR,
                    padding=ft.Padding.symmetric(vertical=0, horizontal=14),
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _corner_marks(self) -> list[ft.Control]:
        size, offset = 6, -3
        width = self.app.sheet_size()[0] * self.app.zoom
        height = self.app.sheet_size()[1] * self.app.zoom
        positions = [
            {"left": offset, "top": offset},
            {"left": width + offset - size, "top": offset},
            {"left": offset, "top": height + offset - size},
            {"left": width + offset - size, "top": height + offset - size},
        ]
        return [
            ft.Container(width=size, height=size, bgcolor=t.ACCENT, **position)
            for position in positions
        ]


# ------------------------------------------------------------------ левая панель


def build_left_rail(app: AppState) -> ft.Control:
    pages = ft.Row(
        [
            ft.Container(
                thumbs.page_thumb(index == app.current_page, index + 1),
                on_click=(lambda index: lambda _e: _go_page(app, index))(index),
                tooltip=f"Полоса {index + 1}",
            )
            for index in range(len(app.project.pages))
        ]
        + [
            ft.Container(
                content=ft.Text("+", size=16, color=t.TEXT_SECONDARY),
                width=44,
                height=62,
                alignment=ft.Alignment.CENTER,
                border=ft.Border.all(1, t.BORDER_STRONG),
                border_radius=2,
                on_click=lambda _e: app.add_page(),
                ink=True,
                tooltip="Добавить полосу",
            )
        ],
        spacing=8,
        wrap=True,
        run_spacing=8,
    )
    page_tools = ft.Row(
        [
            _tool(app, ft.Icons.ARROW_BACK, "Сдвинуть полосу влево",
                  lambda: app.move_page(app.current_page, -1)),
            _tool(app, ft.Icons.ARROW_FORWARD, "Сдвинуть полосу вправо",
                  lambda: app.move_page(app.current_page, 1)),
            _tool(app, ft.Icons.COPY_ALL_OUTLINED, "Дублировать полосу",
                  lambda: app.duplicate_page(app.current_page)),
            _tool(app, ft.Icons.CLOSE, "Удалить полосу",
                  lambda: app.remove_page(app.current_page)),
            ft.Container(expand=True),
            c.ghost_button("Сетка полосы", lambda _e: app.navigate("grid_edit")),
        ],
        spacing=4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    rows: list[ft.Control] = []
    for article in app.project.articles:
        rows.append(_article_row(app, article))
    unplaced = app.project.unplaced_articles()
    if unplaced:
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        t.caps("Не размещено", size=10, color=t.TEXT_FAINT),
                        t.hint("перетащите в блок", size=10, color=t.TEXT_FAINTER),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.Padding.only(top=8, bottom=4),
            )
        )

    modules = ft.Row(
        [
            ft.Container(
                content=t.text(label, size=11, color=t.TEXT_SECONDARY),
                padding=ft.Padding.symmetric(vertical=5, horizontal=10),
                bgcolor=t.BG_CONTROL,
                border=ft.Border.all(1, t.BORDER_BASE),
                border_radius=99,
                on_click=(lambda kind: lambda _e: _add_module(app, kind))(kind),
                ink=True,
            )
            for kind, label in MODULE_TITLES.items()
        ],
        spacing=6,
        wrap=True,
        run_spacing=6,
    )

    return c.rail(
        ft.Column(
            [
                c.panel_section("Полосы", pages, page_tools, spacing=8),
                ft.Row(
                    [
                        t.caps("Статьи"),
                        t.hint(str(len(app.project.articles)), size=11, color=t.TEXT_MUTED),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(rows, spacing=2, scroll=ft.ScrollMode.AUTO, expand=True),
                c.primary_button("Добавить статью", lambda _e: _add_article(app), icon=ft.Icons.ADD,
                                 width=224),
                c.panel_section("Модули", modules, spacing=8),
            ],
            spacing=14,
            expand=True,
        ),
        width=256,
    )


def _article_row(app: AppState, article: Article) -> ft.Control:
    fit = app.article_fit(article.id)
    placed = any(
        block.article_id == article.id for page in app.project.pages for block in page.blocks()
    )
    selected_block = app.selected_block
    active = selected_block is not None and selected_block.article_id == article.id
    overflow = fit is not None and fit.overflows

    lines: list[ft.Control] = [
        t.text(
            article.rubric.upper() or ("НЕ РАЗМЕЩЕНО" if not placed else "БЕЗ РУБРИКИ"),
            size=10,
            color=t.ACCENT if active else t.TEXT_FAINT,
            tracking=0.8,
            weight="500",
        ),
        t.text(article.title, size=13, color=t.TEXT_PRIMARY if placed else t.TEXT_SECONDARY,
               max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
        t.hint(
            f"{article.char_count} зн. · {article.word_count} сл."
            + (f" · {fit.percent:.0f} %" if fit else ""),
            size=11,
            color=t.TEXT_MUTED,
        ),
    ]
    if overflow and fit is not None:
        lines.append(
            ft.Row(
                [c.dot(t.WARN), t.hint(f"не помещается: {fit.overflow_chars} зн.", size=11, color=t.WARN)],
                spacing=6,
            )
        )

    body = ft.Container(
        content=ft.Row(
            [
                ft.Container(width=2, bgcolor=t.ACCENT if active else "transparent"),
                ft.Container(
                    ft.Column(lines, spacing=2),
                    expand=True,
                    padding=ft.Padding.symmetric(vertical=6, horizontal=8),
                ),
            ],
            spacing=0,
        ),
        bgcolor=t.BG_ROW_HOVER if active else (ft.Colors.with_opacity(0.07, t.ACCENT) if overflow else None),
        border_radius=2,
        on_click=lambda _e: _select_article(app, article.id),
    )

    return ft.Draggable(
        group="article",
        content=ft.GestureDetector(
            content=body,
            on_double_tap=lambda _e: _edit(app, article.id),
        ),
        content_feedback=ft.Container(
            content=t.text(article.title, size=12, color="#ffffff"),
            bgcolor=t.ACCENT,
            padding=ft.Padding.symmetric(vertical=6, horizontal=10),
            border_radius=3,
            width=200,
        ),
        on_drag_start=lambda _e: _start_drag(app, article.id),
    )


def _start_drag(app: AppState, article_id: str) -> None:
    app.drag_payload = article_id


def _select_article(app: AppState, article_id: str) -> None:
    for page_index, page in enumerate(app.project.pages):
        for block in page.blocks():
            if block.article_id == article_id:
                app.current_page = page_index
                app.select_block(block.id)
                return
    app.editing_article_id = article_id
    app.navigate("article")


def _edit(app: AppState, article_id: str) -> None:
    app.editing_article_id = article_id
    app.navigate("article")


def _add_article(app: AppState) -> None:
    article = Article(rubric="", title="Новая статья", body="")
    app.project.articles.append(article)
    app.editing_article_id = article.id
    app.navigate("article")


def _add_module(app: AppState, kind: str) -> None:
    block = app.selected_block
    if block is None:
        for candidate in app.page_model.blocks():
            if candidate.is_empty:
                block = candidate
                break
    if block is None:
        return
    if block.article_id:
        app.project.detach(block.article_id)
    block.kind = "module"
    block.modules.append(make_module(kind))
    app.selected_block_id = block.id
    app.touch(rebuild=True, immediate=True)


def _go_page(app: AppState, index: int) -> None:
    app.current_page = index
    app.selected_block_id = None
    app.rebuild()
    app.refresh_preview(immediate=True)


# --------------------------------------------------------------------- строка меню


def _menu_bar(app: AppState) -> ft.Control:
    def item(label: str, handler) -> ft.Control:
        return ft.Container(
            content=t.text(label, size=12, color=t.TEXT_SECONDARY),
            padding=ft.Padding.symmetric(vertical=0, horizontal=10),
            height=34,
            alignment=ft.Alignment.CENTER,
            on_click=handler,
            ink=True,
        )

    def view_toggle(label: str, value: bool, handler) -> ft.Control:
        return ft.Container(
            content=t.text(label, size=11, color=t.ACCENT_TEXT if value else t.TEXT_MUTED),
            padding=ft.Padding.symmetric(vertical=4, horizontal=10),
            bgcolor=t.tint(0.14) if value else None,
            border=ft.Border.all(1, t.ACCENT if value else t.BORDER_BASE),
            border_radius=99,
            on_click=handler,
            ink=True,
        )

    def zoom(delta: float) -> None:
        app.zoom = max(0.3, min(1.6, round(app.zoom + delta, 2)))
        app.rebuild()

    return ft.Container(
        content=ft.Row(
            [
                item("Проекты", lambda _e: app.navigate("start")),
                _history_item(app, "Отменить", app.can_undo, app.undo),
                _history_item(app, "Вернуть", app.can_redo, app.redo),
                item("Номер", lambda _e: app.navigate("issue_edit")),
                item("Издание", lambda _e: app.open_publications("layout")),
                item("Сетка полосы", lambda _e: app.navigate("grid_edit")),
                item("Экспорт", lambda _e: app.navigate("export")),
                ft.Container(expand=True),
                view_toggle("Модульная сетка", app.show_guides,
                            lambda _e: _toggle(app, "show_guides")),
                view_toggle("Бумага", app.show_paper, lambda _e: _toggle(app, "show_paper")),
                ft.Container(width=1, height=18, bgcolor=t.BORDER_STRONG),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(ft.Text("−", size=13, color=t.TEXT_SECONDARY),
                                         on_click=lambda _e: zoom(-0.06), padding=6, ink=True),
                            t.text(f"{app.zoom * 100:.0f} %", size=12, font=t.MONO),
                            ft.Container(ft.Text("+", size=13, color=t.TEXT_SECONDARY),
                                         on_click=lambda _e: zoom(0.06), padding=6, ink=True),
                            ft.Container(
                                t.text("вписать", size=11, color=t.TEXT_MUTED),
                                on_click=lambda _e: app.zoom_to_fit(),
                                padding=ft.Padding.symmetric(vertical=4, horizontal=8),
                                ink=True,
                                tooltip="Подогнать масштаб под окно",
                            ),
                        ],
                        spacing=2,
                    ),
                ),
            ],
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=34,
        bgcolor=t.BG_WINDOW,
        padding=ft.Padding.symmetric(vertical=0, horizontal=10),
    )


def _tool(app: AppState, icon, hint: str, action) -> ft.Control:
    """Мелкая кнопка-иконка для операций с полосой."""
    return ft.Container(
        content=ft.Icon(icon, size=14, color=t.TEXT_SECONDARY),
        width=26,
        height=26,
        alignment=ft.Alignment.CENTER,
        border=ft.Border.all(1, t.BORDER_BASE),
        border_radius=t.RADIUS_CONTROL,
        on_click=lambda _e: action(),
        ink=True,
        tooltip=hint,
    )


def _history_item(app: AppState, label: str, enabled: bool, action) -> ft.Control:
    """Пункт меню, который гаснет, когда отменять нечего."""
    return ft.Container(
        content=t.text(label, size=12, color=t.TEXT_SECONDARY if enabled else t.TEXT_FAINTER),
        padding=ft.Padding.symmetric(vertical=0, horizontal=10),
        height=34,
        alignment=ft.Alignment.CENTER,
        on_click=(lambda _e: action()) if enabled else None,
        ink=enabled,
        disabled=not enabled,
    )


def _toggle(app: AppState, field: str) -> None:
    setattr(app, field, not getattr(app, field))
    app.rebuild()
    app.refresh_preview(immediate=True)
