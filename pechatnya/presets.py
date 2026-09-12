"""Пресеты оформления, шаблоны сеток и стартовое наполнение проекта.

Значения взяты из README-хендофа: пять пресетов экрана 03 и шесть шаблонов
сетки экрана 04. Пресет — это стартовый набор, любые его значения пользователь
потом правит вручную в панелях «Стиль» и «Типографика».
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import (
    Article,
    Block,
    Brand,
    ImageRef,
    Issue,
    ModuleData,
    Page,
    Project,
    Row,
    Style,
    Typography,
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
        name="Таблоидъ",
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
        name="Официальный вестникъ",
        description="Двойная рамка шапки, узкий гротеск капителью, казённый тонъ.",
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
        description="Чёрная плашка съ вывороткой, брусок 6 px, красный акцентъ.",
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
        name="Подпольный листокъ",
        description="Машинописный моноширинный наборъ, слепая печать, звёздочки.",
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
    "ad": lambda: ModuleData(
        kind="ad",
        title="ОБЪЯВЛЕНIЕ",
        text="Артель «Три якоря» беретъ подряды на починку кровель и настиловъ. "
        "Спросить въ лавке Рогова, Нижнiй докъ, 7.",
        framed=True,
    ),
    "weather": lambda: ModuleData(
        kind="weather",
        title="ПОГОДА НА СУТКИ",
        text="Ветръ съ моря, къ ночи туманъ. Днёмъ +11°, ночью +6°. Барометръ падаетъ.",
        framed=True,
    ),
    "rates": lambda: ModuleData(
        kind="rates",
        title="КУРСЫ И ЦЕНЫ",
        rows=[["Хлебъ, фунтъ", "4 к."], ["Уголь, пудъ", "21 к."], ["Наёмъ лодки", "1 р. 10 к."]],
        framed=False,
    ),
    "quote": lambda: ModuleData(
        kind="quote",
        title="",
        text="«Кровлю держали на честномъ слове ещё съ прошлой зимы»",
        attribution="ПОРТОВЫЙ МАСТЕРЪ, ИМЯ НЕ НАЗВАНО",
        framed=False,
    ),
    "obituary": lambda: ModuleData(
        kind="obituary",
        title="ПАМЯТИ",
        text="Тихо скончался смотритель маяка П. Зельке, 61 годъ. Прощанiе въ пятницу у часовни.",
        framed=False,
    ),
    "photo": lambda: ModuleData(
        kind="photo",
        title="",
        text="",
        framed=False,
        image=ImageRef(caption="Подпись къ снимку", height_px=120),
    ),
}

MODULE_TITLES = {
    "ad": "Объявленiе",
    "weather": "Погода",
    "rates": "Курсы",
    "quote": "Цитата",
    "obituary": "Некрологъ",
    "photo": "Снимокъ",
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
    build: Callable[[], list[Row]]


def _block(label: str, **kwargs) -> Block:
    return Block(label=label, kind=kwargs.pop("kind", "empty"), **kwargs)


def _rows_main_side() -> list[Row]:
    return [
        Row(
            weight=1.0,
            blocks=[
                _block("Главная статья", weight=1.0, columns=3),
                _block(
                    "Боковая колонка",
                    fixed_width=196.0,
                    columns=1,
                    border_left=True,
                    column_rules=False,
                    align="left",
                    drop_cap=False,
                ),
            ],
        ),
        Row(
            weight=0.0,
            fixed_height=132.0,
            gap=13.0,
            blocks=[
                _block("Подвалъ — слева", columns=1, drop_cap=False, headline_scale=0.4),
                _block("Подвалъ — въ центре", columns=1, drop_cap=False, headline_scale=0.4),
                _block("Подвалъ — справа", columns=1, drop_cap=False, headline_scale=0.4),
            ],
        ),
    ]


def _rows_three_columns() -> list[Row]:
    return [
        Row(
            weight=1.0,
            blocks=[
                _block("Левая колонка", columns=1, headline_scale=0.55),
                _block("Средняя колонка", columns=1, headline_scale=0.7),
                _block("Правая колонка", columns=1, headline_scale=0.55),
            ],
        ),
        Row(
            weight=0.0,
            fixed_height=120.0,
            blocks=[_block("Нижняя лента", columns=3, drop_cap=False, headline_scale=0.45, border_top=2.5)],
        ),
    ]


def _rows_photo_lead() -> list[Row]:
    return [
        Row(
            weight=0.0,
            fixed_height=300.0,
            blocks=[_block("Фото-гвоздь", columns=2, headline_scale=1.0)],
        ),
        Row(
            weight=1.0,
            blocks=[
                _block("Слева", columns=2, headline_scale=0.6),
                _block("Справа", fixed_width=230.0, columns=1, border_left=True, headline_scale=0.5),
            ],
        ),
        Row(
            weight=0.0,
            fixed_height=110.0,
            blocks=[_block("Подвалъ", columns=3, drop_cap=False, headline_scale=0.42, border_top=2.5)],
        ),
    ]


def _rows_vertical_masthead() -> list[Row]:
    return [
        Row(
            weight=1.0,
            blocks=[
                _block("Боковая шапка", fixed_width=150.0, columns=1, drop_cap=False, align="left"),
                _block("Главная статья", weight=1.0, columns=2),
                _block("Врезки", fixed_width=170.0, columns=1, border_left=True, drop_cap=False, align="left"),
            ],
        ),
        Row(
            weight=0.0,
            fixed_height=140.0,
            blocks=[
                _block("Подвалъ — слева", columns=2, drop_cap=False, headline_scale=0.45, border_top=2.5),
                _block("Подвалъ — справа", columns=1, drop_cap=False, headline_scale=0.45, border_top=2.5),
            ],
        ),
    ]


def _rows_quadrants() -> list[Row]:
    return [
        Row(
            weight=1.0,
            blocks=[
                _block("Верхнiй левый", columns=2, headline_scale=0.7),
                _block("Верхнiй правый", columns=2, headline_scale=0.7),
            ],
        ),
        Row(
            weight=1.0,
            blocks=[
                _block("Нижнiй левый", columns=2, headline_scale=0.6),
                _block("Нижнiй правый", columns=2, headline_scale=0.6),
            ],
        ),
        Row(
            weight=0.0,
            fixed_height=104.0,
            blocks=[_block("Лента внизу", columns=3, drop_cap=False, headline_scale=0.4, border_top=2.5)],
        ),
    ]


def _rows_blank() -> list[Row]:
    return [Row(weight=1.0, blocks=[_block("Пустой блокъ", columns=3)])]


GRID_TEMPLATES: list[GridTemplate] = [
    GridTemplate(
        "front-main-side",
        "Шапка + главная и боковая",
        "Гвоздь номера на три колонки и узкая колонка врезокъ.",
        "front",
        5,
        _rows_main_side,
    ),
    GridTemplate(
        "front-three-columns",
        "Шапка + три колонки",
        "Три равные колонки и нижняя лента — самый ходовой макетъ.",
        "front",
        4,
        _rows_three_columns,
    ),
    GridTemplate(
        "photo-lead",
        "Фото-гвоздь",
        "Крупный снимокъ вверху, подъ нимъ два материала и подвалъ.",
        "both",
        4,
        _rows_photo_lead,
    ),
    GridTemplate(
        "vertical-masthead",
        "Вертикальная шапка",
        "Логотипъ сбоку, наборъ въ две колонки, врезки справа.",
        "front",
        5,
        _rows_vertical_masthead,
    ),
    GridTemplate(
        "quadrants",
        "Четыре квадранта",
        "Четыре равныхъ материала и лента внизу — для внутреннихъ полосъ.",
        "inner",
        5,
        _rows_quadrants,
    ),
    GridTemplate(
        "blank",
        "Пустая сетка",
        "Одинъ блокъ на всю полосу — делите границами вручную.",
        "both",
        1,
        _rows_blank,
    ),
]

TEMPLATES_BY_ID = {template.id: template for template in GRID_TEMPLATES}


def build_page(template_id: str, kind: str = "front") -> Page:
    template = TEMPLATES_BY_ID.get(template_id, GRID_TEMPLATES[0])
    return Page(
        kind=kind,
        template_id=template.id,
        show_masthead=(kind == "front"),
        rows=template.build(),
    )


def apply_template(page: Page, template_id: str) -> None:
    """Меняет сетку полосы, стараясь сохранить уже размещённые статьи."""
    placed = [block.article_id for block in page.blocks() if block.article_id]
    modules = [block.modules for block in page.blocks() if block.modules]
    page.rows = TEMPLATES_BY_ID.get(template_id, GRID_TEMPLATES[0]).build()
    page.template_id = template_id
    blocks = list(page.blocks())
    for block, article_id in zip(blocks, placed):
        block.article_id = article_id
        block.kind = "article"
    for block, stack in zip(blocks[len(placed):], modules):
        block.modules = stack
        block.kind = "module"


# ------------------------------------------------------- стартовые проекты


def new_project(
    issue: Issue | None = None,
    preset_id: str = "classic",
    template_id: str = "front-main-side",
    brand: Brand | None = None,
) -> Project:
    """Пустой выпуск: шапка и сетка есть, материалов ещё нет."""
    issue = issue or Issue()
    project = Project(title=f"{issue.title}, № {issue.number}", issue=issue)
    if brand is not None:
        project.brand = brand
    else:
        project.brand.name_cyrillic = issue.title
        project.brand.motto = issue.motto
    project.brand.superline = issue.title.split()[0].upper() if issue.title else ""
    apply_preset(project, preset_id)
    project.style.masthead_frame = issue.masthead_frame
    project.pages = [build_page(template_id, "front")]
    for _ in range(max(0, issue.pages_count - 1)):
        project.pages.append(build_page("quadrants", "inner"))
    return project


DEMO_BODY = """Ночью, около половины перваго, въ третьемъ пролёте Нижняго дока обрушилась часть кровли. Сторожъ услышалъ трескъ и успелъ вывести двоихъ грузчиковъ прежде, чемъ балка легла на настилъ. По словамъ портового мастера, кровлю держали на честномъ слове ещё съ прошлой зимы: смету на починку отклонили дважды.

## У ВОРОТЪ СЪ УТРА

Собралась артель — люди требовали объясненiй и платы за простой. Управа выставила двухъ постовыхъ, но до сору дело не дошло. Къ полудню движенiе черезъ третiй пролётъ закрыли на трое сутокъ, грузы направили на Верхнюю пристань, где и безъ того тесно.

Смотритель складовъ отстраненъ до окончанiя дознанiя. Въ конторе намъ сказали, что бумаги по прошлогодней смете «находятся въ работе» и будутъ предъявлены дознавателю въ понедельникъ.

## ЧТО ГОВОРЯТЪ АРТЕЛЬНЫЕ

Платить за простой некому, а зима близко. Трое изъ шестерыхъ работали безъ записи въ книге, и на нихъ конторскiе бумаги вовсе не заведены.

Старшiй артели Кузьма Долевъ показалъ намъ тетрадь, где отмечены выходы за апрель и май. По его счёту, конторе следуетъ уплатить сорокъ два рубля съ полтиной — за дни, когда люди являлись къ воротамъ и работы имъ не давали.

## КАКЪ БУДЕТЪ ИДТИ ГРУЗЪ

Верхняя пристань приметъ на себя весь мелкiй каботажъ, крупныя суда будутъ разгружаться на рейде съ баржъ. По оценке мастера, это удлинитъ оборотъ на полдня.

Редакцiя будетъ следить за деломъ и печатать ответы конторы безъ сокращенiй."""


def demo_project() -> Project:
    """Выпуск из макета — им открывается «Печатня» при первом запуске."""
    project = new_project(Issue(), preset_id="classic", template_id="front-main-side")
    project.title = "Вечернiй Вестникъ, № 14"
    project.style.paper_color = "#efe7d4"
    project.brand.name_cyrillic = "ВЕСТНИКЪ"
    project.brand.name_latin = "Harbour Gazette"
    project.brand.superline = "ВЕЧЕРНIЙ"

    lead = Article(
        rubric="ХРОНИКА ПРОИСШЕСТВIЙ",
        title="Ночной обвалъ въ Нижнемъ доке: движенiе закрыто на трое сутокъ",
        subtitle="Пострадавшихъ нетъ. Смотритель складовъ отстраненъ до окончанiя дознанiя, "
        "грузы перенаправлены на Верхнюю пристань.",
        author="Записалъ М. Гроувъ",
        place_time="Нижнiй докъ, 11 iюня, полночь",
        body=DEMO_BODY,
        image=ImageRef(
            caption="Третiй пролётъ утромъ 12 iюня. Балку разбирали вручную, при керосиновыхъ фонаряхъ.",
            height_px=96,
        ),
        continued_on=3,
    )
    footer = [
        Article(
            rubric="ГОРОДСКАЯ ЖИЗНЬ",
            title="Управа продлила комендантскiй часъ",
            body="До конца iюня выходъ въ портовую зону после одиннадцати — по пропускамъ. "
            "Пропуска выдаютъ въ конторе съ девяти утра, по предъявленiи рабочей книжки.",
            drop_cap=False,
        ),
        Article(
            rubric="ПОРТЪ И ТОРГЪ",
            title="«Ласточка» не вернулась къ сроку",
            body="Катеръ вышелъ къ Косе въ понедельникъ и не далъ вести. Поиски ведутъ две лодки; "
            "хозяинъ обещалъ награду тому, кто укажетъ верно.",
            drop_cap=False,
        ),
        Article(
            rubric="ПИСЬМА ВЪ РЕДАКЦIЮ",
            title="«Фонари на Косой не горятъ третью неделю»",
            body="Пишетъ лавочникъ П. Рогову: масло отпускаютъ, а зажигать некому. "
            "Ответъ конторы печатаемъ въ следующемъ номере.",
            drop_cap=False,
        ),
    ]
    extra = [
        Article(
            rubric="ДОЗНАНIЕ",
            title="Смету на починку отклоняли дважды",
            body="Мы подняли бумаги за прошлый годъ. Подрядъ на кровлю третьяго пролёта "
            "вносился въ смету въ октябре и въ феврале; оба раза управа сочла работы "
            "несрочными и перенесла ихъ на следующiй кварталъ.",
            drop_cap=False,
        ),
        Article(
            rubric="ПО ГУБЕРНIИ",
            title="Ярмарка въ Слободе открывается въ субботу",
            body="Торгъ пойдётъ три дня. Обещаны лошади съ верховыхъ заводовъ, "
            "мелкiй скотъ и шорный рядъ.",
            drop_cap=False,
        ),
    ]
    project.articles = [lead, *footer, *extra]

    front = project.pages[0]
    front.rows[0].blocks[0].label = "Главная статья"
    project.assign(lead.id, front.rows[0].blocks[0].id)
    for article, block in zip(footer, front.rows[1].blocks):
        project.assign(article.id, block.id)

    sidebar = front.rows[0].blocks[1]
    sidebar.kind = "module"
    sidebar.label = "Боковая колонка"
    sidebar.modules = [
        make_module(kind) for kind in ("weather", "rates", "quote", "ad", "obituary", "photo")
    ]
    sidebar.modules[-1].image = ImageRef(caption="", height_px=64, filter="halftone")
    return project
