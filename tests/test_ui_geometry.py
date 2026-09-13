"""Геометрия вёрстки: дерево блоков, растягивание границ, зоны поверх превью."""

from __future__ import annotations

from pechatnya.ui.screen_layout import LayoutScreen
from tests.fixtures import sample_project
from tests.ui_harness import fill_metrics, make_app


def _screen() -> tuple[LayoutScreen, object]:
    app = make_app(route="layout")
    app.set_project(sample_project())
    fill_metrics(app)
    return LayoutScreen(app), app


def test_overlay_covers_blocks_and_borders() -> None:
    screen, app = _screen()
    blocks = list(app.page_model.blocks())

    controls = screen._overlay_controls()

    # зона на каждый блок плюс ручка на каждый стык соседей
    joints = sum(
        max(0, len(frame.children) - 1) for frame in app.page_model.frames() if not frame.is_leaf
    )
    assert len(controls) == len(blocks) + joints
    assert joints >= 3


def test_overlay_scales_with_zoom() -> None:
    screen, app = _screen()
    app.zoom = 0.5
    first = screen._overlay_controls()[0]
    rect = app.fit_of(next(app.page_model.blocks()).id)

    assert first.left == rect.x * 0.5
    assert first.top == rect.y * 0.5


def test_dragging_a_border_moves_space_between_neighbours() -> None:
    screen, app = _screen()
    container = next(
        frame for frame in app.page_model.frames()
        if not frame.is_leaf and frame.direction == "row" and len(frame.children) > 1
    )
    left, right = container.children[0], container.children[1]
    total_before = left.weight + right.weight

    screen._resize_siblings(container, 0, 80)

    if right.fixed is not None:  # узкая колонка задана в пикселях
        assert right.fixed < 196.0
    else:
        assert left.weight > right.weight
        assert round(left.weight + right.weight, 4) == round(total_before, 4)


def test_fixed_column_keeps_a_minimum_width() -> None:
    screen, app = _screen()
    container = next(
        frame for frame in app.page_model.frames()
        if not frame.is_leaf and any(child.fixed for child in frame.children)
    )
    index = next(i for i, child in enumerate(container.children) if child.fixed is None)

    for _ in range(12):
        screen._resize_siblings(container, index, 400)

    assert all(child.fixed is None or child.fixed >= 40 for child in container.children)


def test_flexible_blocks_never_collapse() -> None:
    screen, app = _screen()
    container = next(
        frame for frame in app.page_model.frames()
        if not frame.is_leaf and sum(1 for child in frame.children if child.fixed is None) >= 2
    )
    flexible = [child for child in container.children if child.fixed is None]
    index = container.children.index(flexible[0])

    for _ in range(12):
        screen._resize_siblings(container, index, -500)

    assert all(child.weight > 0 for child in container.children)


def test_split_and_remove_rebuild_the_overlay() -> None:
    screen, app = _screen()
    block = next(app.page_model.blocks())
    before = len(list(app.page_model.blocks()))

    fresh = app.page_model.split_block(block.id, "column")
    fill_metrics(app)
    assert len(list(app.page_model.blocks())) == before + 1
    assert len(screen._overlay_controls()) > before

    app.page_model.remove_block(fresh.id)
    fill_metrics(app)
    assert len(list(app.page_model.blocks())) == before
