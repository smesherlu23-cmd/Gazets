"""Интеграцiя с движком рендера — пропускается, если браузера нет в системе."""

from __future__ import annotations

import pytest

from tests.fixtures import sample_project
from pechatnya.render.engine import engine, find_browser
from pechatnya.render.export import ExportSettings, export
from pechatnya.render.html import RenderOptions, page_document

pytestmark = pytest.mark.skipif(find_browser() is None, reason="нет Chrome/Chromium/Edge")


@pytest.fixture(scope="module")
def render_engine():
    current = engine()
    current.start()
    yield current


def test_png_render_has_sheet_size(tmp_path, render_engine) -> None:
    document = page_document(sample_project(), 0, RenderOptions(show_paper=True))

    path = render_engine.render_png(document, tmp_path / "page.png")

    assert path.stat().st_size > 10_000
    pillow = pytest.importorskip("PIL.Image")
    with pillow.open(path) as image:
        assert image.size == (794, 1123)


def test_measure_reports_fit_per_block(render_engine) -> None:
    project = sample_project()
    document = page_document(project, 0, RenderOptions())

    metrics = {item.id: item for item in render_engine.measure(document)}

    if not metrics:
        pytest.skip("движок работает в режиме CLI — замер недоступен")
    assert len(metrics) == len(list(project.pages[0].blocks()))
    lead = project.pages[0].rows[0].blocks[0]
    assert 0 < metrics[lead.id].percent < 100
    assert metrics[lead.id].overflow == 0


def test_overflow_is_detected(render_engine) -> None:
    project = sample_project()
    project.articles[0].body *= 3
    document = page_document(project, 0, RenderOptions())

    metrics = {item.id: item for item in render_engine.measure(document)}
    if not metrics:
        pytest.skip("движок работает в режиме CLI — замер недоступен")

    lead = project.pages[0].rows[0].blocks[0]
    assert metrics[lead.id].percent > 100
    assert metrics[lead.id].overflow > 0


def test_pdf_export_contains_all_pages(tmp_path, render_engine) -> None:
    project = sample_project()

    result = export(project, ExportSettings(fmt="pdf", scope="all", directory=tmp_path))

    data = result.files[0].read_bytes()
    assert data.startswith(b"%PDF")
    assert data.count(b"/Type /Page") - data.count(b"/Type /Pages") == len(project.pages)


def test_png_export_names_and_dpi(tmp_path, render_engine) -> None:
    project = sample_project()

    result = export(
        project, ExportSettings(fmt="png", scope="current", dpi=96, directory=tmp_path)
    )

    assert [path.name for path in result.files] == ["vechernij-vestnik-14-p1.png"]
    pillow = pytest.importorskip("PIL.Image")
    with pillow.open(result.files[0]) as image:
        assert image.size == (794, 1123)


def test_split_point_is_picked_so_the_first_part_fits(render_engine) -> None:
    """Подбор переноса: начало статьи должно влезать в блок, остаток — уезжать."""
    from pechatnya.render.split import fit_split_point, measure_block

    project = sample_project()
    lead = project.articles[0]
    lead.body = lead.body * 2  # заведомо не помещается
    block = project.block_of(lead.id, part=0)

    if not render_engine.can_measure:
        pytest.skip("движок работает в режиме CLI — замер недоступен")

    point = fit_split_point(project, lead.id, render_engine=render_engine)

    assert point is not None and 0 < point < len(lead.body)
    lead.split_at = point
    assert measure_block(project, 0, block.id, None, render_engine) <= 100
    assert lead.part_text(1).strip()  # остаток не пустой
    # разрыв приходится на пробел — слово не разорвано
    assert lead.body[point].isspace() or point == len(lead.body)


def test_no_split_needed_for_short_article(render_engine) -> None:
    from pechatnya.render.split import fit_split_point

    project = sample_project()
    short = project.articles[1]
    if not render_engine.can_measure:
        pytest.skip("движок работает в режиме CLI — замер недоступен")

    assert fit_split_point(project, short.id, render_engine=render_engine) is None
