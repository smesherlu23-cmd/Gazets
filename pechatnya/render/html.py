"""Сборка HTML полосы.

Почему HTML: многоколоночное перетекание, выключка по ширине, переносы,
буквица «в обтекание» и обрыв текста по высоте блока — всё это CSS умеет сам
(``column-count``, ``text-align: justify``, ``hyphens``, ``float``), а на канвасе
Flet это пришлось бы писать руками. Обоснование выбора — в docs/ARCHITECTURE.md.

Метрики набора (кегли, линейки, отступы) взяты из раздела «Полоса (наборные
метрики)» README и параметризованы моделью: стиль, типографика, бренд.
"""

from __future__ import annotations

import html
import pathlib
import re
from dataclasses import dataclass, field
from typing import Optional

from .. import fonts
from ..models import (
    Article,
    Block,
    Brand,
    ImageRef,
    MARGIN_H,
    MARGIN_V,
    ModuleData,
    Page,
    Project,
    SHEET_HEIGHT,
    SHEET_WIDTH,
    Style,
    Typography,
)
from .paper import aging_layer_css

HALFTONE = "repeating-linear-gradient(135deg,#cfc8b6 0 4px,#ddd6c6 4px 8px)"
ACCENT = "#C05B42"

# README предупреждает: при длинном названии логотип распирает grid шапки.
# Скрипт ужимает кегль под свободную ширину — набор остаётся в полосе.
FIT_LOGO_JS = """
<script>
(() => {
  const fit = () => document.querySelectorAll('.logo').forEach(node => {
    const box = node.parentElement;
    const limit = box.clientWidth;
    if (!limit) return;
    let size = parseFloat(getComputedStyle(node).fontSize);
    node.style.whiteSpace = 'nowrap';
    let guard = 60;
    while (node.scrollWidth > limit && size > 8 && guard-- > 0) {
      size -= Math.max(0.5, size * 0.04);
      node.style.fontSize = size + 'px';
    }
  });
  if (document.fonts && document.fonts.ready) { document.fonts.ready.then(fit); }
  fit();
})();
</script>
"""


@dataclass
class RenderOptions:
    """Что показывать поверх набора. При экспорте все флаги выключены."""

    show_guides: bool = False
    show_paper: bool = True
    show_block_borders: bool = False
    selected_block_id: Optional[str] = None
    fit_percents: dict[str, float] = field(default_factory=dict)
    for_export: bool = False
    crop_marks: bool = False


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


# ----------------------------------------------------------------- разметка текста

_BOLD = re.compile(r"\*\*(.+?)\*\*", re.S)
_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", re.S)


def inline_markup(text: str) -> str:
    """``**жирный**`` и ``*курсив*`` — минимальное форматирование из ТЗ, п. 4.4."""
    out = esc(text)
    out = _BOLD.sub(r"<b>\1</b>", out)
    out = _ITALIC.sub(r"<i>\1</i>", out)
    return out


def split_blocks(body: str) -> list[tuple[str, str]]:
    """Делит тело статьи на абзацы, подзаголовки (``## ``) и врезки (``> ``)."""
    result: list[tuple[str, str]] = []
    for chunk in re.split(r"\n\s*\n", (body or "").strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("## "):
            result.append(("subhead", chunk[3:].strip()))
        elif chunk.startswith("> "):
            result.append(("quote", chunk[2:].strip()))
        else:
            result.append(("para", re.sub(r"\s*\n\s*", " ", chunk)))
    return result


def _drop_cap(paragraph: str, small_caps: bool) -> str:
    """Первая буква — буквица, дальше первые слова капителью (как в макете)."""
    stripped = paragraph.lstrip()
    if not stripped:
        return ""
    first, rest = stripped[0], stripped[1:]
    opening, tail = "", rest
    if small_caps:
        match = re.match(r"^(.{8,40}?[,.;:—])\s", rest)
        if match:
            opening, tail = match.group(1), rest[match.end(1):]
        else:
            words = rest.split(" ")
            opening, tail = " ".join(words[:4]), " ".join(words[4:])
            if tail:
                tail = " " + tail
    return (
        f'<span class="dropcap">{esc(first)}</span>'
        f'<span class="smallcaps">{inline_markup(opening)}</span>'
        f"{inline_markup(tail)}"
    )


# ------------------------------------------------------------------- изображения


def image_css_filter(image: ImageRef) -> str:
    return {
        "halftone": "filter:grayscale(1) contrast(1.45) brightness(1.05)",
        "sepia": "filter:sepia(.75) contrast(1.1) saturate(.9)",
        "bw": "filter:grayscale(1) contrast(1.15)",
        "none": "",
    }.get(image.filter, "")


def image_html(image: Optional[ImageRef], project_dir: Optional[pathlib.Path], height: int) -> str:
    """Снимок в блоке: либо файл пользователя, либо полутоновый плейсхолдер."""
    if image is None:
        return ""
    height = int(image.height_px or height)
    inner: str
    if image.path and project_dir is not None and (project_dir / image.path).exists():
        url = (project_dir / image.path).resolve().as_uri()
        position = f"{image.focus_x * 100:.0f}% {image.focus_y * 100:.0f}%"
        inner = (
            f'<div class="photo" style="height:{height}px">'
            f'<img src="{url}" style="object-position:{position};transform:scale({image.scale});'
            f'{image_css_filter(image)}">'
            + ('<div class="screen"></div>' if image.filter == "halftone" else "")
            + "</div>"
        )
    else:
        millimetres = f"{int(height * 0.7)} × {int(height * 0.48)} мм"
        inner = (
            f'<div class="photo placeholder" style="height:{height}px">'
            f"ФОТО · {millimetres}</div>"
        )
    caption = ""
    if image.caption:
        caption = (
            '<div class="caption"><span class="caption-prefix">'
            f"{esc(image.caption_prefix)} </span>{inline_markup(image.caption)}</div>"
        )
    return f'<figure class="figure">{inner}{caption}</figure>'


# ------------------------------------------------------------------------ модули


def module_html(
    module: ModuleData, project_dir: Optional[pathlib.Path], for_export: bool = False
) -> str:
    title = (
        f'<div class="mod-title">{esc(module.title)}</div>' if module.title else ""
    )
    hint = "" if for_export else '<div class="mod-hint">заполните в панели «Блок»</div>'
    if module.kind == "rates":
        filled = [row for row in module.rows if any(cell.strip() for cell in row)]
        rows = "".join(
            f'<div class="rate"><span>{esc(row[0])}</span>'
            f'<span>{esc(row[1] if len(row) > 1 else "")}</span></div>'
            for row in filled
        )
        return f'<div class="mod mod-rates">{title}{rows or hint}</div>'
    if module.kind == "quote":
        attribution = (
            f'<div class="quote-attr">{esc(module.attribution)}</div>' if module.attribution else ""
        )
        body = f'<div class="quote-text">{inline_markup(module.text)}</div>' if module.text else hint
        return f'<div class="mod mod-quote">{body}{attribution}</div>'
    if module.kind == "photo":
        return f'<div class="mod mod-photo">{image_html(module.image, project_dir, 64)}</div>'
    body = f'<div class="mod-text">{inline_markup(module.text)}</div>' if module.text else hint
    classes = "mod mod-framed" if module.framed else "mod"
    if module.kind == "ad":
        classes += " mod-ad"
    return f'<div class="{classes}">{title}{body}</div>'


# ------------------------------------------------------------------------- блоки


def _article_html(
    article: Article,
    block: Block,
    typography: Typography,
    style: Style,
    project_dir: Optional[pathlib.Path],
) -> str:
    headline_px = typography.px("lead_headline_pt") * block.headline_scale
    parts: list[str] = []
    if article.rubric:
        parts.append(f'<div class="rubric">{esc(article.rubric)}</div>')
    title = article.title.upper() if style.uppercase_headlines else article.title
    parts.append(
        f'<h1 class="headline" style="font-size:{headline_px:.1f}px">{inline_markup(title)}</h1>'
    )
    if article.subtitle:
        parts.append(f'<div class="lead">{inline_markup(article.subtitle)}</div>')
    byline = " · ".join(item for item in (article.author, article.place_time) if item)
    if byline:
        parts.append(
            '<div class="byline"><span class="hair"></span>'
            f'<span class="byline-text">{esc(byline.upper())}</span><span class="hair"></span></div>'
        )

    chunks = split_blocks(article.body)
    body_parts: list[str] = []
    figure = image_html(article.image, project_dir, 96) if article.image else ""
    for index, (kind, text) in enumerate(chunks):
        if kind == "subhead":
            body_parts.append(f'<div class="subhead">{esc(text)}</div>')
        elif kind == "quote":
            body_parts.append(f'<div class="inset-quote">{inline_markup(text)}</div>')
        elif index == 0 and block.drop_cap and article.drop_cap:
            body_parts.append(
                f'<p class="first">{_drop_cap(text, article.small_caps_opening)}</p>'
            )
        else:
            body_parts.append(f"<p>{inline_markup(text)}</p>")
        if figure and index == min(1, len(chunks) - 1):
            body_parts.append(figure)
            figure = ""
    if figure:
        body_parts.insert(0, figure)
    if article.continued_on:
        body_parts.append(
            f'<div class="jump">ПРОДОЛЖЕНИЕ НА СТР. {article.continued_on} &#9656;</div>'
        )

    column_style = (
        f"column-count:{max(1, block.columns)};column-gap:14px;"
        + ("column-rule:1px solid var(--rule);" if block.column_rules and style.column_rules else "")
        + f"text-align:{'justify' if block.align == 'justify' else block.align};"
        + f"hyphens:{'auto' if block.hyphens else 'manual'};"
    )
    parts.append(
        f'<div class="body js-fit" data-fit="{block.id}" style="{column_style}">'
        + "".join(body_parts)
        + "</div>"
    )
    return "".join(parts)


def _block_html(
    block: Block,
    project: Project,
    options: RenderOptions,
    project_dir: Optional[pathlib.Path],
) -> str:
    styles = [f"flex:{block.weight if block.fixed_width is None else '0 0 auto'}"]
    if block.fixed_width is not None:
        styles.append(f"width:{block.fixed_width:.1f}px")
    if block.border_left:
        styles.append("border-left:1px solid var(--ink);padding-left:14px")
    if block.border_top:
        styles.append(f"border-top:{block.border_top}px solid var(--ink);padding-top:8px")

    classes = ["block"]
    selected = options.selected_block_id == block.id and not options.for_export
    if selected:
        classes.append("selected")
    if options.show_block_borders and not options.for_export:
        classes.append("outlined")

    badge = ""
    if selected:
        percent = options.fit_percents.get(block.id)
        meta = f"{block.label.upper()} · {block.columns} КОЛ."
        if percent is not None:
            meta += f" · {percent:.0f} %"
        badge = f'<div class="badge">{esc(meta)}</div>'

    article = project.article(block.article_id)
    if article is not None:
        inner = _article_html(article, block, project.typography, project.style, project_dir)
    elif block.modules:
        inner = (
            f'<div class="modules js-fit" data-fit="{block.id}">'
            + "".join(
                module_html(module, project_dir, options.for_export) for module in block.modules
            )
            + "</div>"
        )
    else:
        inner = (
            f'<div class="empty-block js-fit" data-fit="{block.id}">'
            f'<span>{esc(block.label)}</span></div>'
            if not options.for_export
            else '<div class="empty-block-export"></div>'
        )
    return (
        f'<div class="{" ".join(classes)}" data-block="{block.id}" style="{";".join(styles)}">'
        f"{badge}{inner}</div>"
    )


# -------------------------------------------------------------------------- шапка


def masthead_html(project: Project, page: Page, options_for_export: bool = False) -> str:
    brand: Brand = project.brand
    issue = project.issue
    if not page.show_masthead:
        running = f"{issue.title} · № {issue.number} · {issue.date}"
        return f'<div class="running-head">{esc(running.upper())}</div>'

    def join(*parts: str) -> str:
        return " · ".join(part for part in parts if part.strip())

    left = join(f"№ {issue.number}" if issue.number.strip() else "", issue.year_line)
    middle = join(issue.city, issue.date)
    right = f"ЦЕНА {issue.price}" if issue.price.strip() else ""
    service = ""
    if any((left, middle, right)):
        service = (
            f'<div class="service"><div>{esc(left.upper())}</div>'
            f"<div>{esc(middle.upper())}</div><div>{esc(right.upper())}</div></div>"
        )

    def side(text: str) -> str:
        head, *rest = (text or "").split("|")
        middle = f'<span class="side-strong">{esc(rest[0])}</span>' if rest else ""
        tail = esc(rest[1]) if len(rest) > 1 else ""
        return f'<div class="side">{esc(head)}<br>{middle}<br>{tail}</div>'

    logo_text = brand.display_name
    placeholder = not logo_text.strip()
    if placeholder:
        logo_text = "" if options_for_export else "НАЗВАНИЕ ИЗДАНИЯ"
    logo_font = fonts.resolve_for_text(brand.logo_font, logo_text)
    logo_size = brand.logo_size_pt * 96 / 72
    tracking = brand.tracking_permille / 1000
    superline = (
        f'<div class="superline" style="letter-spacing:{tracking * 12:.3f}em;'
        f'text-indent:{tracking * 12:.3f}em">{esc(brand.superline.upper())}</div>'
        if brand.superline_enabled and brand.superline
        else ""
    )
    logo_class = "logo" + (" logo-framed" if brand.logo_font_preset == "framed" else "")
    if placeholder:
        logo_class += " logo-placeholder"
    logo = (
        f'<div class="{logo_class}" style="font-family:\'{logo_font}\',serif;'
        f"font-size:{logo_size:.1f}px;letter-spacing:{tracking:.3f}em;"
        f'text-indent:{tracking:.3f}em">{esc(logo_text)}</div>'
    )
    motto = (
        f'<div class="motto">{esc(brand.motto)}</div>'
        if brand.motto_enabled and brand.motto
        else ""
    )

    if brand.rules_style == "single":
        rules = '<div class="rule" style="height:1px"></div>'
    elif brand.rules_style == "ornament":
        rules = (
            '<div class="rule" style="height:1px"></div>'
            '<div class="ornament">✦ ✦ ✦</div>'
            '<div class="rule" style="height:1px"></div>'
        )
    else:
        rules = (
            f'<div class="rule" style="height:{project.style.masthead_rule_weight}px"></div>'
            '<div class="rule" style="height:1px;margin-top:2.5px"></div>'
        )

    rubricator = ""
    if brand.rubricator:
        items = '<span class="diamond">✦</span>'.join(
            f"<span>{esc(item.upper())}</span>" for item in brand.rubricator
        )
        rubricator = f'<div class="rubricator">{items}</div>'

    frame_class = {
        "double_rule": "masthead",
        "ornament": "masthead masthead-framed",
        "none": "masthead masthead-plain",
    }.get(project.style.masthead_frame, "masthead")

    return (
        f'<header class="{frame_class}">{service}'
        f'<div class="logo-grid">{side(issue.masthead_left)}'
        f'<div class="logo-box">{superline}{logo}</div>{side(issue.masthead_right)}</div>'
        f"{motto}{rules}{rubricator}</header>"
    )


def folio_html(project: Project, page_index: int) -> str:
    issue = project.issue
    return (
        '<div class="folio">'
        f"<div>{esc(issue.title.upper())} · № {esc(issue.number)}</div>"
        f"<div>— {page_index + 1} —</div>"
        f"<div>{esc(issue.date.upper())}</div></div>"
    )


# --------------------------------------------------------------------------- CSS


def sheet_css(project: Project, options: RenderOptions) -> str:
    style: Style = project.style
    typo: Typography = project.typography
    body_px = typo.px("body_pt")
    heading = fonts.resolve_for_text(typo.heading_font, project.issue.title)
    return f"""
:root{{
  --paper:{style.paper_color};--ink:{style.ink_color};--body-ink:{style.body_ink};
  --soft:{style.soft_ink};--faint:{style.faint_ink};--rule:{style.rule_color};
  --accent-ink:{style.accent_ink};
}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:#101112}}
.sheet{{position:relative;width:{SHEET_WIDTH}px;height:{SHEET_HEIGHT}px;background:var(--paper);
  overflow:hidden;font-kerning:normal;text-rendering:optimizeLegibility}}
.inner{{position:absolute;inset:0;padding:{MARGIN_V}px {MARGIN_H}px;display:flex;flex-direction:column;
  {'text-shadow:0 0 .45px rgba(20,16,12,.55);' if style.ink_spread else ''}}}
.service{{display:flex;justify-content:space-between;align-items:baseline;
  font:400 10px '{typo.caption_font}',sans-serif;color:#453b2e;letter-spacing:.14em;
  padding-bottom:4px;border-bottom:1px solid #6d6250}}
.logo-grid{{display:grid;grid-template-columns:112px 1fr 112px;align-items:center;gap:14px;padding:12px 0 8px}}
.side{{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);padding:5px 0;
  font:400 8.5px/1.5 '{typo.caption_font}',sans-serif;letter-spacing:.08em;color:var(--soft);text-align:center}}
.side-strong{{font-size:11px;letter-spacing:.04em}}
.logo-box{{text-align:center;min-width:0}}
.superline{{font:400 13px/1 '{heading}',serif;color:#2a231b}}
.logo{{font-weight:700;line-height:.98;color:var(--ink);white-space:nowrap;margin-top:2px}}
.logo-framed{{border:2px solid var(--ink);padding:4px 10px;display:inline-block}}
.motto{{font:italic 400 12.5px/1.2 '{heading}',serif;color:var(--soft);text-align:center;padding-bottom:9px}}
.rule{{background:var(--ink)}}
.ornament{{text-align:center;font:400 9px '{typo.caption_font}',sans-serif;color:var(--soft);
  letter-spacing:.4em;padding:2px 0}}
.rubricator{{display:flex;justify-content:center;gap:22px;font:400 9px '{typo.caption_font}',sans-serif;
  letter-spacing:.2em;color:var(--soft);padding:6px 0;border-bottom:1px solid var(--ink)}}
.diamond{{color:#8d8271}}
.masthead-plain .rubricator{{border-bottom:none}}
.masthead-framed{{border:2px double var(--ink);padding:8px 10px}}
.running-head{{display:flex;justify-content:space-between;font:400 9px '{typo.caption_font}',sans-serif;
  letter-spacing:.18em;color:var(--faint);border-bottom:1px solid var(--ink);padding-bottom:5px}}
.stack{{flex:1;display:flex;flex-direction:column;min-height:0;padding-top:12px;gap:10px}}
.row{{display:flex;min-height:0}}
.block{{position:relative;display:flex;flex-direction:column;min-width:0;min-height:0;overflow:hidden}}
.block.selected{{outline:1.5px solid {ACCENT};outline-offset:6px}}
.block.outlined{{outline:1px dashed rgba(192,91,66,.5);outline-offset:3px}}
.badge{{position:absolute;top:0;right:0;z-index:2;background:{ACCENT};color:#fff;
  font:500 9px 'IBM Plex Sans',sans-serif;padding:3px 7px;letter-spacing:.06em;white-space:nowrap}}
.rubric{{font:400 10px '{typo.caption_font}',sans-serif;letter-spacing:.2em;color:var(--accent-ink);
  border-bottom:1px solid #b8ae9b;padding-bottom:4px;margin-bottom:8px}}
{'.rubric{background:var(--ink);color:var(--paper);padding:3px 6px;border:none;display:inline-block}' if style.invert_rubrics else ''}
.headline{{font:700 38px/1.04 '{heading}',serif;color:var(--ink);margin:0}}
.lead{{font:italic 400 15px/1.35 '{heading}',serif;color:var(--soft);margin-top:8px;
  border-bottom:1px solid #b8ae9b;padding-bottom:8px}}
.byline{{display:flex;align-items:center;gap:8px;padding:6px 0}}
.hair{{height:1px;flex:1;background:var(--rule)}}
.byline-text{{font:400 9px '{typo.caption_font}',sans-serif;letter-spacing:.16em;color:var(--faint)}}
.body{{flex:1;min-height:0;overflow:hidden;font:400 {body_px}px/{typo.leading} '{typo.body_font}',serif;
  color:var(--body-ink)}}
.body p{{margin:0;text-indent:1.1em}}
.body p.first{{text-indent:0}}
.dropcap{{float:left;font:700 {body_px * 4:.0f}px/0.82 '{heading}',serif;padding:3px 6px 0 0;color:var(--ink)}}
.smallcaps{{font-variant:small-caps;letter-spacing:.03em}}
.subhead{{font:700 10px '{typo.caption_font}',sans-serif;letter-spacing:.14em;color:var(--ink);
  margin:7px 0 3px;text-indent:0}}
.inset-quote{{font:italic 700 14px/1.3 '{heading}',serif;color:var(--ink);margin:7px 0;
  padding:6px 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);text-indent:0;
  break-inside:avoid}}
.figure{{margin:8px 0;break-inside:avoid}}
.photo{{position:relative;overflow:hidden;background:{HALFTONE}}}
.photo img{{width:100%;height:100%;object-fit:cover;display:block}}
.photo .screen{{position:absolute;inset:0;mix-blend-mode:multiply;opacity:.55;
  background:radial-gradient(circle at 50% 50%,#000 0 28%,transparent 30%);background-size:3px 3px}}
.photo.placeholder{{display:flex;align-items:center;justify-content:center;
  font:400 9px 'IBM Plex Mono',monospace;color:#6b6354;letter-spacing:.04em}}
.caption{{border-top:1px solid var(--ink);margin-top:3px;padding-top:3px;
  font:italic 400 9.5px/1.4 '{typo.body_font}',serif;color:#3f372b;text-indent:0}}
.caption-prefix{{font-style:normal;font-weight:700;font-family:'{typo.caption_font}',sans-serif;
  letter-spacing:.1em;font-size:8.5px}}
.jump{{border-top:1px solid var(--ink);margin-top:6px;padding-top:4px;text-indent:0;
  font:400 10px '{typo.caption_font}',sans-serif;letter-spacing:.1em;color:var(--accent-ink)}}
.modules{{flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column;gap:10px}}
.mod-title{{font:700 10px '{typo.caption_font}',sans-serif;letter-spacing:.16em;color:var(--ink);
  margin-bottom:4px}}
.mod-text{{font:400 10.5px/1.5 '{typo.body_font}',serif;color:var(--body-ink)}}
.mod-framed{{border:1px solid var(--ink);padding:8px}}
.mod-framed .mod-title{{text-align:center;border-bottom:1px solid var(--ink);padding-bottom:4px;margin-bottom:6px}}
.mod-ad{{border-width:2px;text-align:center}}
.mod-rates{{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);padding:6px 0}}
.rate{{display:flex;justify-content:space-between;font:400 10.5px/1.7 '{typo.body_font}',serif;
  color:var(--body-ink)}}
.mod-quote{{padding:8px 0;border-bottom:1px solid #b8ae9b}}
.quote-text{{font:italic 700 14px/1.3 '{heading}',serif;color:var(--ink)}}
.quote-attr{{font:400 9px '{typo.caption_font}',sans-serif;letter-spacing:.12em;color:var(--faint);margin-top:5px}}
.mod-photo{{margin-top:auto}}
.mod-hint{{font:italic 400 10px/1.4 '{typo.body_font}',serif;color:#8a8172}}
.logo-placeholder{{color:#9b9182}}
.empty-block{{flex:1;display:flex;align-items:center;justify-content:center;
  border:1px dashed rgba(90,81,69,.55);font:400 10px 'IBM Plex Mono',monospace;color:#6b6354;
  letter-spacing:.06em;text-align:center;padding:8px}}
.empty-block-export{{flex:1}}
.folio{{border-top:1px solid var(--ink);margin-top:8px;padding-top:5px;display:flex;
  justify-content:space-between;font:400 8.5px '{typo.caption_font}',sans-serif;letter-spacing:.16em;
  color:var(--faint)}}
.guides{{position:absolute;inset:0;pointer-events:none}}
.crop-marks{{position:absolute;inset:0;pointer-events:none}}
.crop-marks div{{position:absolute;background:#15120e}}
"""


def guides_html(project: Project) -> str:
    width = SHEET_WIDTH - MARGIN_H * 2
    columns = max(1, project.grid_columns)
    gutter = project.grid_gutter_mm * 96 / 25.4
    step = (width + gutter) / columns
    return (
        f'<div class="guides"><div style="position:absolute;left:{MARGIN_H}px;right:{MARGIN_H}px;'
        f"top:{MARGIN_V}px;bottom:{MARGIN_V}px;background:repeating-linear-gradient(to right,"
        f"rgba(192,91,66,.5) 0 1px,rgba(192,91,66,0) 1px {step:.2f}px)\"></div></div>"
    )


def crop_marks_html() -> str:
    marks = []
    for x in (0, SHEET_WIDTH - 12):
        for y in (0, SHEET_HEIGHT - 12):
            marks.append(f'<div style="left:{x}px;top:{y + 6}px;width:12px;height:1px"></div>')
            marks.append(f'<div style="left:{x + 6}px;top:{y}px;width:1px;height:12px"></div>')
    return f'<div class="crop-marks">{"".join(marks)}</div>'


# ------------------------------------------------------------------------- сборка


def page_body_html(
    project: Project,
    page_index: int,
    options: RenderOptions,
    project_dir: Optional[pathlib.Path] = None,
) -> str:
    page = project.page(page_index)
    rows_html = []
    for row in page.rows:
        style = [f"gap:{row.gap}px"]
        if row.fixed_height is not None:
            style.append(f"flex:0 0 {row.fixed_height:.1f}px")
        else:
            style.append(f"flex:{row.weight}")
        blocks = "".join(_block_html(block, project, options, project_dir) for block in row.blocks)
        rows_html.append(f'<div class="row" data-row="{row.id}" style="{";".join(style)}">{blocks}</div>')

    layers = ""
    if options.show_guides and not options.for_export:
        layers += guides_html(project)
    if options.show_paper:
        aging = aging_layer_css(project.paper)
        if aging:
            layers += f'<div style="{aging}"></div>'
    if options.crop_marks:
        layers += crop_marks_html()

    return (
        '<div class="sheet" id="sheet">'
        f'<div class="inner">{masthead_html(project, page, options.for_export)}'
        f'<div class="stack">{"".join(rows_html)}</div>'
        f"{folio_html(project, page_index)}</div>{layers}</div>"
    )


def page_document(
    project: Project,
    page_index: int,
    options: Optional[RenderOptions] = None,
    project_dir: Optional[pathlib.Path] = None,
) -> str:
    """Готовый HTML-документ одной полосы — то, что уходит в браузерный движок."""
    options = options or RenderOptions()
    return (
        "<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'><style>"
        + fonts.font_face_css()
        + sheet_css(project, options)
        + "</style></head><body>"
        + page_body_html(project, page_index, options, project_dir)
        + FIT_LOGO_JS
        + "</body></html>"
    )


def issue_document(
    project: Project,
    options: Optional[RenderOptions] = None,
    project_dir: Optional[pathlib.Path] = None,
    page_indexes: Optional[list[int]] = None,
) -> str:
    """Все полосы подряд — для печати выпуска одним PDF."""
    options = options or RenderOptions(for_export=True, show_paper=True)
    indexes = page_indexes if page_indexes is not None else list(range(len(project.pages)))
    sheets = "".join(
        page_body_html(project, index, options, project_dir) for index in indexes
    )
    print_css = (
        "@page{size:%dpx %dpx;margin:0}body{background:#fff}"
        ".sheet{page-break-after:always;break-after:page}"
        ".sheet:last-child{page-break-after:auto;break-after:auto}"
    ) % (SHEET_WIDTH, SHEET_HEIGHT)
    return (
        "<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'><style>"
        + fonts.font_face_css()
        + sheet_css(project, options)
        + print_css
        + "</style></head><body>"
        + sheets
        + FIT_LOGO_JS
        + "</body></html>"
    )
