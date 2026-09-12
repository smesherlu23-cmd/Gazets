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
from dataclasses import dataclass, field
from typing import Any, Optional

from .models import Brand, Project, Style, Typography
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


def save_project(project: Project, path: pathlib.Path) -> pathlib.Path:
    path = pathlib.Path(path)
    if path.suffix != ".json":
        path = path.with_name(path.name + PROJECT_SUFFIX)
    images_dir_for(path).mkdir(parents=True, exist_ok=True)
    _write_json(path, project.to_json_dict())
    remember_recent(path, project)
    return path


def load_project(path: pathlib.Path) -> Project:
    data = _read_json(pathlib.Path(path), None)
    if data is None:
        raise OSError(f"не удалось прочитать проект: {path}")
    project = Project.from_json_dict(data)
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
        ),
    )
    _write_json(recents_file(), [to_dict(entry) for entry in entries[:24]])


def forget_recent(path: str) -> None:
    entries = [entry for entry in recent_projects(99) if entry.path != path]
    _write_json(recents_file(), [to_dict(entry) for entry in entries])


# ------------------------------------------------------------ бренды и пресеты


def brands_file() -> pathlib.Path:
    return app_dir() / "brands.json"


def saved_brands() -> list[Brand]:
    raw = _read_json(brands_file(), [])
    return [from_dict(Brand, item) for item in raw if isinstance(item, dict)]


def save_brand(brand: Brand) -> None:
    brands = [item for item in saved_brands() if item.id != brand.id]
    brands.insert(0, brand)
    _write_json(brands_file(), [to_dict(item) for item in brands])


def delete_brand(brand_id: str) -> None:
    brands = [item for item in saved_brands() if item.id != brand_id]
    _write_json(brands_file(), [to_dict(item) for item in brands])


@dataclass
class UserPreset:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "Свой пресетъ"
    description: str = "Сохранённое оформленiе"
    style: Style = field(default_factory=Style)
    typography: Typography = field(default_factory=Typography)


def presets_file() -> pathlib.Path:
    return app_dir() / "presets.json"


def user_presets() -> list[UserPreset]:
    raw = _read_json(presets_file(), [])
    return [from_dict(UserPreset, item) for item in raw if isinstance(item, dict)]


def save_user_preset(preset: UserPreset) -> None:
    presets = [item for item in user_presets() if item.id != preset.id]
    presets.insert(0, preset)
    _write_json(presets_file(), [to_dict(item) for item in presets])


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
