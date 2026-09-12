"""Движок рендера полосы: headless-Chromium поверх HTML из ``render.html``.

Один класс делает три вещи, которые нужны приложению:

* ``render_png`` — картинка полосы для превью и для экспорта (dpi задаётся
  масштабом устройства, 96 dpi = 1.0);
* ``measure`` — замер вместимости блоков и их координат на листе; координаты
  нужны интерфейсу, чтобы положить поверх картинки невидимые зоны выделения и
  перетаскивания;
* ``render_pdf`` — печатный PDF всего выпуска.

Движок ищется в таком порядке: Playwright (если установлен), затем системный
Chrome/Chromium/Edge — на Windows Edge есть всегда, поэтому приложение остаётся
работоспособным даже без ``playwright install``. В режиме CLI доступны рендер и
печать, но не замер: без метрик интерфейс не показывает проценты заполнения.

Весь браузер живёт в одном служебном потоке: синхронный API Playwright нельзя
звать из потока, где крутится asyncio-цикл Flet, поэтому вызовы из интерфейса,
превью и экспорта ставятся в очередь этого потока и выполняются по одному.
"""

from __future__ import annotations

import concurrent.futures
import os
import pathlib
import platform
import queue
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

from ..models import SHEET_HEIGHT, SHEET_WIDTH

MEASURE_JS = """
() => {
  // Многоколоночный текст при переполнении уезжает в лишние колонки по горизонтали,
  // поэтому высоту содержимого меряем на клоне в одну колонку нужной ширины:
  // получается непрерывный процент заполнения, а не ступеньки по числу колонок.
  const measureFill = (node) => {
    const styles = getComputedStyle(node);
    const columns = Math.max(1, parseInt(styles.columnCount) || 1);
    const gap = parseFloat(styles.columnGap) || 0;
    const available = node.clientHeight;
    if (!available) return { percent: 0, chars: 0 };
    const columnWidth = (node.clientWidth - gap * (columns - 1)) / columns;
    const probe = node.cloneNode(true);
    probe.style.cssText = getComputedStyle(node).cssText;
    probe.style.position = 'absolute';
    probe.style.visibility = 'hidden';
    probe.style.left = '-10000px';
    probe.style.top = '0';
    probe.style.columnCount = '1';
    probe.style.width = columnWidth + 'px';
    probe.style.height = 'auto';
    probe.style.minHeight = '0';
    probe.style.maxHeight = 'none';
    probe.style.flex = 'none';
    probe.style.overflow = 'visible';
    document.body.appendChild(probe);
    const contentHeight = probe.scrollHeight;
    const chars = (probe.textContent || '').length;
    probe.remove();
    return { percent: (contentHeight / (available * columns)) * 100, chars: chars };
  };

  const sheet = document.getElementById('sheet');
  const base = sheet.getBoundingClientRect();
  const blocks = [];
  document.querySelectorAll('[data-block]').forEach(node => {
    const rect = node.getBoundingClientRect();
    const fit = node.querySelector('[data-fit]');
    let percent = 0, overflow = 0;
    if (fit) {
      const measured = measureFill(fit);
      percent = measured.percent;
      if (percent > 100) {
        overflow = Math.round(measured.chars * (1 - 100 / percent));
      }
    }
    blocks.push({
      id: node.getAttribute('data-block'),
      x: rect.left - base.left, y: rect.top - base.top,
      width: rect.width, height: rect.height,
      percent: percent, overflow: overflow
    });
  });
  return blocks;
}
"""

WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
POSIX_CANDIDATES = [
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "microsoft-edge",
]


class RenderError(RuntimeError):
    """Движок рендера недоступен или упал."""


@dataclass
class BlockMetrics:
    id: str
    x: float
    y: float
    width: float
    height: float
    percent: float
    overflow: int


def find_browser() -> Optional[str]:
    """Путь к исполняемому Chromium/Chrome/Edge, если он есть в системе."""
    override = os.environ.get("PECHATNYA_BROWSER")
    if override and pathlib.Path(override).exists():
        return override
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path:
        root = pathlib.Path(browsers_path)
        for pattern in ("chromium-*/chrome-linux/chrome", "chromium-*/chrome-win/chrome.exe",
                        "chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium"):
            found = sorted(root.glob(pattern))
            if found:
                return str(found[-1])
    if platform.system() == "Windows":
        for path in WINDOWS_CANDIDATES:
            if pathlib.Path(path).exists():
                return path
        return None
    for name in POSIX_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    return None


class ChromiumEngine:
    """Обёртка над браузером: держит страницу открытой между вызовами."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: "queue.Queue[tuple]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._playwright = None
        self._browser = None
        self._page = None
        self._cli_path: Optional[str] = None
        self._mode = "none"
        self._error: Optional[str] = None

    # ------------------------------------------------------ служебный поток
    def _ensure_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._serve, name="pechatnya-engine", daemon=True)
        self._worker.start()

    def _serve(self) -> None:
        while True:
            job, future = self._jobs.get()
            if job is None:
                future.set_result(None)
                return
            if future.set_running_or_notify_cancel():
                try:
                    future.set_result(job())
                except BaseException as error:  # noqa: BLE001 — пробрасываем вызывающему
                    future.set_exception(error)

    def _submit(self, job: Callable[[], T]) -> T:
        """Выполняет работу в потоке движка и возвращает результат вызывающему."""
        if threading.current_thread() is self._worker:
            return job()
        self._ensure_worker()
        future: "concurrent.futures.Future[T]" = concurrent.futures.Future()
        self._jobs.put((job, future))
        return future.result()

    # ------------------------------------------------------------------ запуск
    def start(self) -> str:
        """Публичный запуск: поднимает браузер в служебном потоке."""
        if self._mode != "none":
            return self._mode
        return self._submit(self._start_impl)

    def _start_impl(self) -> str:
        """Поднимает движок. Возвращает режим: ``playwright``, ``cli`` или ``none``."""
        if self._mode != "none":
            return self._mode
        executable = find_browser()
        try:
            from playwright.sync_api import sync_playwright  # noqa: PLC0415

            self._playwright = sync_playwright().start()
            launch: dict[str, object] = {"args": ["--force-color-profile=srgb",
                                                  "--font-render-hinting=none",
                                                  "--disable-lcd-text"]}
            if executable:
                launch["executable_path"] = executable
            try:
                self._browser = self._playwright.chromium.launch(**launch)
            except Exception:
                launch.pop("executable_path", None)
                self._browser = self._playwright.chromium.launch(**launch)
            self._page = self._browser.new_page(
                viewport={"width": SHEET_WIDTH, "height": SHEET_HEIGHT}
            )
            self._mode = "playwright"
            return self._mode
        except Exception as error:  # Playwright нет или браузер не встал
            self._error = str(error)
            self._shutdown_playwright()
        if executable:
            self._cli_path = executable
            self._mode = "cli"
        return self._mode

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def can_measure(self) -> bool:
        return self._mode == "playwright"

    def _shutdown_playwright(self) -> None:
        for closer in (self._page, self._browser, self._playwright):
            try:
                if closer is None:
                    continue
                closer.close() if hasattr(closer, "close") else closer.stop()
            except Exception:
                pass
        self._page = self._browser = self._playwright = None

    def close(self) -> None:
        if self._worker is None or not self._worker.is_alive():
            return

        def stop() -> None:
            self._shutdown_playwright()
            self._mode = "none"

        self._submit(stop)
        future: "concurrent.futures.Future[None]" = concurrent.futures.Future()
        self._jobs.put((None, future))
        future.result(timeout=5)
        self._worker = None

    # ----------------------------------------------------------------- рендеринг
    def render_png(self, document: str, path: pathlib.Path, scale: float = 1.0) -> pathlib.Path:
        """Снимок одной полосы. ``scale`` = dpi / 96."""
        return self._submit(lambda: self._render_png_impl(document, path, scale))

    def _render_png_impl(self, document: str, path: pathlib.Path, scale: float) -> pathlib.Path:
        mode = self._start_impl()
        if mode == "playwright":
            return self._png_playwright(document, path, scale)
        if mode == "cli":
            return self._png_cli(document, path, scale)
        raise RenderError(
            "Не найден движок рендера. Установите Google Chrome, Microsoft Edge или "
            "выполните «playwright install chromium»."
        )

    def _png_playwright(self, document: str, path: pathlib.Path, scale: float) -> pathlib.Path:
        assert self._page is not None
        if abs(scale - 1.0) > 1e-6:
            # deviceScaleFactor задаётся только при создании страницы
            page = self._browser.new_page(  # type: ignore[union-attr]
                viewport={"width": SHEET_WIDTH, "height": SHEET_HEIGHT},
                device_scale_factor=scale,
            )
            try:
                page.set_content(document, wait_until="load")
                page.locator("#sheet").screenshot(path=str(path))
            finally:
                page.close()
            return path
        self._page.set_content(document, wait_until="load")
        self._page.locator("#sheet").screenshot(path=str(path))
        return path

    def _cli_run(self, args: list[str], document: str, timeout: int = 120) -> None:
        assert self._cli_path
        with tempfile.TemporaryDirectory() as tmp:
            source = pathlib.Path(tmp) / "page.html"
            source.write_text(document, encoding="utf-8")
            command = [
                self._cli_path,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--hide-scrollbars",
                f"--user-data-dir={tmp}/profile",
                "--allow-file-access-from-files",
                "--virtual-time-budget=4000",
                *args,
                source.as_uri(),
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            if result.returncode != 0:
                raise RenderError(result.stderr.strip()[:400] or "браузер вернул ошибку")

    def _png_cli(self, document: str, path: pathlib.Path, scale: float) -> pathlib.Path:
        width, height = int(SHEET_WIDTH * scale), int(SHEET_HEIGHT * scale)
        self._cli_run(
            [f"--screenshot={path}", f"--window-size={width},{height}",
             f"--force-device-scale-factor={scale}"],
            document,
        )
        if not path.exists():
            raise RenderError("браузер не создал файл снимка")
        return path

    def render_pdf(self, document: str, path: pathlib.Path, paper: str = "A4") -> pathlib.Path:
        """PDF выпуска. ``paper`` — физический формат листа (A4 или A3)."""
        return self._submit(lambda: self._render_pdf_impl(document, path, paper))

    def _render_pdf_impl(self, document: str, path: pathlib.Path, paper: str) -> pathlib.Path:
        mode = self._start_impl()
        width_in = SHEET_WIDTH / 96
        height_in = SHEET_HEIGHT / 96
        scale = 1.0
        if paper.upper() == "A3":
            scale = 1.414
            width_in *= scale
            height_in *= scale
        if mode == "playwright":
            page = self._browser.new_page()  # type: ignore[union-attr]
            try:
                page.set_content(document, wait_until="load")
                page.pdf(
                    path=str(path),
                    width=f"{width_in}in",
                    height=f"{height_in}in",
                    scale=scale,
                    print_background=True,
                    margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                )
            finally:
                page.close()
            return path
        if mode == "cli":
            self._cli_run([f"--print-to-pdf={path}", "--no-pdf-header-footer"], document)
            if not path.exists():
                raise RenderError("браузер не создал PDF")
            return path
        raise RenderError("Не найден движок рендера для печати PDF.")

    # -------------------------------------------------------------------- замер
    def measure(self, document: str) -> list[BlockMetrics]:
        """Координаты блоков на листе и процент заполнения каждого."""
        return self._submit(lambda: self._measure_impl(document))

    def _measure_impl(self, document: str) -> list[BlockMetrics]:
        if self._start_impl() != "playwright":
            return []
        assert self._page is not None
        self._page.set_content(document, wait_until="load")
        raw = self._page.evaluate(MEASURE_JS)
        return [BlockMetrics(**item) for item in raw]

    def render_and_measure(
        self, document: str, path: pathlib.Path, scale: float = 1.0
    ) -> tuple[pathlib.Path, list[BlockMetrics]]:
        """Один проход: и картинка превью, и метрики — чтобы не грузить страницу дважды."""
        return self._submit(lambda: self._render_and_measure_impl(document, path, scale))

    def _render_and_measure_impl(
        self, document: str, path: pathlib.Path, scale: float
    ) -> tuple[pathlib.Path, list[BlockMetrics]]:
        mode = self._start_impl()
        if mode != "playwright":
            return self._render_png_impl(document, path, scale), []
        assert self._page is not None
        self._page.set_viewport_size({"width": SHEET_WIDTH, "height": SHEET_HEIGHT})
        self._page.set_content(document, wait_until="load")
        metrics = [BlockMetrics(**item) for item in self._page.evaluate(MEASURE_JS)]
        self._page.locator("#sheet").screenshot(path=str(path))
        return path, metrics


_ENGINE: Optional[ChromiumEngine] = None


def engine() -> ChromiumEngine:
    """Единый экземпляр движка на приложение."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ChromiumEngine()
    return _ENGINE


def engine_report() -> str:
    """Строка для статус-бара: какой движок используется."""
    current = engine()
    mode = current.start()
    return {
        "playwright": "Рендер: Chromium (Playwright)",
        "cli": f"Рендер: {pathlib.Path(current._cli_path or '').name}",
        "none": "Рендер недоступенъ — установите Chrome/Edge",
    }[mode]
