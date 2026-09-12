"""Файлы проекта: сохранение, недавние, картинки, бренды."""

from __future__ import annotations

import pathlib

import pytest

from pechatnya import storage
from pechatnya.models import Brand
from pechatnya.presets import demo_project


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("PECHATNYA_HOME", str(tmp_path / "профиль"))
    monkeypatch.setattr(storage, "app_dir", lambda: _ensure(tmp_path / "профиль"))
    yield


def _ensure(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_save_and_load_roundtrip(tmp_path) -> None:
    project = demo_project()

    path = storage.save_project(project, tmp_path / "vestnik-14")

    assert path.name == "vestnik-14.pechatnya.json"
    assert storage.images_dir_for(path).is_dir()

    restored = storage.load_project(path)
    assert restored.issue.number == project.issue.number
    assert len(restored.articles) == len(project.articles)


def test_recent_projects_listed_newest_first(tmp_path) -> None:
    first = demo_project()
    first.issue.number = "14"
    second = demo_project()
    second.issue.number = "15"
    second.title = "Вечернiй Вестникъ, № 15"

    storage.save_project(first, tmp_path / "n14")
    storage.save_project(second, tmp_path / "n15")

    recents = storage.recent_projects()
    assert recents[0].number == "15"
    assert len(storage.issues_of_title("Вечернiй Вестникъ")) == 2


def test_import_image_copies_into_project_folder(tmp_path) -> None:
    source = tmp_path / "снимокъ.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n")
    path = storage.save_project(demo_project(), tmp_path / "vestnik")

    relative = storage.import_image(source, path)

    assert relative == "vestnik.images/снимокъ.png"
    assert (path.parent / relative).read_bytes() == source.read_bytes()


def test_brands_library(tmp_path) -> None:
    brand = Brand(name_cyrillic="Голосъ дока")

    storage.save_brand(brand)

    assert [item.name_cyrillic for item in storage.saved_brands()] == ["Голосъ дока"]
    storage.delete_brand(brand.id)
    assert storage.saved_brands() == []
