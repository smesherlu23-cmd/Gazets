"""Обвязка для тестов интерфейса: состояние без рендера и проверка контролов.

Настоящее окно Flet в тестах не поднимается, но экраны — обычные функции,
собирающие дерево контролов. Их можно построить и прогнать через ту же
проверку, которую Flet делает перед отправкой в окно: именно она ловит ошибки
вроде «expand должен быть bool или int», из-за которых панель молча перестаёт
обновляться.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Iterator

import flet as ft

from pechatnya.ui.state import AppState


class FakePage:
    """Заглушка страницы: экраны обращаются к services, update и run_task."""

    def __init__(self) -> None:
        self.services: list[Any] = []
        self.updates = 0
        self.tasks: list[Callable] = []

    def update(self) -> None:
        self.updates += 1

    def run_task(self, handler: Callable, *args: Any) -> None:
        self.tasks.append((handler, args))


def make_app(**kwargs: Any) -> AppState:
    """Состояние приложения без фонового рендера и автосохранения."""
    app = AppState(FakePage(), start_preview=False)
    app.bind_rebuild(lambda: None)
    for name, value in kwargs.items():
        setattr(app, name, value)
    return app


def walk(control: Any) -> Iterator[ft.BaseControl]:
    """Обходит дерево контролов вглубь."""
    if isinstance(control, ft.BaseControl):
        yield control
        for field in dataclasses.fields(control):
            if field.name.startswith("_"):
                continue
            try:
                value = getattr(control, field.name)
            except Exception:
                continue
            yield from walk(value)
    elif isinstance(control, (list, tuple)):
        for item in control:
            yield from walk(item)


def check_controls(root: Any) -> int:
    """Прогоняет дерево через проверку Flet. Кидает ValueError на плохом поле."""
    from flet.utils.validation import validate

    count = 0
    for control in walk(root):
        validate(control)
        count += 1
    return count
