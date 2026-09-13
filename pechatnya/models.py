"""Модель данных выпуска: бренд, издание, полосы, блоки, статьи, оформление.

Вся структура соответствует разделу «State Management» из README-хендофа:
``brand`` → ``issue`` → ``pages[] → root (дерево Frame) → blocks[]`` плюс
сквозной список ``articles[]``, настройки типографики, бумаги и стиля.

Геометрия полосы — дерево: узел либо делит место между детьми (в ряд или
в колонку), либо несёт блок. Размер задаётся весом (доля свободного места) или
фиксированной величиной в пикселях. Отсюда и деление блока, и удаление, и
перетаскивание границ — всё это правка одного-двух чисел, не ломающая вёрстку
при смене формата листа.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from .serde import from_dict, to_dict

PROJECT_FORMAT_VERSION = 1

# Базовый лист в дизайн-пикселях (96 dpi) — A4, под него подобраны метрики набора.
SHEET_WIDTH = 794
SHEET_HEIGHT = 1123
MARGIN_V = 34
MARGIN_H = 38

PT_TO_PX = 96 / 72
MM_TO_PX = 96 / 25.4

# Форматы листа в миллиметрах (портрет).
PAGE_FORMATS: dict[str, tuple[float, float]] = {
    "A3": (297.0, 420.0),
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "Таблоид": (289.0, 380.0),
    "Бродлист": (305.0, 560.0),
    "Листовка": (148.0, 148.0),
}


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
    split_source_len: Optional[int] = None  # длина текста, при которой считали перенос

    @property
    def split_is_stale(self) -> bool:
        """Текст правили после переноса — точку разрыва надо пересчитать."""
        return self.split_at is not None and self.split_source_len != len(self.body)

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
    columns: int = 3
    column_rules: bool = True
    hyphens: bool = False
    align: str = "justify"  # left | justify | center
    drop_cap: bool = True
    headline_scale: float = 1.0
    body_scale: float = 1.0  # кегль текста в блоке относительно издания
    column_gap: float = 14.0
    border_left: bool = False
    border_top: float = 0.0
    frame: str = "none"  # none | hairline | double | bold
    tint: bool = False  # плашка под блоком
    padding: float = 0.0
    article_id: Optional[str] = None
    article_part: int = 0  # 1 — блок с «продолжением» статьи
    modules: list[ModuleData] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return self.article_id is None and not self.modules


@dataclass
class Frame:
    """Узел сетки полосы: либо контейнер, либо блок.

    ``direction`` пустой — это лист с блоком; ``row`` — дети стоят в ряд,
    ``column`` — друг под другом. Дерево даёт то, чего не давал плоский список
    строк: любой блок делится в любую сторону и удаляется, а соседи занимают
    освободившееся место.
    """

    id: str = field(default_factory=lambda: new_id("frm"))
    direction: str = ""  # "" | row | column
    weight: float = 1.0
    fixed: Optional[float] = None  # px: ширина в ряду, высота в колонке
    gap: float = 14.0
    children: list["Frame"] = field(default_factory=list)
    block: Optional[Block] = None

    @property
    def is_leaf(self) -> bool:
        return not self.direction

    def leaves(self) -> Iterator["Frame"]:
        if self.is_leaf:
            if self.block is not None:
                yield self
            return
        for child in self.children:
            yield from child.leaves()

    def walk(self) -> Iterator["Frame"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, frame_id: str) -> Optional["Frame"]:
        return next((frame for frame in self.walk() if frame.id == frame_id), None)

    def parent_of(self, frame_id: str) -> Optional["Frame"]:
        for frame in self.walk():
            if any(child.id == frame_id for child in frame.children):
                return frame
        return None

    def leaf_of_block(self, block_id: str) -> Optional["Frame"]:
        return next(
            (frame for frame in self.leaves() if frame.block and frame.block.id == block_id), None
        )


def leaf(block: Block, weight: float = 1.0, fixed: Optional[float] = None) -> Frame:
    return Frame(block=block, weight=weight, fixed=fixed)


def row(*children: Frame, weight: float = 1.0, fixed: Optional[float] = None,
        gap: float = 14.0) -> Frame:
    return Frame(direction="row", children=list(children), weight=weight, fixed=fixed, gap=gap)


def column(*children: Frame, weight: float = 1.0, fixed: Optional[float] = None,
           gap: float = 12.0) -> Frame:
    return Frame(direction="column", children=list(children), weight=weight, fixed=fixed, gap=gap)


def _prune_frame(frame: Frame) -> bool:
    """Оставляет узел в дереве или сообщает, что он пуст и его надо выбросить."""
    if frame.is_leaf:
        return frame.block is not None
    frame.children = [child for child in frame.children if _prune_frame(child)]
    if not frame.children:
        return False
    if len(frame.children) == 1:
        only = frame.children[0]
        frame.direction = only.direction
        frame.children = only.children
        frame.block = only.block
        frame.gap = only.gap
    return True


@dataclass
class Page:
    """Полоса выпуска: шапка, дерево блоков, колонцифра."""

    id: str = field(default_factory=lambda: new_id("pg"))
    kind: str = "front"  # front | inner
    template_id: str = "front-main-side"
    show_masthead: bool = True
    root: Frame = field(default_factory=lambda: column(leaf(Block(label="Блок"))))

    # ------------------------------------------------------------- доступ
    def frames(self) -> Iterator[Frame]:
        return self.root.walk()

    def leaves(self) -> Iterator[Frame]:
        return self.root.leaves()

    def blocks(self) -> Iterator[Block]:
        for frame in self.root.leaves():
            if frame.block is not None:
                yield frame.block

    def find_block(self, block_id: str) -> Optional[Block]:
        frame = self.root.leaf_of_block(block_id)
        return frame.block if frame else None

    # ------------------------------------------------------- перестройка
    def split_block(self, block_id: str, direction: str) -> Optional[Block]:
        """Делит блок пополам: рядом появляется пустой блок."""
        frame = self.root.leaf_of_block(block_id)
        if frame is None or frame.block is None:
            return None
        fresh = Block(
            label="Новый блок",
            columns=1 if direction == "row" else frame.block.columns,
            drop_cap=False,
            headline_scale=frame.block.headline_scale,
        )
        parent = self.root.parent_of(frame.id)
        if parent is not None and parent.direction == direction:
            index = parent.children.index(frame)
            if frame.fixed is not None:
                frame.fixed = max(60.0, frame.fixed / 2)
                parent.children.insert(index + 1, leaf(fresh, fixed=frame.fixed))
            else:
                frame.weight = max(0.1, frame.weight / 2)
                parent.children.insert(index + 1, leaf(fresh, weight=frame.weight))
        else:
            # лист превращается в контейнер с двумя блоками
            moved = leaf(frame.block)
            frame.block = None
            frame.direction = direction
            frame.children = [moved, leaf(fresh)]
        self.normalize()
        return fresh

    def remove_block(self, block_id: str) -> bool:
        """Убирает блок; соседи занимают его место. Последний блок не удаляем."""
        frame = self.root.leaf_of_block(block_id)
        if frame is None:
            return False
        parent = self.root.parent_of(frame.id)
        if parent is None or len(list(self.leaves())) <= 1:
            return False
        parent.children.remove(frame)
        self.normalize()
        return True

    def normalize(self) -> None:
        """Приводит дерево в порядок после любой перестройки.

        Убирает опустевшие контейнеры и схлопывает те, где остался один ребёнок:
        иначе в сетке копятся невидимые узлы, а превью и ручки границ начинают
        врать. Полоса без единого блока получает пустой блок.
        """
        if not _prune_frame(self.root):
            self.root = column(leaf(Block(label="Блок")))

    def move_block(self, block_id: str, delta: int) -> bool:
        """Меняет блок местами с соседом внутри контейнера."""
        frame = self.root.leaf_of_block(block_id)
        if frame is None:
            return False
        parent = self.root.parent_of(frame.id)
        if parent is None:
            return False
        index = parent.children.index(frame)
        target = index + delta
        if not 0 <= target < len(parent.children):
            return False
        parent.children[index], parent.children[target] = (
            parent.children[target],
            parent.children[index],
        )
        return True

    def add_block(self, direction: str = "column") -> Block:
        """Добавляет блок в конец полосы (снизу или справа)."""
        fresh = Block(label="Новый блок", drop_cap=False)
        if self.root.is_leaf:
            moved = leaf(self.root.block) if self.root.block else None
            self.root.block = None
            self.root.direction = direction
            self.root.children = [item for item in (moved, leaf(fresh)) if item]
        elif self.root.direction == direction:
            self.root.children.append(leaf(fresh))
        else:
            inner = Frame(
                direction=self.root.direction, children=self.root.children, gap=self.root.gap
            )
            self.root.direction = direction
            self.root.children = [inner, leaf(fresh)]
        self.normalize()
        return fresh


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
    typography_polish: bool = True  # кавычки-ёлочки, тире, неразрывные пробелы
    trim_partial_lines: bool = True  # не показывать обрезанную половину строки
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
    page_format: str = "A4"
    orientation: str = "portrait"  # portrait | landscape
    custom_size_mm: list[float] = field(default_factory=lambda: [210.0, 297.0])
    margins_mm: list[float] = field(default_factory=lambda: [9.0, 9.0, 10.0, 10.0])
    grid_columns: int = 6
    grid_gutter_mm: float = 4.0
    created_at: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))
    saved_at: str = ""

    # -------------------------------------------------------------- лист
    def sheet_mm(self) -> tuple[float, float]:
        """Размер листа в миллиметрах с учётом ориентации."""
        if self.page_format in PAGE_FORMATS:
            width, height = PAGE_FORMATS[self.page_format]
        else:
            width, height = (self.custom_size_mm + [210.0, 297.0])[:2]
        if self.orientation == "landscape":
            width, height = height, width
        return float(width), float(height)

    def sheet_px(self) -> tuple[int, int]:
        """Размер листа в дизайн-пикселях (96 dpi) — в них рисуется полоса."""
        width, height = self.sheet_mm()
        return max(200, round(width * MM_TO_PX)), max(200, round(height * MM_TO_PX))

    def margins_px(self) -> tuple[float, float, float, float]:
        """Поля листа: верх, низ, лево, право."""
        values = (list(self.margins_mm) + [9.0, 9.0, 10.0, 10.0])[:4]
        return tuple(round(max(0.0, value) * MM_TO_PX, 2) for value in values)  # type: ignore[return-value]

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
        """Кладёт статью в блок целиком, освобождая прежние блоки.

        Если статья была разделена между полосами, перенос отменяется: иначе
        остаток текста остался бы нигде, а на полосе висела бы строка
        «продолжение на стр.», ведущая в пустоту.
        """
        article = self.article(article_id)
        if article is not None and article.split_at is not None:
            self.drop_continuation(article_id)
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
        # в блоке мог лежать чужой материал — снимаем его целиком, иначе у той
        # статьи остался бы висячий перенос без начала
        if target.article_id and target.article_id != article_id:
            self.release_block(target)
        target.article_id = article_id
        target.article_part = 0
        target.kind = "article"
        target.modules = []
        if article is not None:
            article.block_id = block_id
        self.repair_continuations()

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
            article.split_source_len = None

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
        source = self.block_of(article_id, part=0)
        if source is None:
            return None  # переносить нечего: статья не размещена
        target = self.block_of(article_id, part=1) or self.free_block_on(page_index)
        if target is None or target.id == source.id:
            return None
        if target.article_id and target.article_id != article_id:
            self.release_block(target)
        target.article_id = article_id
        target.article_part = 1
        target.kind = "article"
        target.modules = []
        article.split_at = max(1, split_at)
        article.split_source_len = len(article.body)
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
            article.split_source_len = None
            article.continued_on = None

    def release_block(self, block: "Block") -> None:
        """Готовит блок к удалению: снимает с него статью, не теряя текст.

        Блок с продолжением — отменяем перенос, статья остаётся целой на своей
        полосе. Блок с началом статьи — снимаем статью с полосы совсем.
        """
        if not block.article_id:
            return
        if block.article_part == 1:
            self.drop_continuation(block.article_id)
        else:
            self.detach(block.article_id)

    def repair_continuations(self) -> int:
        """Снимает переносы, у которых потерялась одна из частей.

        Такое бывает после смены сетки или удаления полосы: иначе на полосе
        осталась бы строка «продолжение на стр.», ведущая в никуда, а хвост
        текста пропал бы из выпуска.
        """
        repaired = 0
        for article in self.articles:
            if article.split_at is None and article.continued_on is None:
                continue
            head = self.block_of(article.id, part=0)
            tail = self.block_of(article.id, part=1)
            if head is None or tail is None:
                self.drop_continuation(article.id)
                repaired += 1
                continue
            page = self.page_of_block(tail.id)
            if page is not None and article.continued_on != page + 1:
                # Полосы переставили — номер в строке «продолжение на стр.» устарел.
                article.continued_on = page + 1
                repaired += 1
        return repaired

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
        return from_dict(cls, migrate_project_dict(data))

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
            for frame in page.frames():
                frame.id = new_id("frm")
                if frame.block is not None:
                    frame.block.id = new_id("blk")
                    frame.block.article_id = None
                    frame.block.article_part = 0
                    if frame.block.kind == "article":
                        frame.block.kind = "empty"
        return copy


def migrate_project_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Читает файлы прошлых версий: плоские строки полосы → дерево блоков."""
    if not isinstance(data, dict) or not data.get("pages"):
        return data
    pages = data["pages"]
    if not any(isinstance(page, dict) and "rows" in page for page in pages):
        return data
    data = dict(data)
    migrated = []
    for page in pages:
        if not isinstance(page, dict) or "rows" not in page:
            migrated.append(page)
            continue
        page = dict(page)
        rows = page.pop("rows") or []
        children = []
        for old_row in rows:
            cells = [
                {
                    "direction": "",
                    "weight": block.get("weight", 1.0),
                    "fixed": block.get("fixed_width"),
                    "block": block,
                }
                for block in old_row.get("blocks", [])
            ]
            if not cells:
                continue
            children.append(
                {
                    "direction": "row",
                    "weight": old_row.get("weight", 1.0),
                    "fixed": old_row.get("fixed_height"),
                    "gap": old_row.get("gap", 14.0),
                    "children": cells,
                }
            )
        page["root"] = {"direction": "column", "gap": 12.0, "children": children}
        migrated.append(page)
    data["pages"] = migrated
    return data


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
