"""Модель данных выпуска: бренд, издание, полосы, блоки, статьи, оформление.

Вся структура соответствует разделу «State Management» из README-хендофа:
``brand`` → ``issue`` → ``pages[] → rows[] → blocks[]`` плюс сквозной список
``articles[]``, настройки типографики, бумаги и стиля. Геометрия полосы описана
не абсолютными координатами, а весами строк и блоков: так «перетаскивание
границ» из ТЗ сводится к изменению одного числа и не ломает вёрстку при смене
формата листа.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from .serde import from_dict, to_dict

PROJECT_FORMAT_VERSION = 1

# Лист в дизайн-пикселях (96 dpi). Все метрики полосы из README заданы в них.
SHEET_WIDTH = 794
SHEET_HEIGHT = 1123
MARGIN_V = 34
MARGIN_H = 38

PT_TO_PX = 96 / 72


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------- бренд


@dataclass
class Brand:
    """Логотип и постоянные элементы шапки. Заполняется пользователем."""

    id: str = field(default_factory=lambda: new_id("brand"))
    name_latin: str = ""
    name_cyrillic: str = ""
    use_cyrillic: bool = True
    logo_font: str = "Old Standard TT"
    logo_fallback_font: str = "Old Standard TT"
    logo_size_pt: float = 43.5
    tracking_permille: int = 50
    superline_enabled: bool = False
    superline: str = ""
    motto_enabled: bool = True
    motto: str = ""
    rules_style: str = "bold_thin"  # single | bold_thin | ornament
    rubricator: list[str] = field(default_factory=list)
    ink: str = "#15120e"
    logo_font_preset: str = "antiqua"  # antiqua | gothic | modern | narrow | framed
    imprint: str = ""

    @property
    def display_name(self) -> str:
        if self.use_cyrillic and self.name_cyrillic:
            return self.name_cyrillic
        return self.name_latin or self.name_cyrillic


# ------------------------------------------------------------------------- выпуск


@dataclass
class Issue:
    """Данные конкретного номера. Всё, что печатается в служебных строках шапки."""

    title: str = ""
    motto: str = ""
    number: str = ""
    date: str = ""
    price: str = ""
    city: str = ""
    pages_count: int = 2
    masthead_frame: str = "double_rule"  # none | double_rule | ornament
    year_line: str = ""
    masthead_left: str = ""
    masthead_right: str = ""


# --------------------------------------------------------------------- типографика


@dataclass
class Typography:
    """Гарнитуры и кегли. Кегли — в пунктах, на лист переводятся как pt × 96/72."""

    heading_font: str = "Old Standard TT"
    body_font: str = "PT Serif"
    caption_font: str = "PT Sans Narrow"
    masthead_pt: float = 43.5
    lead_headline_pt: float = 28.5
    article_headline_pt: float = 11.3
    body_pt: float = 8.6
    leading: float = 1.52

    def px(self, name: str) -> float:
        return round(getattr(self, name) * PT_TO_PX, 2)


@dataclass
class Paper:
    """Состаривание бумаги (панель «Бумага», экран 07)."""

    enabled: bool = True
    intensity: int = 55
    yellowing: bool = True
    stains: bool = True
    unevenness: bool = True
    folds: bool = False
    grain: bool = False


# ---------------------------------------------------------------------- содержимое


@dataclass
class ImageRef:
    """Иллюстрация: путь относительно папки images проекта + обработка."""

    path: str = ""
    caption: str = ""
    caption_prefix: str = "СНИМОК."
    filter: str = "halftone"  # none | halftone | sepia | bw
    height_px: int = 96
    scale: float = 1.0
    focus_x: float = 0.5
    focus_y: float = 0.5

    @property
    def is_empty(self) -> bool:
        return not self.path


@dataclass
class Article:
    """Материал выпуска. Тело — плейн-текст с минимальной разметкой.

    Разметка тела: ``**полужирный**``, ``*курсив*``, строка ``## Подзаголовок``,
    строка ``> цитата`` — врезка, пустая строка — новый абзац.
    """

    id: str = field(default_factory=lambda: new_id("art"))
    rubric: str = ""
    title: str = "Без заголовка"
    subtitle: str = ""
    author: str = ""
    place_time: str = ""
    body: str = ""
    drop_cap: bool = True
    small_caps_opening: bool = True
    image: Optional[ImageRef] = None
    block_id: Optional[str] = None
    continued_on: Optional[int] = None
    split_at: Optional[int] = None  # сколько знаков уходит в первую часть

    def part_text(self, part: int) -> str:
        """Текст части: 0 — начало до разрыва, 1 — остаток для «продолжения»."""
        if self.split_at is None:
            return self.body if part == 0 else ""
        point = max(0, min(len(self.body), self.split_at))
        return self.body[:point].rstrip() if part == 0 else self.body[point:].lstrip()

    @property
    def char_count(self) -> int:
        return len(self.body)

    @property
    def word_count(self) -> int:
        return len(self.body.split())


@dataclass
class ModuleData:
    """Служебный блок: объявление, погода, курсы, цитата, некролог."""

    kind: str = "ad"  # ad | weather | rates | quote | obituary | photo | free
    title: str = "ОБЪЯВЛЕНИЕ"
    text: str = ""
    rows: list[list[str]] = field(default_factory=list)  # пары «подпись — значение»
    attribution: str = ""
    framed: bool = True
    image: Optional[ImageRef] = None


@dataclass
class Block:
    """Прямоугольник полосы. Ширина внутри строки задаётся весом ``weight``."""

    id: str = field(default_factory=lambda: new_id("blk"))
    kind: str = "article"  # article | module | photo | empty
    label: str = "Блок"
    weight: float = 1.0
    fixed_width: Optional[float] = None  # px, для узких боковых колонок
    columns: int = 3
    column_rules: bool = True
    hyphens: bool = False
    align: str = "justify"  # left | justify | center
    drop_cap: bool = True
    headline_scale: float = 1.0
    border_left: bool = False
    border_top: float = 0.0
    article_id: Optional[str] = None
    article_part: int = 0  # 1 — блок с «продолжением» статьи
    modules: list[ModuleData] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return self.article_id is None and not self.modules


@dataclass
class Row:
    """Горизонтальная зона полосы. Высота — доля от свободного места."""

    id: str = field(default_factory=lambda: new_id("row"))
    weight: float = 1.0
    fixed_height: Optional[float] = None
    gap: float = 16.0
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Page:
    """Полоса выпуска."""

    id: str = field(default_factory=lambda: new_id("pg"))
    kind: str = "front"  # front | inner
    template_id: str = "front-main-side"
    show_masthead: bool = True
    rows: list[Row] = field(default_factory=list)

    def blocks(self) -> Iterator[Block]:
        for row in self.rows:
            yield from row.blocks

    def find_block(self, block_id: str) -> Optional[Block]:
        return next((block for block in self.blocks() if block.id == block_id), None)


# -------------------------------------------------------------------------- проект


@dataclass
class Style:
    """Оформление полосы: бумага, краска, линейки, декор (пресеты экрана 03)."""

    preset_id: str = "classic"
    paper_color: str = "#efe7d4"
    ink_color: str = "#15120e"
    body_ink: str = "#1c1812"
    soft_ink: str = "#3a3227"
    faint_ink: str = "#5a5145"
    rule_color: str = "#cac2b0"
    accent_ink: str = "#6b3226"
    masthead_rule_weight: float = 2.5
    column_rules: bool = True
    masthead_frame: str = "double_rule"
    rubric_caps: bool = True
    ink_spread: bool = True  # text-shadow — имитация растекания краски
    uppercase_headlines: bool = False
    invert_rubrics: bool = False


@dataclass
class Publication:
    """Издание: постоянный облик газеты, общий для всех её номеров.

    Живёт в библиотеке приложения отдельным файлом. Выпуск хранит ссылку
    ``publication_id`` и снимок оформления, чтобы файл проекта открывался и без
    библиотеки; при открытии снимок обновляется из библиотеки, если издание там
    нашлось.
    """

    id: str = field(default_factory=lambda: new_id("pub"))
    name: str = ""
    brand: Brand = field(default_factory=Brand)
    style: Style = field(default_factory=Style)
    typography: Typography = field(default_factory=Typography)
    masthead_left: str = ""
    masthead_right: str = ""
    year_line: str = ""
    city: str = ""
    price: str = ""
    pages_count: int = 2
    created_at: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))
    updated_at: str = ""

    @property
    def display_name(self) -> str:
        return self.name or self.brand.display_name or "Без названия"


@dataclass
class Project:
    """Файл проекта: всё, что нужно, чтобы вернуться к правке выпуска."""

    format_version: int = PROJECT_FORMAT_VERSION
    app: str = "pechatnya"
    title: str = ""
    publication_id: str = ""
    brand: Brand = field(default_factory=Brand)
    issue: Issue = field(default_factory=Issue)
    style: Style = field(default_factory=Style)
    typography: Typography = field(default_factory=Typography)
    paper: Paper = field(default_factory=Paper)
    pages: list[Page] = field(default_factory=list)
    articles: list[Article] = field(default_factory=list)
    page_format: str = "A3"  # A3 | A4
    orientation: str = "portrait"
    margins_mm: list[float] = field(default_factory=lambda: [14, 14, 12, 12])
    grid_columns: int = 6
    grid_gutter_mm: float = 4.0
    created_at: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))
    saved_at: str = ""

    # ------------------------------------------------------------ издание
    def inherit(self, publication: "Publication") -> None:
        """Берёт оформление из издания. Вёрстку и тексты не трогает."""
        self.publication_id = publication.id
        self.brand = from_dict(Brand, to_dict(publication.brand))
        self.style = from_dict(Style, to_dict(publication.style))
        self.typography = from_dict(Typography, to_dict(publication.typography))
        self.issue.title = publication.display_name
        self.issue.motto = publication.brand.motto
        self.issue.masthead_left = publication.masthead_left
        self.issue.masthead_right = publication.masthead_right
        self.issue.year_line = publication.year_line
        if not self.issue.city:
            self.issue.city = publication.city
        if not self.issue.price:
            self.issue.price = publication.price
        self.style.masthead_frame = self.issue.masthead_frame

    def as_publication(self, name: str = "") -> "Publication":
        """Собирает издание из текущего оформления выпуска."""
        return Publication(
            name=name or self.issue.title,
            brand=from_dict(Brand, to_dict(self.brand)),
            style=from_dict(Style, to_dict(self.style)),
            typography=from_dict(Typography, to_dict(self.typography)),
            masthead_left=self.issue.masthead_left,
            masthead_right=self.issue.masthead_right,
            year_line=self.issue.year_line,
            city=self.issue.city,
            price=self.issue.price,
            pages_count=len(self.pages) or self.issue.pages_count,
        )

    # ------------------------------------------------------------------ доступ
    def article(self, article_id: Optional[str]) -> Optional[Article]:
        if not article_id:
            return None
        return next((item for item in self.articles if item.id == article_id), None)

    def page(self, index: int) -> Page:
        return self.pages[max(0, min(index, len(self.pages) - 1))]

    def find_block(self, block_id: str) -> tuple[Optional[Page], Optional[Block]]:
        for page in self.pages:
            block = page.find_block(block_id)
            if block:
                return page, block
        return None, None

    def page_of_block(self, block_id: str) -> Optional[int]:
        for index, page in enumerate(self.pages):
            if page.find_block(block_id):
                return index
        return None

    def unplaced_articles(self) -> list[Article]:
        placed = {block.article_id for page in self.pages for block in page.blocks()}
        return [item for item in self.articles if item.id not in placed]

    def assign(self, article_id: str, block_id: str) -> None:
        """Кладёт статью в блок, освобождая тот блок, где она лежала раньше."""
        for page in self.pages:
            for block in page.blocks():
                if block.article_id == article_id:
                    block.article_id = None
                    block.article_part = 0
                    if block.kind == "article":
                        block.kind = "empty"
        _, target = self.find_block(block_id)
        if target is None:
            return
        previous = target.article_id
        target.article_id = article_id
        target.kind = "article"
        target.modules = []
        article = self.article(article_id)
        if article:
            article.block_id = block_id
        if previous and previous != article_id:
            stale = self.article(previous)
            if stale:
                stale.block_id = None

    def detach(self, article_id: str) -> None:
        """Снимает статью с полосы целиком — вместе с блоком «продолжения»."""
        for page in self.pages:
            for block in page.blocks():
                if block.article_id == article_id:
                    block.article_id = None
                    block.article_part = 0
                    block.kind = "empty"
        article = self.article(article_id)
        if article:
            article.block_id = None
            article.continued_on = None
            article.split_at = None

    # ------------------------------------------------- продолжение на стр. N
    def block_of(self, article_id: str, part: int = 0) -> Optional[Block]:
        for page in self.pages:
            for block in page.blocks():
                if block.article_id == article_id and block.article_part == part:
                    return block
        return None

    def free_block_on(self, page_index: int) -> Optional[Block]:
        """Первый свободный блок полосы — туда ляжет продолжение."""
        if not 0 <= page_index < len(self.pages):
            return None
        return next((block for block in self.pages[page_index].blocks() if block.is_empty), None)

    def place_continuation(self, article_id: str, page_index: int, split_at: int) -> Optional[Block]:
        """Кладёт остаток статьи на указанную полосу и ставит перекрёстные ссылки."""
        article = self.article(article_id)
        if article is None:
            return None
        target = self.block_of(article_id, part=1) or self.free_block_on(page_index)
        if target is None:
            return None
        source = self.block_of(article_id, part=0)
        if source is not None and source.id == target.id:
            return None
        target.article_id = article_id
        target.article_part = 1
        target.kind = "article"
        target.modules = []
        article.split_at = max(1, split_at)
        article.continued_on = page_index + 1
        return target

    def drop_continuation(self, article_id: str) -> None:
        block = self.block_of(article_id, part=1)
        if block is not None:
            block.article_id = None
            block.article_part = 0
            block.kind = "empty"
        article = self.article(article_id)
        if article is not None:
            article.split_at = None
            article.continued_on = None

    def page_of_article(self, article_id: str, part: int = 0) -> Optional[int]:
        block = self.block_of(article_id, part)
        return self.page_of_block(block.id) if block else None

    # -------------------------------------------------------------- сохранение
    def to_json_dict(self) -> dict[str, Any]:
        data = to_dict(self)
        data["saved_at"] = dt.datetime.now().isoformat(timespec="seconds")
        return data

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "Project":
        return from_dict(cls, data)

    def clone_for_new_issue(self, number: str, date: str) -> "Project":
        """Новый номер того же издания: оформление наследуется, тексты — нет."""
        copy = Project.from_json_dict(to_dict(self))
        copy.issue.number = number
        copy.issue.date = date
        copy.title = f"{self.issue.title}, № {number}"
        copy.created_at = dt.datetime.now().isoformat(timespec="seconds")
        copy.saved_at = ""
        copy.articles = []
        for page in copy.pages:
            page.id = new_id("pg")
            for row in page.rows:
                row.id = new_id("row")
                for block in row.blocks:
                    block.id = new_id("blk")
                    block.article_id = None
                    if block.kind == "article":
                        block.kind = "empty"
        return copy


@dataclass
class BlockFit:
    """Результат замера вместимости блока (README, «Контроль вместимости»)."""

    block_id: str
    percent: float = 0.0
    overflow_chars: int = 0
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def overflows(self) -> bool:
        return self.percent > 100.0
