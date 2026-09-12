"""Состояние приложения: проект, состояние интерфейса, превью, автосохранение.

Экраны не хранят данных: они читают состояние, меняют его через методы этого
класса и просят перерисовать себя. Любая правка модели проходит через
``touch()`` — он помечает проект изменённым, ставит автосохранение и запускает
пересборку превью.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import threading
from typing import Callable, Optional

import flet as ft

from .. import storage
from ..models import Block, BlockFit, Brand, Issue, Project
from ..presets import demo_project
from ..render.engine import engine, engine_report
from ..render.html import RenderOptions
from .preview import PreviewController, PreviewResult

AUTOSAVE_INTERVAL = 25.0


class Wizard:
    """Черновик нового выпуска: экраны 02 → 03 → 04 заполняют его по шагам."""

    def __init__(self) -> None:
        self.issue = Issue()
        self.preset_id = "classic"
        self.template_id = "front-main-side"
        self.brand: Brand | None = None

    def reset(self) -> None:
        self.__init__()


class AppState:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.project: Project = demo_project()
        self.project_path: Optional[pathlib.Path] = None
        self.dirty = False

        self.wizard = Wizard()
        self.route = "start"
        self.current_page = 0
        self.selected_block_id: Optional[str] = None
        self.editing_article_id: Optional[str] = None
        self.panel_tab = "block"
        self.zoom = 0.74
        self.show_guides = True
        self.show_paper = True
        self.show_borders = False

        self.drag_payload: Optional[str] = None
        self.fits: dict[str, BlockFit] = {}
        self.preview_image: Optional[pathlib.Path] = None
        self.preview_b64: Optional[str] = None
        self.preview_error: Optional[str] = None
        self.last_render_ms = 0
        self.autosave_stamp = "—"
        self.engine_note = ""
        self.brand_tab = "logo"
        self.export_settings = None
        self.screens: dict[str, object] = {}

        self._preview_listeners: list[Callable[[PreviewResult], None]] = []
        self._rebuild: Optional[Callable[[], None]] = None
        self.preview = PreviewController(self._on_preview_ready)
        self._file_picker: Optional[ft.FilePicker] = None
        self._autosave_timer: Optional[threading.Timer] = None

    # ------------------------------------------------------------ диалоги
    def file_picker(self) -> ft.FilePicker:
        """Один диалог выбора файлов на приложение — Flet требует его в services."""
        if self._file_picker is None:
            self._file_picker = ft.FilePicker()
            self.page.services.append(self._file_picker)
            self.page.update()
        return self._file_picker

    # ------------------------------------------------------------- навигация
    def bind_rebuild(self, rebuild: Callable[[], None]) -> None:
        self._rebuild = rebuild

    def navigate(self, route: str) -> None:
        self.route = route
        self.rebuild()

    def rebuild(self) -> None:
        if self._rebuild is not None:
            self._rebuild()

    # --------------------------------------------------------------- превью
    def add_preview_listener(self, listener: Callable[[PreviewResult], None]) -> None:
        self._preview_listeners = [listener]

    def render_options(self, for_export: bool = False) -> RenderOptions:
        return RenderOptions(
            show_guides=self.show_guides and not for_export,
            show_paper=self.show_paper or for_export,
            show_block_borders=self.show_borders and not for_export,
            selected_block_id=None,  # выделение рисует интерфейс поверх картинки
            fit_percents={key: fit.percent for key, fit in self.fits.items()},
            for_export=for_export,
        )

    @property
    def project_dir(self) -> Optional[pathlib.Path]:
        return self.project_path.parent if self.project_path else None

    def refresh_preview(self, immediate: bool = False) -> None:
        self.preview.request(
            self.project,
            self.current_page,
            self.render_options(),
            self.project_dir,
            immediate=immediate,
        )

    def _on_preview_ready(self, result: PreviewResult) -> None:
        if result.page_index != self.current_page:
            return
        self.preview_image = result.image
        if result.image_b64:
            self.preview_b64 = result.image_b64
        self.preview_error = result.error
        self.last_render_ms = result.elapsed_ms
        self.fits = {
            item.id: BlockFit(
                block_id=item.id,
                percent=item.percent,
                overflow_chars=item.overflow,
                x=item.x,
                y=item.y,
                width=item.width,
                height=item.height,
            )
            for item in result.metrics
        }
        for listener in list(self._preview_listeners):
            try:
                listener(result)
            except Exception:
                pass

    # ---------------------------------------------------------------- правка
    def touch(self, rebuild: bool = False, immediate: bool = False) -> None:
        """Проект изменён: перерисовать превью, поставить автосохранение."""
        self.dirty = True
        self.refresh_preview(immediate=immediate)
        self._schedule_autosave()
        if rebuild:
            self.rebuild()

    def _schedule_autosave(self) -> None:
        if self._autosave_timer is not None:
            self._autosave_timer.cancel()
        self._autosave_timer = threading.Timer(AUTOSAVE_INTERVAL, self._autosave)
        self._autosave_timer.daemon = True
        self._autosave_timer.start()

    def _autosave(self) -> None:
        try:
            storage.autosave(self.project, self.project_path)
            self.autosave_stamp = dt.datetime.now().strftime("%H:%M")
            self.rebuild()
        except OSError:
            pass

    # ------------------------------------------------------------ сохранение
    def save(self, path: Optional[pathlib.Path] = None) -> pathlib.Path:
        target = pathlib.Path(path) if path else self.project_path
        if target is None:
            target = storage.documents_dir() / f"{self.project.title}"
        self.project_path = storage.save_project(self.project, target)
        self.dirty = False
        self.autosave_stamp = dt.datetime.now().strftime("%H:%M")
        return self.project_path

    def open(self, path: pathlib.Path) -> None:
        self.project = storage.load_project(pathlib.Path(path))
        self.project_path = pathlib.Path(path)
        self.dirty = False
        self.current_page = 0
        self.selected_block_id = None
        self.fits = {}
        self.navigate("layout")
        self.refresh_preview(immediate=True)

    def set_project(self, project: Project, path: Optional[pathlib.Path] = None) -> None:
        self.project = project
        self.project_path = path
        self.dirty = True
        self.current_page = 0
        self.selected_block_id = None
        self.fits = {}

    # ---------------------------------------------------------------- блоки
    @property
    def page_model(self):
        return self.project.page(self.current_page)

    @property
    def selected_block(self) -> Optional[Block]:
        if not self.selected_block_id:
            return None
        _, block = self.project.find_block(self.selected_block_id)
        return block

    def select_block(self, block_id: Optional[str]) -> None:
        self.selected_block_id = block_id
        if block_id:
            self.panel_tab = "block"
        self.rebuild()

    def fit_of(self, block_id: str) -> Optional[BlockFit]:
        return self.fits.get(block_id)

    def overflowing_blocks(self) -> list[BlockFit]:
        return [fit for fit in self.fits.values() if fit.overflows]

    def article_fit(self, article_id: str) -> Optional[BlockFit]:
        for page in self.project.pages:
            for block in page.blocks():
                if block.article_id == article_id:
                    return self.fits.get(block.id)
        return None

    # -------------------------------------------------------------- движок
    def check_engine(self) -> str:
        self.engine_note = engine_report()
        return self.engine_note

    def shutdown(self) -> None:
        if self._autosave_timer is not None:
            self._autosave_timer.cancel()
        self.preview.shutdown()
        engine().close()
