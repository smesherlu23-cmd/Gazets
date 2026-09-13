"""Сборка HTML полосы: разметка текста, шапка, слой состаривания."""

from __future__ import annotations

from pechatnya.models import Article, Paper
from pechatnya.presets import new_project
from tests.fixtures import sample_project
from pechatnya.render import paper as paper_layer
from pechatnya.render.html import (
    RenderOptions,
    inline_markup,
    issue_document,
    page_document,
    split_blocks,
)


def test_inline_markup_escapes_and_formats() -> None:
    assert inline_markup("**жирно** и *курсивъ*") == "<b>жирно</b> и <i>курсивъ</i>"
    assert inline_markup("<script>") == "&lt;script&gt;"


def test_split_blocks_recognises_structure() -> None:
    parsed = split_blocks("Первый абзацъ\n\n## ПОДЗАГОЛОВОКЪ\n\n> Цитата\n\nВторой абзацъ")

    assert [kind for kind, _ in parsed] == ["para", "subhead", "quote", "para"]
    assert parsed[1][1] == "ПОДЗАГОЛОВОКЪ"


def test_page_document_contains_masthead_and_fonts() -> None:
    project = sample_project()

    html = page_document(project, 0)

    assert "@font-face" in html
    assert project.brand.display_name in html
    assert "ПРОДОЛЖЕНИЕ НА СТР. 3" in html
    assert 'data-fit=' in html  # крючки для замера вместимости
    assert "column-count:3" in html


def test_drop_cap_and_small_caps_only_when_enabled() -> None:
    project = new_project()
    article = Article(title="Проба", body="Ночью, около половины перваго, случилось вотъ что.")
    project.articles.append(article)
    block = next(project.pages[0].blocks())
    project.assign(article.id, block.id)

    with_cap = page_document(project, 0)
    assert 'class="dropcap"' in with_cap

    article.drop_cap = False
    assert 'class="dropcap"' not in page_document(project, 0)


def test_aging_layer_follows_checkboxes() -> None:
    full = Paper(enabled=True, intensity=100, folds=True, grain=True)
    assert paper_layer.aging_opacity(full) == 0.9
    background = paper_layer.aging_background(full)
    assert background.count("radial-gradient") == 4
    assert "repeating-linear-gradient" in background

    plain = Paper(enabled=True, yellowing=False, stains=False, unevenness=False)
    assert paper_layer.aging_background(plain) == ""

    assert paper_layer.aging_layer_css(Paper(enabled=False)) == ""


def test_export_document_has_page_break_per_sheet() -> None:
    project = sample_project()

    html = issue_document(project, RenderOptions(for_export=True), page_indexes=[0, 1, 2])

    assert html.count('class="sheet"') == 3
    assert "page-break-after" in html
    assert '<div class="guides">' not in html  # сетка колонок в экспорт не попадает


def test_guides_and_borders_only_in_preview() -> None:
    project = sample_project()

    preview = page_document(project, 0, RenderOptions(show_guides=True, show_block_borders=True))
    export = page_document(project, 0, RenderOptions(show_guides=True, for_export=True))

    assert 'class="guides"' in preview
    assert 'class="guides"' not in export


def test_continuation_splits_text_between_pages() -> None:
    """Остаток статьи печатается на другой полосе со ссылками в обе стороны."""
    project = sample_project()
    project.style.typography_polish = False  # сравниваем текст как набран
    lead = project.articles[0]
    split_at = 900

    project.place_continuation(lead.id, 2, split_at)
    first = page_document(project, 0)
    third = page_document(project, 2)

    assert "ПРОДОЛЖЕНИЕ НА СТР. 3" in first
    assert "НАЧАЛО НА СТР. 1" in third
    # текст поделён, а не продублирован (сравниваем куски внутри абзацев:
    # абзацы в HTML разложены по <p>, поэтому срез через перенос строки не ищем)
    head_fragment = lead.part_text(0).split("\n")[-1][-40:]
    tail_fragment = lead.part_text(1).split("\n")[0][:40]
    assert head_fragment in first and head_fragment not in third
    assert tail_fragment in third and tail_fragment not in first
    # лид, автор и снимок остаются в начале статьи
    assert lead.subtitle in first and lead.subtitle not in third
    assert 'class="dropcap"' in first and 'class="dropcap"' not in third


def test_dropping_continuation_returns_whole_text() -> None:
    project = sample_project()
    lead = project.articles[0]
    project.place_continuation(lead.id, 2, 900)

    project.drop_continuation(lead.id)

    assert lead.split_at is None
    assert lead.continued_on is None
    assert project.block_of(lead.id, part=1) is None
    assert lead.part_text(0) == lead.body
    assert "ПРОДОЛЖЕНИЕ НА СТР." not in page_document(project, 0)
