"""Каждый экран собирается и проходит проверку Flet.

Тест ловит то, что раньше находилось только глазами: неверные типы полей,
из-за которых Flet молча перестаёт обновлять панель, и падения в build().
"""

from __future__ import annotations

import pytest

from pechatnya.models import Article, Publication
from pechatnya.presets import make_module
from pechatnya.ui import (
    panels,
    screen_article,
    screen_export,
    screen_grid,
    screen_issue,
    screen_layout,
    screen_publication,
    screen_start,
)
from tests.fixtures import sample_project
from tests.ui_harness import check_controls, make_app

SIMPLE_SCREENS = {
    "start": screen_start.build,
    "issue": screen_issue.build,
    "grid": screen_grid.build,
    "publications": screen_publication.build,
}


@pytest.mark.parametrize("route", sorted(SIMPLE_SCREENS))
def test_screen_builds_and_validates(route: str) -> None:
    app = make_app(route=route)
    app.set_project(sample_project())

    control = SIMPLE_SCREENS[route](app)

    assert check_controls(control) > 5


def test_layout_screen_with_selection_and_overflow() -> None:
    from pechatnya.models import BlockFit

    app = make_app(route="layout")
    app.set_project(sample_project())
    blocks = list(app.page_model.blocks())
    app.fits = {
        blocks[0].id: BlockFit(blocks[0].id, percent=142.0, overflow_chars=640,
                               x=38, y=207, width=506, height=716),
        blocks[1].id: BlockFit(blocks[1].id, percent=78.0, x=560, y=207, width=196, height=716),
    }
    app.selected_block_id = blocks[0].id

    screen = screen_layout.LayoutScreen(app)
    control = screen.build()

    assert check_controls(control) > 20
    # зоны блоков, ручки границ и бейдж выделения кладутся поверх картинки
    assert len(screen.overlay.controls) >= 3


def test_panels_cover_every_tab() -> None:
    app = make_app(route="layout")
    app.set_project(sample_project())
    block = list(app.page_model.blocks())[0]
    app.selected_block_id = block.id

    for tab in ("block", "paper"):
        app.panel_tab = tab
        assert check_controls(panels.build(app)) > 5

    # блок с модулями — редакторы их содержимого
    module_block = list(app.page_model.blocks())[1]
    app.selected_block_id = module_block.id
    app.panel_tab = "block"
    assert check_controls(panels.build(app)) > 10


def test_article_editor_builds() -> None:
    app = make_app(route="article")
    app.set_project(sample_project())
    app.editing_article_id = app.project.articles[0].id

    screen = screen_article.ArticleScreen(app)

    assert check_controls(screen.build()) > 10


def test_article_editor_survives_missing_article() -> None:
    app = make_app(route="article")
    app.set_project(sample_project())
    app.editing_article_id = "нет такой статьи"

    screen = screen_article.ArticleScreen(app)

    assert check_controls(screen.build()) >= 1


def test_export_screen_builds_for_both_formats(tmp_path) -> None:
    app = make_app(route="export")
    app.set_project(sample_project())
    screen = screen_export.ExportScreen(app)
    screen.settings.directory = tmp_path

    for fmt in ("png", "pdf"):
        screen.settings.fmt = fmt
        assert check_controls(screen.build()) > 10


def test_empty_project_screens_do_not_crash() -> None:
    """Пустой выпуск — то, что видит пользователь при первом запуске."""
    app = make_app(route="layout")
    empty = app.project
    assert empty.articles == []

    screen = screen_layout.LayoutScreen(app)
    assert check_controls(screen.build()) > 10

    app.panel_tab = "block"
    assert check_controls(panels.build(app)) >= 1


def test_publication_editor_tabs() -> None:
    app = make_app(route="publications")
    app.editing_publication = Publication(name="Голос дока")

    for tab in ("logo", "sections", "design"):
        app.publication_tab = tab
        assert check_controls(screen_publication.build(app)) > 10


def test_block_panel_shows_continuation_controls() -> None:
    app = make_app(route="layout")
    app.set_project(sample_project())
    lead = app.project.articles[0]
    app.project.place_continuation(lead.id, 2, 900)

    app.selected_block_id = app.project.block_of(lead.id, part=0).id
    assert check_controls(panels.build(app)) > 10

    app.selected_block_id = app.project.block_of(lead.id, part=1).id
    assert check_controls(panels.build(app)) > 10


def test_added_module_and_article_render_in_panel() -> None:
    app = make_app(route="layout")
    app.set_project(sample_project())
    block = app.project.free_block_on(1)
    block.modules = [make_module(kind) for kind in ("ad", "rates", "quote", "photo")]
    block.kind = "module"
    app.current_page = 1
    app.selected_block_id = block.id

    assert check_controls(panels.build(app)) > 20

    app.project.articles.append(Article(title="Ещё материал"))
    assert check_controls(screen_layout.build_left_rail(app)) > 10
