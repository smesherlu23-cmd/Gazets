"""Фоновая пересборка превью полосы.

Рендер идёт в отдельном потоке с задержкой (debounce ≈ 400 мс, как описано в
README): пока пользователь набирает текст, запросы схлопываются в один. Каждый
результат — PNG-файл и метрики блоков; интерфейс кладёт поверх картинки
невидимые зоны выделения и перетаскивания.
"""

from __future__ import annotations

import base64
import itertools
import pathlib
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Callable, Optional

from ..models import Project
from ..render.engine import BlockMetrics, engine
from ..render.html import RenderOptions, page_document


@dataclass
class PreviewResult:
    image: Optional[pathlib.Path]
    metrics: list[BlockMetrics]
    page_index: int
    error: Optional[str] = None
    elapsed_ms: int = 0
    image_b64: Optional[str] = None


class PreviewController:
    """Очередь из одного запроса: новый вытесняет ещё не начатый старый."""

    def __init__(self, on_ready: Callable[[PreviewResult], None], debounce: float = 0.4) -> None:
        self._on_ready = on_ready
        self._debounce = debounce
        self._pending: Optional[tuple] = None
        self._event = threading.Event()
        self._stop = False
        self._counter = itertools.count()
        self._dir = pathlib.Path(tempfile.mkdtemp(prefix="pechatnya-preview-"))
        self._thread = threading.Thread(target=self._loop, name="pechatnya-preview", daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------ запрос
    def request(
        self,
        project: Project,
        page_index: int,
        options: RenderOptions,
        project_dir: Optional[pathlib.Path] = None,
        immediate: bool = False,
    ) -> None:
        """Просит пересобрать полосу. Документ собирается сразу — модель может
        измениться, пока поток ждёт, а HTML должен отражать момент запроса."""
        document = page_document(project, page_index, options, project_dir)
        self._pending = (document, page_index, 0.0 if immediate else self._debounce, time.monotonic())
        self._event.set()

    def shutdown(self) -> None:
        self._stop = True
        self._event.set()

    # -------------------------------------------------------------------- поток
    def _loop(self) -> None:
        while not self._stop:
            self._event.wait()
            if self._stop:
                return
            self._event.clear()
            job = self._pending
            if job is None:
                continue
            document, page_index, delay, _ = job
            if delay:
                time.sleep(delay)
                if self._event.is_set():
                    continue  # пришёл более свежий запрос — этот отбрасываем
            self._pending = None
            started = time.monotonic()
            try:
                target = self._dir / f"page-{next(self._counter)}.png"
                path, metrics = engine().render_and_measure(document, target)
                if not metrics:
                    metrics = []
                result = PreviewResult(
                    image=path,
                    metrics=metrics,
                    page_index=page_index,
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                    image_b64=base64.b64encode(path.read_bytes()).decode("ascii"),
                )
                self._cleanup(keep=target)
            except Exception as error:  # движок недоступен или упал
                result = PreviewResult(
                    image=None,
                    metrics=[],
                    page_index=page_index,
                    error=f"{error}".strip() or traceback.format_exc(limit=1),
                )
            try:
                self._on_ready(result)
            except Exception:  # интерфейс уже закрыт
                pass

    def _cleanup(self, keep: pathlib.Path) -> None:
        for path in sorted(self._dir.glob("page-*.png"))[:-2]:
            if path != keep:
                path.unlink(missing_ok=True)
