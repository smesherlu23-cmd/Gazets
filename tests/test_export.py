"""Экспорт: имена файлов, выбор полос, оценка объёма."""

from __future__ import annotations

import pathlib

from pechatnya.presets import demo_project
from pechatnya.render.export import ExportSettings, dpi_label, planned_names, px_for_dpi, slugify


def test_slugify_transliterates_russian() -> None:
    assert slugify("Вечернiй Вестникъ") == "vechernij-vestnik"
    assert slugify("!!!") == "vypusk"


def test_scope_selects_pages() -> None:
    settings = ExportSettings(scope="all")
    assert settings.pages(4) == [0, 1, 2, 3]

    settings = ExportSettings(scope="current", current_page=2)
    assert settings.pages(4) == [2]

    settings = ExportSettings(scope="range", range_from=2, range_to=3)
    assert settings.pages(4) == [1, 2]

    settings = ExportSettings(scope="range", range_from=3, range_to=99)
    assert settings.pages(4) == [2, 3]


def test_file_names_follow_pattern() -> None:
    project = demo_project()

    names = planned_names(project, ExportSettings(fmt="png", scope="all",
                                                  directory=pathlib.Path(".")))
    assert names[0] == "vechernij-vestnik-14-p1.png"
    assert len(names) == len(project.pages)

    pdf = planned_names(project, ExportSettings(fmt="pdf", directory=pathlib.Path(".")))
    assert pdf == ["vechernij-vestnik-14.pdf"]

    stitched = planned_names(
        project, ExportSettings(fmt="png", stitch=True, directory=pathlib.Path("."))
    )
    assert stitched == ["vechernij-vestnik-14-all.png"]


def test_dpi_sizes() -> None:
    assert px_for_dpi(96) == (794, 1123)
    assert px_for_dpi(300) == (2481, 3509)
    assert dpi_label(150).startswith("150 dpi")
