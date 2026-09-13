"""Состояние приложения: проект, состояние интерфейса, превью, автосохранение.

Экраны не хранят данных: они читают состояние, меняют его через методы этого
класса и просят перерисовать себя. Любая правка модели проходит через
``touch()`` — он помечает проект изменённым, ставит автосохранение и запускает
пересборку превью.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import time
import threading
from typing import Callable, Optional

import flet as ft

from .. import storage
from ..models import Block, BlockFit, Issue, Project, Publication
from ..presets import new_project
from ..serde import from_dict, to_dict
from ..render.engine import engine, engine_report
from ..render.split import fit_split_point
from ..render.html import RenderOptions
from .preview import PreviewController, PreviewResult

AUTOSAVE_INTERVAL = 25.0
UNDO_DEPTH = 60
UNDO_COALESCE = 1.2  # с — правки подряд складываются в один шаг отмены


class Wizard:
    """Черновик нового выпуска: издание и данные номера, затем сетка полосы."""

    def __init__(self) -> None:
        self.issue = Issue()
        self.template_id = "front-main-side"
        self.publication_id = ""

    def reset(self) -> None:
        self.__init__()


class AppState:
    def __init__(self, page: ft.Page, start_preview: bool = True) -> None:
        """``start_preview=False`` — состояние без фонового рендера, для тестов."""
        self.page = page
        self.project: Project = new_project()
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

        self._undo: list[str] = []
        self._redo: list[str] = []
        self._snapshot = json.dumps(to_dict(self.project), ensure_ascii=False)
        self._snapshot_at = 0.0
        self.drag_payload: Optional[str] = None
        self.fits: dict[str, BlockFit] = {}
        self.preview_image: Optional[pathlib.Path] = None
        self.preview_b64: Optional[str] = None
        self.preview_error: Optional[str] = None
        self.last_render_ms = 0
        self.autosave_stamp = "—"
        self.busy_note = ""
        self.continuation_target = 0
        self.engine_note = ""
        self.start_filter = ""
        self.publication_tab = "logo"
        self.editing_publication: Optional[Publication] = None
        self.publication_dirty = False
        self.publication_return_route = "start"
        self.export_settings = None
        self.screens: dict[str, object] = {}

        self._preview_listeners: list[Callable[[PreviewResult], None]] = []
        self._rebuild: Optional[Callable[[], None]] = None
        self.preview: Optional[PreviewController] = (
            PreviewController(self._on_preview_ready) if start_preview else None
        )
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
        if self.preview is None:
            return
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
    # ------------------------------------------------------------- история
    def _remember(self) -> None:
        """Кладёт прошлое состояние в стопку отмены, схлопывая частые правки."""
        now = time.monotonic()
        if now - self._snapshot_at < UNDO_COALESCE and self._undo:
            self._snapshot = json.dumps(to_dict(self.project), ensure_ascii=False)
            return
        current = json.dumps(to_dict(self.project), ensure_ascii=False)
        if current == self._snapshot:
            return
        self._undo.append(self._snapshot)
        del self._undo[:-UNDO_DEPTH]
        self._redo.clear()
        self._snapshot = current
        self._snapshot_at = now

    def reset_history(self) -> None:
        """Новый выпуск — новая история: отменять предыдущий проект нельзя."""
        self._undo.clear()
        self._redo.clear()
        self._snapshot = json.dumps(to_dict(self.project), ensure_ascii=False)
        self._snapshot_at = 0.0

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(json.dumps(to_dict(self.project), ensure_ascii=False))
        self._apply_snapshot(self._undo.pop())
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(json.dumps(to_dict(self.project), ensure_ascii=False))
        self._apply_snapshot(self._redo.pop())
        return True

    def _apply_snapshot(self, snapshot: str) -> None:
        self.project = Project.from_json_dict(json.loads(snapshot))
        self._snapshot = snapshot
        self._snapshot_at = time.monotonic()
        if self.selected_block_id and self.selected_block is None:
            self.selected_block_id = None
        self.dirty = True
        self.refresh_preview(immediate=True)
        self._schedule_autosave()
        self.rebuild()

    def touch(self, rebuild: bool = False, immediate: bool = False) -> None:
        """Проект изменён: запомнить для отмены, перерисовать превью, автосохранить."""
        self._remember()
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
        """Сохраняет выпуск; картинки при этом переезжают в папку проекта."""
        previous_dir = self.project_dir
        target = pathlib.Path(path) if path else self.project_path
        if target is None:
            target = storage.documents_dir() / (self.project.title or "Выпуск")
        self.project_path = storage.save_project(self.project, target, source_dir=previous_dir)
        self.dirty = False
        self.autosave_stamp = dt.datetime.now().strftime("%H:%M")
        self._snapshot = json.dumps(to_dict(self.project), ensure_ascii=False)
        return self.project_path

    async def save_as(self) -> Optional[pathlib.Path]:
        """«Сохранить как…» — выбор места и имени файла."""
        suggested = (self.project.title or "Выпуск").replace("/", "-")
        chosen = await self.file_picker().save_file(
            dialog_title="Сохранить выпуск как…",
            file_name=f"{suggested}{storage.PROJECT_SUFFIX}",
            initial_directory=str(self.project_dir or storage.documents_dir()),
            allowed_extensions=["json"],
        )
        if not chosen:
            return None
        path = self.save(pathlib.Path(chosen))
        self.rebuild()
        return path

    def open(self, path: pathlib.Path) -> None:
        self.project = storage.load_project(pathlib.Path(path))
        self.project_path = pathlib.Path(path)
        self.reset_history()
        self.dirty = False
        self.current_page = 0
        self.selected_block_id = None
        self.fits = {}
        self.navigate("layout")
        self.refresh_preview(immediate=True)

    def set_project(self, project: Project, path: Optional[pathlib.Path] = None) -> None:
        self.project = project
        self.project_path = path
        self.reset_history()
        self.dirty = True
        self.current_page = 0
        self.selected_block_id = None
        self.fits = {}

    # ------------------------------------------------- продолжение на стр. N
    def split_article(self, article_id: str, page_index: int) -> None:
        """Подбирает точку разрыва и кладёт остаток статьи на выбранную полосу."""
        if self.busy_note:
            return
        article = self.project.article(article_id)
        if article is None or self.project.block_of(article_id, part=0) is None:
            return
        if self.project.free_block_on(page_index) is None and (
            self.project.block_of(article_id, part=1) is None
        ):
            self.busy_note = f"На полосе {page_index + 1} нет свободного блока"
            self.rebuild()
            return

        self.busy_note = "подбираем перенос…"
        self.rebuild()

        def worker() -> None:
            try:
                point = fit_split_point(
                    self.project,
                    article_id,
                    self.project_dir,
                    progress=self._set_busy,
                )
                if point is None:
                    self.busy_note = "Статья помещается целиком — перенос не нужен"
                elif point <= 0:
                    self.busy_note = "В блок не влезает даже начало статьи"
                else:
                    self.project.place_continuation(article_id, page_index, point)
                    self.busy_note = (
                        f"Остаток ({len(article.part_text(1))} зн.) перенесён "
                        f"на полосу {page_index + 1}"
                    )
                    self.touch(immediate=True)
            except Exception as error:  # движок мог отвалиться
                self.busy_note = f"Не удалось подобрать перенос: {error}"
            finally:
                self.rebuild()

        threading.Thread(target=worker, name="pechatnya-split", daemon=True).start()

    def _set_busy(self, note: str) -> None:
        self.busy_note = note
        self.rebuild()

    def drop_split(self, article_id: str) -> None:
        self.project.drop_continuation(article_id)
        self.busy_note = ""
        self.continuation_target = 0
        self.touch(rebuild=True, immediate=True)

    # -------------------------------------------------------------- издания
    @property
    def publications(self) -> list[Publication]:
        return storage.publications()

    @property
    def publication_back_label(self) -> str:
        return {
            "layout": "К вёрстке",
            "issue": "К созданию выпуска",
        }.get(self.publication_return_route, "К списку проектов")

    def open_publications(self, return_route: str = "layout") -> None:
        """Открывает редактор изданий, запоминая, куда возвращаться.

        Если издание текущего выпуска в библиотеке не нашлось (файл принесли с
        другой машины или издание ещё не сохраняли), редактор открывается на его
        облике с тем же идентификатором — иначе правка шапки не привязалась бы
        к выпуску и пропала.
        """
        self.publication_return_route = return_route
        library = self.publications
        known = (
            storage.publication(self.project.publication_id)
            if self.project.publication_id
            else None
        )
        if known is not None:
            self.editing_publication = known
            self.publication_dirty = False
        elif return_route == "start" and library:
            self.editing_publication = library[0]
            self.publication_dirty = False
        else:
            draft = self.project.as_publication()
            if self.project.publication_id:
                draft.id = self.project.publication_id
            self.editing_publication = draft
            self.publication_dirty = True  # черновик ещё не в библиотеке
        self.navigate("publications")

    def start_editing_publication(self) -> Publication:
        library = self.publications
        self.editing_publication = library[0] if library else Publication()
        return self.editing_publication

    def edit_publication(self, publication_id: str) -> None:
        found = storage.publication(publication_id)
        if found is not None:
            self.editing_publication = found
            self.publication_dirty = False
            self.rebuild()

    def new_publication(self, from_wizard: bool = False) -> None:
        self.editing_publication = Publication()
        self.publication_dirty = True
        self.start_filter = ""
        self.publication_tab = "logo"
        if from_wizard:
            self.publication_return_route = "issue"
        self.navigate("publications")

    def save_publication(self) -> None:
        """Сохраняет издание и обновляет им текущий выпуск, если он этого издания."""
        item = self.editing_publication
        if item is None:
            return
        if not item.name.strip():
            item.name = item.brand.display_name
        storage.save_publication(item)
        self.publication_dirty = False
        if self.project.publication_id in ("", item.id):
            self.project.inherit(item)
            self.touch(immediate=True)
        if self.publication_return_route == "issue":
            self.wizard.publication_id = item.id
        self.rebuild()

    def duplicate_publication(self) -> None:
        item = self.editing_publication
        if item is None:
            return
        copy = from_dict(Publication, to_dict(item))
        copy.id = Publication().id
        copy.name = f"{item.display_name} — копия"
        storage.save_publication(copy)
        self.editing_publication = copy
        self.publication_dirty = False
        self.rebuild()

    def delete_publication(self) -> None:
        item = self.editing_publication
        if item is None:
            return
        storage.delete_publication(item.id)
        library = self.publications
        self.editing_publication = library[0] if library else Publication()
        self.publication_dirty = not library
        self.rebuild()

    def leave_publications(self) -> None:
        self.navigate(self.publication_return_route)

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
        if self.preview is not None:
            self.preview.shutdown()
        engine().close()
