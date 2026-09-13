"""Файлы проекта: сохранение, недавние, картинки, бренды."""

from __future__ import annotations

import pathlib

import pytest

from pechatnya import storage
from pechatnya.models import Publication
from tests.fixtures import sample_project


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("PECHATNYA_HOME", str(tmp_path / "профиль"))
    monkeypatch.setattr(storage, "app_dir", lambda: _ensure(tmp_path / "профиль"))
    yield


def _ensure(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_save_and_load_roundtrip(tmp_path) -> None:
    project = sample_project()

    path = storage.save_project(project, tmp_path / "vestnik-14")

    assert path.name == "vestnik-14.pechatnya.json"
    assert storage.images_dir_for(path).is_dir()

    restored = storage.load_project(path)
    assert restored.issue.number == project.issue.number
    assert len(restored.articles) == len(project.articles)


def test_recent_projects_listed_newest_first(tmp_path) -> None:
    first = sample_project()
    first.issue.number = "14"
    second = sample_project()
    second.issue.number = "15"
    second.title = "Вечернiй Вестникъ, № 15"

    storage.save_project(first, tmp_path / "n14")
    storage.save_project(second, tmp_path / "n15")

    recents = storage.recent_projects()
    assert recents[0].number == "15"
    assert len(storage.issues_of_title("Вечерний вестник")) == 2


def test_import_image_copies_into_project_folder(tmp_path) -> None:
    source = tmp_path / "снимокъ.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n")
    path = storage.save_project(sample_project(), tmp_path / "vestnik")

    relative = storage.import_image(source, path)

    assert relative == "vestnik.images/снимокъ.png"
    assert (path.parent / relative).read_bytes() == source.read_bytes()


def test_publications_library(tmp_path) -> None:
    item = Publication(name="Голос дока")

    storage.save_publication(item)

    assert [saved.display_name for saved in storage.publications()] == ["Голос дока"]
    assert storage.publication(item.id) is not None
    storage.delete_publication(item.id)
    assert storage.publications() == []


def test_project_picks_up_edited_publication(tmp_path) -> None:
    """Правка издания видна во всех его номерах при следующем открытии."""
    item = storage.save_publication(Publication(name="Вечерний вестник"))
    project = sample_project()
    project.inherit(item)
    path = storage.save_project(project, tmp_path / "n14")

    item.style.paper_color = "#e4ded0"
    item.brand.name_cyrillic = "ВЕСТНИК ДОКА"
    storage.save_publication(item)

    reopened = storage.load_project(path)
    assert reopened.style.paper_color == "#e4ded0"
    assert reopened.brand.name_cyrillic == "ВЕСТНИК ДОКА"
    assert len(reopened.articles) == len(project.articles)  # тексты и вёрстка на месте
