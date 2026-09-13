"""Пресеты оформления, шаблоны сеток и стартовое наполнение проекта.

Значения взяты из README-хендофа: пять пресетов экрана 03 и шесть шаблонов
сетки экрана 04. Пресет — это стартовый набор, любые его значения пользователь
потом правит вручную в панелях «Стиль» и «Типографика».
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import (
    Block,
    Frame,
    ImageRef,
    Issue,
    ModuleData,
    Page,
    Project,
    Publication,
    Style,
    Typography,
    column,
    leaf,
    row,
)

# --------------------------------------------------------------------- пресеты


@dataclass(frozen=True)
class StylePreset:
    id: str
    name: str
    description: str
    style: Style
    typography: Typography


def _style(**kwargs) -> Style:
    return Style(**kwargs)


STYLE_PRESETS: list[StylePreset] = [
    StylePreset(
        id="classic",
        name="Классическая пресса",
        description="Антиква, двойная линейка, три колонки, полутоновые снимки.",
        style=_style(preset_id="classic", paper_color="#f1ece0"),
        typography=Typography(),
    ),
    StylePreset(
        id="tabloid",
        name="Таблоид",
        description="Крикливый гротеск, жирная линейка 4 px, крупное фото.",
        style=_style(
            preset_id="tabloid",
            paper_color="#eae5d9",
            ink_color="#141210",
            accent_ink="#8a2a1c",
            masthead_rule_weight=4.0,
            uppercase_headlines=True,
        ),
        typography=Typography(
            heading_font="Oswald",
            body_font="PT Serif",
            caption_font="PT Sans Narrow",
            masthead_pt=40,
            lead_headline_pt=33,
            article_headline_pt=12,
            body_pt=8.6,
            leading=1.48,
        ),
    ),
    StylePreset(
        id="bulletin",
        name="Официальный вестник",
        description="Двойная рамка шапки, узкий гротеск капителью, казённый тон.",
        style=_style(
            preset_id="bulletin",
            paper_color="#f0eee6",
            ink_color="#23221e",
            accent_ink="#3c3a33",
            rule_color="#c6c2b4",
            masthead_frame="ornament",
            masthead_rule_weight=2.0,
            ink_spread=False,
        ),
        typography=Typography(
            heading_font="PT Sans Narrow",
            body_font="PT Serif",
            caption_font="PT Sans Narrow",
            masthead_pt=34,
            lead_headline_pt=21,
            article_headline_pt=10.5,
            body_pt=8.2,
            leading=1.55,
        ),
    ),
    StylePreset(
        id="agitprop",
        name="Партийная агитка",
        description="Чёрная плашка с вывороткой, брусок 6 px, красный акцент.",
        style=_style(
            preset_id="agitprop",
            paper_color="#e8e0cd",
            ink_color="#15120e",
            accent_ink="#8a2a1c",
            masthead_rule_weight=6.0,
            invert_rubrics=True,
            uppercase_headlines=True,
        ),
        typography=Typography(
            heading_font="Oswald",
            body_font="PT Serif",
            caption_font="PT Sans Narrow",
            masthead_pt=32,
            lead_headline_pt=26,
            article_headline_pt=12,
            body_pt=8.8,
            leading=1.45,
        ),
    ),
    StylePreset(
        id="underground",
        name="Подпольный листок",
        description="Машинописный моноширинный набор, слепая печать, звёздочки.",
        style=_style(
            preset_id="underground",
            paper_color="#e4ded0",
            ink_color="#221f1a",
            body_ink="#2a261f",
            accent_ink="#4a4238",
            rule_color="#b9b1a0",
            masthead_frame="none",
            masthead_rule_weight=1.0,
            column_rules=False,
            ink_spread=True,
        ),
        typography=Typography(
            heading_font="IBM Plex Mono",
            body_font="IBM Plex Mono",
            caption_font="IBM Plex Mono",
            masthead_pt=24,
            lead_headline_pt=16,
            article_headline_pt=10,
            body_pt=7.6,
            leading=1.6,
        ),
    ),
]

PRESETS_BY_ID = {preset.id: preset for preset in STYLE_PRESETS}


def apply_preset(project: Project, preset_id: str) -> None:
    """Накатывает пресет на проект, сохраняя тексты и геометрию блоков."""
    preset = PRESETS_BY_ID.get(preset_id)
    if preset is None:
        return
    project.style = Style(**vars(preset.style))
    project.typography = Typography(**vars(preset.typography))
    project.brand.logo_font = preset.typography.heading_font
    project.brand.logo_size_pt = preset.typography.masthead_pt
    project.brand.ink = preset.style.ink_color


# ------------------------------------------------------------- модули полосы

MODULE_LIBRARY: dict[str, Callable[[], ModuleData]] = {
    "ad": lambda: ModuleData(kind="ad", title="ОБЪЯВЛЕНИЕ", text="", framed=True),
    "weather": lambda: ModuleData(kind="weather", title="ПОГОДА", text="", framed=True),
    "rates": lambda: ModuleData(
        kind="rates", title="ЦЕНЫ И КУРСЫ", rows=[["", ""], ["", ""], ["", ""]], framed=False
    ),
    "schedule": lambda: ModuleData(
        kind="schedule", title="РАСПИСАНИЕ", rows=[["", ""], ["", ""], ["", ""]], framed=True
    ),
    "list": lambda: ModuleData(
        kind="list", title="ПЕРЕЧЕНЬ", rows=[[""], [""], [""]], framed=False
    ),
    "quote": lambda: ModuleData(kind="quote", title="", text="", attribution="", framed=False),
    "fact": lambda: ModuleData(kind="fact", title="", text="", attribution="", framed=False),
    "obituary": lambda: ModuleData(kind="obituary", title="ПАМЯТИ", text="", framed=False),
    "photo": lambda: ModuleData(
        kind="photo", title="", text="", framed=False, image=ImageRef(caption="", height_px=120)
    ),
    "free": lambda: ModuleData(kind="free", title="", text="", framed=False),
}

MODULE_TITLES = {
    "ad": "Объявление",
    "weather": "Погода",
    "rates": "Цены",
    "schedule": "Расписание",
    "list": "Перечень",
    "quote": "Цитата",
    "fact": "Цифра дня",
    "obituary": "Некролог",
    "photo": "Снимок",
    "free": "Свободный блок",
}

# Подсказка, что писать в модуле, — видна в панели блока.
MODULE_HINTS = {
    "ad": "текст объявления",
    "weather": "погода на сутки",
    "rates": "строки «товар — цена»",
    "schedule": "строки «время — событие»",
    "list": "пункты перечня, по одному в строке",
    "quote": "цитата и кто сказал",
    "fact": "крупное число и пояснение",
    "obituary": "кто и когда",
    "photo": "снимок и подпись",
    "free": "заголовок и текст на ваше усмотрение",
}


def make_module(kind: str) -> ModuleData:
    factory = MODULE_LIBRARY.get(kind, MODULE_LIBRARY["ad"])
    return factory()


# ------------------------------------------------------------ шаблоны сеток


@dataclass(frozen=True)
class GridTemplate:
    id: str
    name: str
    description: str
    kind: str  # front | inner | both
    blocks_count: int
    build: Callable[[], Frame]


def _block(label: str, **kwargs) -> Block:
    return Block(label=label, kind=kwargs.pop("kind", "empty"), **kwargs)


def _side(label: str, width: float = 196.0, **kwargs) -> Frame:
    """Узкая колонка врезок: своя ширина в пикселях, набор в одну колонку."""
    block = _block(label, columns=1, column_rules=False, align="left", drop_cap=False,
                   border_left=True, **kwargs)
    return leaf(block, fixed=width)


def _strip(*labels: str, height: float = 132.0, columns: int = 1) -> Frame:
    """Нижняя лента: несколько коротких материалов через разделители."""
    cells = [
        leaf(_block(label, columns=columns, drop_cap=False, headline_scale=0.4, border_top=2.5))
        for label in labels
    ]
    return row(*cells, fixed=height, gap=13.0)


def _tree_main_side() -> Frame:
    return column(
        row(
            leaf(_block("Главная статья", columns=3)),
            _side("Боковая колонка"),
        ),
        _strip("Подвал — слева", "Подвал — в центре", "Подвал — справа"),
    )


def _tree_three_columns() -> Frame:
    return column(
        row(
            leaf(_block("Левая колонка", columns=1, headline_scale=0.55)),
            leaf(_block("Средняя колонка", columns=1, headline_scale=0.7)),
            leaf(_block("Правая колонка", columns=1, headline_scale=0.55)),
        ),
        _strip("Нижняя лента", height=120.0, columns=3),
    )


def _tree_photo_lead() -> Frame:
    return column(
        leaf(_block("Фото-гвоздь", columns=2), fixed=300.0),
        row(
            leaf(_block("Слева", columns=2, headline_scale=0.6)),
            _side("Справа", width=230.0, headline_scale=0.5),
        ),
        _strip("Подвал", height=110.0, columns=3),
    )


def _tree_vertical_masthead() -> Frame:
    return column(
        row(
            leaf(
                _block("Боковая шапка", columns=1, drop_cap=False, align="left"),
                fixed=150.0,
            ),
            leaf(_block("Главная статья", columns=2)),
            _side("Врезки", width=170.0),
        ),
        _strip("Подвал — слева", "Подвал — справа", height=140.0, columns=2),
    )


def _tree_two_leads() -> Frame:
    """Два гвоздя рядом — для номеров, где новостей две, а не одна."""
    return column(
        row(
            leaf(_block("Первый гвоздь", columns=2, headline_scale=0.85)),
            leaf(_block("Второй гвоздь", columns=2, headline_scale=0.85)),
            _side("Объявления", width=168.0),
        ),
        _strip("Подвал — слева", "Подвал — справа", height=150.0, columns=2),
    )


def _tree_poster() -> Frame:
    """Афиша: один материал во всю полосу и лента внизу."""
    return column(
        leaf(_block("Афиша", columns=1, headline_scale=1.6, align="center", drop_cap=False)),
        _strip("Подробности", height=150.0, columns=3),
    )


def _tree_quadrants() -> Frame:
    return column(
        row(
            leaf(_block("Верхний левый", columns=2, headline_scale=0.7)),
            leaf(_block("Верхний правый", columns=2, headline_scale=0.7)),
        ),
        row(
            leaf(_block("Нижний левый", columns=2, headline_scale=0.6)),
            leaf(_block("Нижний правый", columns=2, headline_scale=0.6)),
        ),
        _strip("Лента внизу", height=104.0, columns=3),
    )


def _tree_inner_two() -> Frame:
    """Две широкие колонки — спокойная внутренняя полоса."""
    return column(
        row(
            leaf(_block("Левый материал", columns=2, headline_scale=0.75)),
            leaf(_block("Правый материал", columns=2, headline_scale=0.75)),
        ),
        _strip("Подвал", height=130.0, columns=3),
    )


def _tree_gallery() -> Frame:
    """Полоса снимков: шесть клеток под фото с подписями."""
    def cell(label: str) -> Frame:
        return leaf(_block(label, columns=1, drop_cap=False, headline_scale=0.4))

    return column(
        row(cell("Снимок 1"), cell("Снимок 2"), cell("Снимок 3")),
        row(cell("Снимок 4"), cell("Снимок 5"), cell("Снимок 6")),
    )


def _tree_letters() -> Frame:
    """Письма и ответы: узкая колонка писем, широкий разбор, низ на два."""
    return column(
        row(
            _side("Письма", width=210.0),
            leaf(_block("Разбор", columns=2)),
        ),
        _strip("Ответ редакции", "Короткой строкой", height=150.0, columns=2),
    )


def _tree_blank() -> Frame:
    return column(leaf(_block("Пустой блок", columns=3)))


GRID_TEMPLATES: list[GridTemplate] = [
    GridTemplate("front-main-side", "Шапка + главная и боковая",
                 "Гвоздь номера на три колонки и узкая колонка врезок.", "front", 5,
                 _tree_main_side),
    GridTemplate("front-three-columns", "Шапка + три колонки",
                 "Три равные колонки и нижняя лента — самый ходовой макет.", "front", 4,
                 _tree_three_columns),
    GridTemplate("front-two-leads", "Два гвоздя",
                 "Две главные новости рядом и колонка объявлений.", "front", 6, _tree_two_leads),
    GridTemplate("photo-lead", "Фото-гвоздь",
                 "Крупный снимок вверху, под ним два материала и подвал.", "both", 6,
                 _tree_photo_lead),
    GridTemplate("vertical-masthead", "Вертикальная шапка",
                 "Логотип сбоку, набор в две колонки, врезки справа.", "front", 5,
                 _tree_vertical_masthead),
    GridTemplate("poster", "Афиша",
                 "Один материал во всю полосу — объявление, призыв, некролог.", "both", 4,
                 _tree_poster),
    GridTemplate("quadrants", "Четыре квадранта",
                 "Четыре равных материала и лента внизу.", "inner", 5, _tree_quadrants),
    GridTemplate("inner-two-columns", "Две широкие колонки",
                 "Спокойная внутренняя полоса: два материала и подвал.", "inner", 5,
                 _tree_inner_two),
    GridTemplate("gallery", "Полоса снимков",
                 "Шесть клеток под фотографии с подписями.", "inner", 6, _tree_gallery),
    GridTemplate("letters", "Письма и разбор",
                 "Узкая колонка писем, широкий разбор, низ на два материала.", "inner", 5,
                 _tree_letters),
    GridTemplate("blank", "Пустая сетка",
                 "Один блок на всю полосу — делите его сами.", "both", 1, _tree_blank),
]

TEMPLATES_BY_ID = {template.id: template for template in GRID_TEMPLATES}


def build_page(template_id: str, kind: str = "front") -> Page:
    """Собирает полосу по шаблону. ``user:<id>`` — своя сохранённая сетка."""
    if template_id.startswith("user:"):
        root = _user_template_root(template_id.split(":", 1)[1])
        if root is not None:
            return Page(
                kind=kind,
                template_id=template_id,
                show_masthead=(kind == "front"),
                root=root,
            )
    template = TEMPLATES_BY_ID.get(template_id, GRID_TEMPLATES[0])
    return Page(
        kind=kind,
        template_id=template.id,
        show_masthead=(kind == "front"),
        root=template.build(),
    )


def _user_template_root(template_id: str):
    """Копия дерева своей сетки со свежими идентификаторами."""
    from . import storage
    from .models import Frame, new_id
    from .serde import from_dict, to_dict

    saved = next((item for item in storage.user_templates() if item.id == template_id), None)
    if saved is None:
        return None
    root = from_dict(Frame, to_dict(saved.root))
    for frame in root.walk():
        frame.id = new_id("frm")
        if frame.block is not None:
            frame.block.id = new_id("blk")
            frame.block.article_id = None
            frame.block.article_part = 0
    return root


def apply_template(page: Page, template_id: str) -> None:
    """Меняет сетку полосы, стараясь сохранить уже размещённые статьи."""
    placed = [
        (block.article_id, block.article_part) for block in page.blocks() if block.article_id
    ]
    modules = [block.modules for block in page.blocks() if block.modules]
    page.root = TEMPLATES_BY_ID.get(template_id, GRID_TEMPLATES[0]).build()
    page.template_id = template_id
    blocks = list(page.blocks())
    for block, (article_id, part) in zip(blocks, placed):
        block.article_id = article_id
        block.article_part = part  # продолжение остаётся продолжением
        block.kind = "article"
    for block, stack in zip(blocks[len(placed):], modules):
        block.modules = stack
        block.kind = "module"
    page.normalize()


# ------------------------------------------------------- стартовые проекты


def new_project(
    issue: Issue | None = None,
    publication: "Publication | None" = None,
    template_id: str = "front-main-side",
    inner_template_id: str = "quadrants",
) -> Project:
    """Пустой выпуск: шапка и сетка есть, материалов ещё нет."""
    issue = issue or Issue()
    project = Project(issue=issue)
    if publication is not None:
        project.inherit(publication)
    project.title = _project_title(issue)
    project.style.masthead_frame = issue.masthead_frame
    project.pages = [build_page(template_id, "front")]
    for _ in range(max(0, issue.pages_count - 1)):
        project.pages.append(build_page(inner_template_id, "inner"))
    return project


def _project_title(issue: Issue) -> str:
    name = issue.title.strip() or "Без названия"
    return f"{name}, № {issue.number}" if issue.number.strip() else name
