"""Геометрия вёрстки: растягивание границ блоков и строк.

Границы тянутся мышью поверх картинки превью, поэтому проверяем сам пересчёт
весов: он должен перераспределять место, а не ломать полосу.
"""

from __future__ import annotations

from pechatnya.models import BlockFit
from pechatnya.ui.screen_layout import LayoutScreen
from tests.fixtures import sample_project
from tests.ui_harness import make_app


def _screen_with_metrics() -> tuple[LayoutScreen, object]:
    app = make_app(route="layout")
    app.set_project(sample_project())
    blocks = list(app.page_model.blocks())
    app.fits = {
        blocks[0].id: BlockFit(blocks[0].id, percent=80, x=38, y=207, width=506, height=716),
        blocks[1].id: BlockFit(blocks[1].id, percent=78, x=560, y=207, width=196, height=716),
        blocks[2].id: BlockFit(blocks[2].id, percent=92, x=38, y=933, width=231, height=132),
        blocks[3].id: BlockFit(blocks[3].id, percent=92, x=282, y=933, width=231, height=132),
        blocks[4].id: BlockFit(blocks[4].id, percent=68, x=525, y=933, width=231, height=132),
    }
    return LayoutScreen(app), app


def test_dragging_a_fixed_border_changes_width_in_pixels() -> None:
    screen, app = _screen_with_metrics()
    row = app.page_model.rows[0]
    sidebar = row.blocks[1]
    before = sidebar.fixed_width

    screen._resize_columns(row, 0, -60)  # тянем границу влево

    assert sidebar.fixed_width == before + 60
    assert sidebar.fixed_width > 60


def test_flexible_blocks_share_the_row() -> None:
    screen, app = _screen_with_metrics()
    row = app.page_model.rows[1]
    left, middle = row.blocks[0], row.blocks[1]
    total_before = left.weight + middle.weight

    screen._resize_columns(row, 0, 80)

    assert left.weight > middle.weight
    assert round(left.weight + middle.weight, 4) == round(total_before, 4)


def test_block_cannot_be_squeezed_to_nothing() -> None:
    screen, app = _screen_with_metrics()
    row = app.page_model.rows[1]
    left, middle = row.blocks[0], row.blocks[1]

    for _ in range(10):
        screen._resize_columns(row, 0, -500)

    assert left.weight > 0
    assert middle.weight > 0
    assert left.weight / (left.weight + middle.weight) >= 0.12


def test_row_border_moves_between_rows() -> None:
    screen, app = _screen_with_metrics()
    page = app.page_model
    bottom = page.rows[1]
    before = bottom.fixed_height

    screen._resize_rows(page, 0, 40)  # тянем границу вниз

    assert bottom.fixed_height == before - 40


def test_row_keeps_a_minimum_height() -> None:
    screen, app = _screen_with_metrics()
    page = app.page_model
    bottom = page.rows[1]

    for _ in range(10):
        screen._resize_rows(page, 0, 400)

    assert bottom.fixed_height >= 50


def test_overlay_has_zone_for_every_block_and_handles() -> None:
    screen, app = _screen_with_metrics()

    controls = screen._overlay_controls()

    # пять блоков + три вертикальные границы + одна горизонтальная
    assert len(controls) == 5 + 3 + 1


def test_overlay_scales_with_zoom() -> None:
    screen, app = _screen_with_metrics()
    app.zoom = 0.5
    first = screen._overlay_controls()[0]

    assert first.left == 38 * 0.5
    assert first.top == 207 * 0.5
