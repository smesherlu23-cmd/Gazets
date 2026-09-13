"""Файлы приложения: проекты, библиотека брендов, пользовательские пресеты.

Проект — один JSON плюс папка ``<имя>.images`` рядом с ним (ТЗ, п. 4.8).
Служебные списки (недавние проекты, бренды, свои пресеты) лежат в профиле
пользователя и к проекту не привязаны.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import platform
import shutil
import uuid
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from .models import ImageRef, Project, Publication
from .serde import from_dict, to_dict

PROJECT_SUFFIX = ".pechatnya.json"


def app_dir() -> pathlib.Path:
    """Каталог настроек: %APPDATA%\\Pechatnya на Windows, ~/.pechatnya иначе."""
    if platform.system() == "Windows":
        base = pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home()))
        path = base / "Pechatnya"
    else:
        path = pathlib.Path(os.environ.get("PECHATNYA_HOME", pathlib.Path.home() / ".pechatnya"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir() -> pathlib.Path:
    """Куда по умолчанию кладём проекты и экспорт."""
    home = pathlib.Path.home()
    for name in ("Documents", "Документы"):
        candidate = home / name
        if candidate.exists():
            target = candidate / "Печатня"
            target.mkdir(parents=True, exist_ok=True)
            return target
    target = home / "Печатня"
    target.mkdir(parents=True, exist_ok=True)
    return target


def images_dir_for(path: pathlib.Path) -> pathlib.Path:
    stem = path.name
    for suffix in (PROJECT_SUFFIX, ".json"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return path.parent / f"{stem}.images"


def _read_json(path: pathlib.Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ------------------------------------------------------------------- проекты


def project_images(project: Project) -> Iterator[ImageRef]:
    """Все картинки выпуска: в статьях и в модулях полос."""
    for article in project.articles:
        if article.image is not None:
            yield article.image
    for page in project.pages:
        for block in page.blocks():
            for module in block.modules:
                if module.image is not None:
                    yield module.image


def relocate_images(
    project: Project, target_path: pathlib.Path, source_dir: Optional[pathlib.Path] = None
) -> int:
    """Собирает картинки в папку проекта и делает пути относительными.

    Нужно в двух случаях: снимок вставили до первого сохранения (он лежит в
    профиле по абсолютному пути) и проект сохранили в другое место («сохранить
    как») — иначе файл уедет без картинок.
    """
    target_dir = images_dir_for(target_path)
    base = pathlib.Path(source_dir) if source_dir else target_path.parent
    moved = 0
    for image in project_images(project):
        if not image.path:
            continue
        current = pathlib.Path(image.path)
        if not current.is_absolute():
            current = base / current
        if not current.exists():
            continue  # файл потеряли — на полосе останется плейсхолдер
        if current.parent.resolve() != target_dir.resolve():
            target_dir.mkdir(parents=True, exist_ok=True)
            destination = target_dir / current.name
            if destination.exists() and destination.stat().st_size != current.stat().st_size:
                destination = target_dir / f"{current.stem}-{uuid.uuid4().hex[:4]}{current.suffix}"
            if not destination.exists():
                shutil.copy2(current, destination)
            current = destination
            moved += 1
        image.path = os.path.relpath(current, target_path.parent).replace(os.sep, "/")
    return moved


def save_project(
    project: Project, path: pathlib.Path, source_dir: Optional[pathlib.Path] = None
) -> pathlib.Path:
    path = pathlib.Path(path)
    if path.suffix != ".json":
        path = path.with_name(path.name + PROJECT_SUFFIX)
    images_dir_for(path).mkdir(parents=True, exist_ok=True)
    relocate_images(project, path, source_dir)
    _write_json(path, project.to_json_dict())
    remember_recent(path, project)
    return path


def load_project(path: pathlib.Path) -> Project:
    data = _read_json(pathlib.Path(path), None)
    if data is None:
        raise OSError(f"не удалось прочитать проект: {path}")
    project = Project.from_json_dict(data)
    # оформление берём из библиотеки: правка издания видна во всех его номерах,
    # а если издания в библиотеке нет (файл принесли с другой машины) — остаётся
    # снимок, сохранённый внутри проекта.
    known = publication(project.publication_id) if project.publication_id else None
    if known is not None:
        project.inherit(known)
    remember_recent(pathlib.Path(path), project)
    return project


def autosave_path(path: Optional[pathlib.Path]) -> pathlib.Path:
    if path is None:
        return app_dir() / "autosave" / "unsaved.pechatnya.json"
    return app_dir() / "autosave" / path.name


def autosave(project: Project, path: Optional[pathlib.Path]) -> pathlib.Path:
    target = autosave_path(path)
    _write_json(target, project.to_json_dict())
    return target


def import_image(source: pathlib.Path, project_path: Optional[pathlib.Path]) -> str:
    """Копирует картинку в папку проекта и возвращает путь относительно проекта."""
    source = pathlib.Path(source)
    if project_path is None:
        target_dir = app_dir() / "unsaved.images"
    else:
        target_dir = images_dir_for(project_path)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists() and target.stat().st_size != source.stat().st_size:
        target = target_dir / f"{source.stem}-{uuid.uuid4().hex[:4]}{source.suffix}"
    if not target.exists():
        shutil.copy2(source, target)
    if project_path is None:
        return str(target)
    return os.path.relpath(target, project_path.parent).replace(os.sep, "/")


# -------------------------------------------------------------- недавние файлы


@dataclass
class RecentEntry:
    path: str
    title: str = ""
    issue: str = ""
    number: str = ""
    date: str = ""
    modified: str = ""
    pages: int = 0
    publication_id: str = ""

    @property
    def exists(self) -> bool:
        return pathlib.Path(self.path).exists()


def recents_file() -> pathlib.Path:
    return app_dir() / "recent.json"


def recent_projects(limit: int = 24) -> list[RecentEntry]:
    raw = _read_json(recents_file(), [])
    entries = [from_dict(RecentEntry, item) for item in raw if isinstance(item, dict)]
    return [entry for entry in entries if entry.exists][:limit]


def remember_recent(path: pathlib.Path, project: Project) -> None:
    entries = [entry for entry in recent_projects(99) if entry.path != str(path)]
    entries.insert(
        0,
        RecentEntry(
            path=str(path),
            title=project.title,
            issue=project.issue.title,
            number=project.issue.number,
            date=project.issue.date,
            modified=dt.datetime.now().isoformat(timespec="seconds"),
            pages=len(project.pages),
            publication_id=project.publication_id,
        ),
    )
    _write_json(recents_file(), [to_dict(entry) for entry in entries[:24]])


def forget_recent(path: str) -> None:
    entries = [entry for entry in recent_projects(99) if entry.path != path]
    _write_json(recents_file(), [to_dict(entry) for entry in entries])


# ---------------------------------------------------------- библиотека изданий


def publications_file() -> pathlib.Path:
    return app_dir() / "publications.json"


def publications() -> list[Publication]:
    """Все издания пользователя, свежие сверху."""
    raw = _read_json(publications_file(), [])
    items = [from_dict(Publication, item) for item in raw if isinstance(item, dict)]
    return sorted(items, key=lambda item: item.updated_at or item.created_at, reverse=True)


def publication(publication_id: str) -> Optional[Publication]:
    return next((item for item in publications() if item.id == publication_id), None)


def save_publication(item: Publication) -> Publication:
    item.updated_at = dt.datetime.now().isoformat(timespec="seconds")
    rest = [other for other in publications() if other.id != item.id]
    _write_json(publications_file(), [to_dict(entry) for entry in [item, *rest]])
    return item


def delete_publication(publication_id: str) -> None:
    rest = [item for item in publications() if item.id != publication_id]
    _write_json(publications_file(), [to_dict(item) for item in rest])


def issues_of_publication(publication_id: str) -> list["RecentEntry"]:
    """Сохранённые номера одного издания."""
    return [entry for entry in recent_projects(99) if entry.publication_id == publication_id]


# ---------------------------------------------------------------- выпуски серии


def issues_of_title(title: str) -> list[RecentEntry]:
    """Все сохранённые номера одного издания — для таблицы на экране 01."""
    return [entry for entry in recent_projects(99) if entry.issue == title]


def settings_file() -> pathlib.Path:
    return app_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    return _read_json(settings_file(), {})


def save_settings(data: dict[str, Any]) -> None:
    _write_json(settings_file(), data)
