"""Проверка выпуска перед выгрузкой.

Ошибки вёрстки видно не сразу: переполненный блок на четвёртой полосе,
потерянный снимок, статья, которую забыли поставить. Здесь они собираются
в один список — так же, как в типографии проверяют оригинал-макет перед печатью.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Optional

from .models import Project
from .presets import MODULE_TITLES
from .render.engine import ChromiumEngine
from .render.html import RenderOptions, page_document

ERROR = "error"
WARNING = "warning"
NOTE = "note"


@dataclass
class Finding:
    level: str
    text: str
    page: Optional[int] = None  # номер полосы, 1-based

    @property
    def label(self) -> str:
        return f"Полоса {self.page}: {self.text}" if self.page else self.text


def _image_missing(path: str, project_dir: Optional[pathlib.Path]) -> bool:
    if not path:
        return False
    full = pathlib.Path(path)
    if not full.is_absolute() and project_dir is not None:
        full = project_dir / full
    return not full.exists()


def inspect(
    project: Project,
    project_dir: Optional[pathlib.Path] = None,
    render_engine: Optional[ChromiumEngine] = None,
) -> list[Finding]:
    """Собирает замечания. С движком добавляется проверка переполнения блоков."""
    findings: list[Finding] = []

    issue = project.issue
    if not issue.title.strip():
        findings.append(Finding(ERROR, "не заполнено название издания"))
    if not issue.number.strip():
        findings.append(Finding(WARNING, "не указан номер выпуска"))
    if not issue.date.strip():
        findings.append(Finding(WARNING, "не указана дата выпуска"))

    unplaced = project.unplaced_articles()
    for article in unplaced:
        findings.append(
            Finding(WARNING, f"статья «{article.title}» не размещена на полосе")
        )

    for article in project.articles:
        if article.split_is_stale:
            page = project.page_of_article(article.id, part=0)
            findings.append(
                Finding(
                    WARNING,
                    f"текст статьи «{article.title}» правили после переноса — "
                    "точку разрыва надо пересчитать",
                    page=page + 1 if page is not None else None,
                )
            )

    for index, page in enumerate(project.pages, start=1):
        empty = [block for block in page.blocks() if block.is_empty]
        if empty:
            findings.append(
                Finding(NOTE, f"пустых блоков: {len(empty)}", page=index)
            )
        for block in page.blocks():
            article = project.article(block.article_id)
            if article is not None:
                if not article.part_text(block.article_part).strip():
                    findings.append(
                        Finding(WARNING, f"в блоке «{block.label}» нет текста", page=index)
                    )
                image = article.image
                if image is not None and _image_missing(image.path, project_dir):
                    findings.append(
                        Finding(ERROR, f"снимок к статье «{article.title}» не найден", page=index)
                    )
                elif image is not None and image.path and not image.caption.strip():
                    findings.append(
                        Finding(NOTE, f"снимок к статье «{article.title}» без подписи", page=index)
                    )
            for module in block.modules:
                filled = module.text.strip() or any(
                    cell.strip() for line in module.rows for cell in line
                )
                if module.kind == "photo":
                    filled = module.image is not None and bool(module.image.path)
                if not filled:
                    name = MODULE_TITLES.get(module.kind, module.kind)
                    findings.append(
                        Finding(WARNING, f"модуль «{name}» пустой", page=index)
                    )
                if module.image is not None and _image_missing(module.image.path, project_dir):
                    findings.append(
                        Finding(ERROR, "снимок модуля не найден", page=index)
                    )

    if render_engine is not None and render_engine.can_measure:
        findings.extend(_overflow_findings(project, project_dir, render_engine))
    return findings


def _overflow_findings(
    project: Project, project_dir: Optional[pathlib.Path], render_engine: ChromiumEngine
) -> list[Finding]:
    """Замеряет каждую полосу и жалуется на блоки, куда текст не влез."""
    findings: list[Finding] = []
    options = RenderOptions(show_paper=False, for_export=True)
    for index, page in enumerate(project.pages, start=1):
        document = page_document(project, index - 1, options, project_dir)
        metrics = {
            item.id: item
            for item in render_engine.measure(document)
            if item.kind == "block"
        }
        for block in page.blocks():
            item = metrics.get(block.id)
            if item is not None and item.percent > 100:
                findings.append(
                    Finding(
                        ERROR,
                        f"в блок «{block.label}» не помещается {item.overflow} зн.",
                        page=index,
                    )
                )
    return findings


def summary(findings: list[Finding]) -> str:
    """Короткая строка для кнопки и статус-бара."""
    if not findings:
        return "замечаний нет"
    errors = sum(1 for item in findings if item.level == ERROR)
    warnings = sum(1 for item in findings if item.level == WARNING)
    notes = sum(1 for item in findings if item.level == NOTE)
    parts = []
    if errors:
        parts.append(f"ошибок: {errors}")
    if warnings:
        parts.append(f"предупреждений: {warnings}")
    if notes:
        parts.append(f"заметок: {notes}")
    return " · ".join(parts)
