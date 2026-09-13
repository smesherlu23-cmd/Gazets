"""Перенос остатка статьи на другую полосу («продолжение на стр. N»).

Точку разрыва нельзя посчитать формулой: сколько знаков влезет в блок, зависит
от переносов, врезок и балансировки колонок. Поэтому она подбирается замером —
двоичным поиском по длине первой части, начиная с оценки, которую даёт первый
же замер переполнения. Обычно хватает трёх-четырёх проб.
"""

from __future__ import annotations

import pathlib
import re
from typing import Callable, Optional

from ..models import Project
from .engine import ChromiumEngine, engine
from .html import RenderOptions, page_document

MAX_PROBES = 6
_WORD_BREAK = re.compile(r"[\s]")


def snap_to_word(text: str, point: int) -> int:
    """Двигает точку разрыва к ближайшему пробелу слева — не рвём слово."""
    point = max(0, min(len(text), point))
    if point >= len(text):
        return len(text)
    window = text.rfind(" ", max(0, point - 120), point)
    newline = text.rfind("\n", max(0, point - 120), point)
    best = max(window, newline)
    return best if best > 0 else point


def measure_block(
    project: Project,
    page_index: int,
    block_id: str,
    project_dir: Optional[pathlib.Path],
    render_engine: ChromiumEngine,
) -> float:
    """Процент заполнения одного блока на полосе."""
    document = page_document(project, page_index, RenderOptions(show_paper=False), project_dir)
    metrics = render_engine.measure(document)
    for item in metrics:
        if item.id == block_id:
            return item.percent
    return 0.0


def fit_split_point(
    project: Project,
    article_id: str,
    project_dir: Optional[pathlib.Path] = None,
    render_engine: Optional[ChromiumEngine] = None,
    probes: int = MAX_PROBES,
    progress: Optional[Callable[[str], None]] = None,
) -> Optional[int]:
    """Подбирает, сколько знаков оставить на исходной полосе.

    Возвращает точку разрыва, ``None`` — если статья и так помещается, и ``0`` —
    если в блок не влезает даже начало (блок слишком мал).
    """
    article = project.article(article_id)
    block = project.block_of(article_id, part=0)
    if article is None or block is None or not article.body.strip():
        return None
    page_index = project.page_of_block(block.id)
    if page_index is None:
        return None

    render_engine = render_engine or engine()
    if not render_engine.can_measure:
        return None

    original_split = article.split_at
    article.split_at = None
    percent = measure_block(project, page_index, block.id, project_dir, render_engine)
    if percent <= 100:
        article.split_at = original_split
        return None

    body = article.body
    low, high = 0, len(body)
    probe = snap_to_word(body, int(len(body) * 100 / percent))
    best = 0
    for attempt in range(1, probes + 1):
        article.split_at = probe
        if progress:
            progress(f"подбираем перенос: проба {attempt} из {probes}")
        percent = measure_block(project, page_index, block.id, project_dir, render_engine)
        if percent <= 100:
            best = max(best, probe)
            low = probe
        else:
            high = probe
        if high - low <= 80:
            break
        probe = snap_to_word(body, (low + high) // 2)

    article.split_at = original_split
    return best
