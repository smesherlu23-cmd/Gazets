"""Экспорт выпуска в PNG и PDF (экран 08).

Имена файлов — ``<издание>-<номер>-p<N>.png``, как описано в README. Рендер
локальный: тот же движок, что и для превью, поэтому экспорт гарантированно
совпадает с тем, что пользователь видел на экране, включая слой состаривания.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..models import Project, SHEET_HEIGHT, SHEET_WIDTH
from .engine import ChromiumEngine, RenderError, engine
from .html import RenderOptions, issue_document, page_document

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "j", "i": "i", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h",
    "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "ѣ": "e",
    "э": "e", "ю": "yu", "я": "ya",
}

DPI_CHOICES = [96, 150, 300, 600]


def slugify(text: str) -> str:
    out = []
    for char in (text or "").lower():
        out.append(TRANSLIT.get(char, char))
    slug = re.sub(r"[^a-z0-9]+", "-", "".join(out)).strip("-")
    return slug or "vypusk"


def px_for_dpi(dpi: int, sheet: tuple[int, int] | None = None) -> tuple[int, int]:
    scale = dpi / 96
    width, height = sheet or (SHEET_WIDTH, SHEET_HEIGHT)
    return int(round(width * scale)), int(round(height * scale))


def dpi_label(dpi: int, sheet: tuple[int, int] | None = None) -> str:
    width, height = px_for_dpi(dpi, sheet)
    return f"{dpi} dpi · {width} × {height} px"


@dataclass
class ExportSettings:
    """Параметры диалога экспорта."""

    fmt: str = "png"  # png | pdf
    scope: str = "all"  # all | current | range
    range_from: int = 1
    range_to: int = 1
    current_page: int = 0
    dpi: int = 150
    with_paper: bool = True
    crop_marks: bool = False
    stitch: bool = False
    directory: pathlib.Path = field(default_factory=pathlib.Path.cwd)

    def pages(self, total: int) -> list[int]:
        if self.scope == "current":
            return [max(0, min(self.current_page, total - 1))]
        if self.scope == "range":
            start = max(1, min(self.range_from, total))
            end = max(start, min(self.range_to, total))
            return list(range(start - 1, end))
        return list(range(total))


@dataclass
class ExportResult:
    files: list[pathlib.Path] = field(default_factory=list)
    total_bytes: int = 0

    @property
    def size_label(self) -> str:
        if self.total_bytes < 1024 * 1024:
            return f"{self.total_bytes / 1024:.0f} КБ"
        return f"{self.total_bytes / 1024 / 1024:.1f} МБ".replace(".", ",")


def file_stem(project: Project, page_index: int) -> str:
    return f"{slugify(project.issue.title)}-{slugify(project.issue.number)}-p{page_index + 1}"


def planned_names(project: Project, settings: ExportSettings) -> list[str]:
    pages = settings.pages(len(project.pages))
    if settings.fmt == "pdf":
        return [f"{slugify(project.issue.title)}-{slugify(project.issue.number)}.pdf"]
    if settings.stitch:
        return [f"{slugify(project.issue.title)}-{slugify(project.issue.number)}-all.png"]
    return [f"{file_stem(project, index)}.png" for index in pages]


def estimate_size(project: Project, settings: ExportSettings) -> str:
    """Грубая оценка объёма для сводки в диалоге (до самого рендера)."""
    pages = len(settings.pages(len(project.pages)))
    width, height = px_for_dpi(settings.dpi, project.sheet_px())
    per_page = width * height * 0.35 / 1024 / 1024  # PNG газетной полосы жмётся примерно так
    if settings.fmt == "pdf":
        per_page *= 0.45
    total = per_page * max(1, pages)
    return f"≈ {total:.1f} МБ".replace(".", ",")


def export(
    project: Project,
    settings: ExportSettings,
    project_dir: Optional[pathlib.Path] = None,
    progress: Optional[Callable[[int, int, str], None]] = None,
    render_engine: Optional[ChromiumEngine] = None,
) -> ExportResult:
    """Выгружает выпуск. ``progress(done, total, name)`` зовётся после каждой полосы."""
    render_engine = render_engine or engine()
    settings.directory.mkdir(parents=True, exist_ok=True)
    pages = settings.pages(len(project.pages))
    options = RenderOptions(
        show_guides=False,
        show_paper=settings.with_paper,
        show_block_borders=False,
        for_export=True,
        crop_marks=settings.crop_marks,
    )
    result = ExportResult()

    if settings.fmt == "pdf":
        target = settings.directory / planned_names(project, settings)[0]
        document = issue_document(project, options, project_dir, pages)
        render_engine.render_pdf(document, target, project.sheet_mm())
        result.files.append(target)
        result.total_bytes = target.stat().st_size
        if progress:
            progress(1, 1, target.name)
        return result

    scale = settings.dpi / 96
    rendered: list[pathlib.Path] = []
    for order, index in enumerate(pages, start=1):
        target = settings.directory / f"{file_stem(project, index)}.png"
        document = page_document(project, index, options, project_dir)
        render_engine.render_png(document, target, scale, size=project.sheet_px())
        rendered.append(target)
        if progress:
            progress(order, len(pages), target.name)

    if settings.stitch and len(rendered) > 1:
        target = settings.directory / planned_names(project, settings)[0]
        stitch_images(rendered, target)
        for path in rendered:
            path.unlink(missing_ok=True)
        rendered = [target]

    result.files = rendered
    result.total_bytes = sum(path.stat().st_size for path in rendered if path.exists())
    return result


def stitch_images(paths: list[pathlib.Path], target: pathlib.Path) -> pathlib.Path:
    """Склейка полос в одну картинку — «для чата» из диалога экспорта."""
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError as error:  # pragma: no cover - Pillow есть в зависимостях
        raise RenderError("Для склейки нужен Pillow") from error

    images = [Image.open(path).convert("RGB") for path in paths]
    gap = 24
    width = max(image.width for image in images)
    height = sum(image.height for image in images) + gap * (len(images) - 1)
    canvas = Image.new("RGB", (width, height), "#101112")
    offset = 0
    for image in images:
        canvas.paste(image, ((width - image.width) // 2, offset))
        offset += image.height + gap
    canvas.save(target)
    for image in images:
        image.close()
    return target
