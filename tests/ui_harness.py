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


def fill_metrics(app: AppState, sheet: tuple[int, int] | None = None) -> None:
    """Заполняет метрики так, как их вернул бы движок: прямоугольники дерева.

    Раскладка считается тем же способом, что и во flex: вес — доля свободного
    места, ``fixed`` — размер в пикселях. Этого хватает, чтобы проверять зоны
    блоков, ручки границ и пересчёт весов без браузера.
    """
    from pechatnya.models import BlockFit

    width, height = sheet or app.sheet_size()
    top, bottom, left, right = app.project.margins_px()
    app.fits = {}
    app.frame_rects = {}

    def place(frame, x: float, y: float, box_w: float, box_h: float) -> None:
        rect = BlockFit(frame.id, percent=0, x=x, y=y, width=box_w, height=box_h)
        app.frame_rects[frame.id] = rect
        if frame.is_leaf:
            if frame.block is not None:
                app.fits[frame.block.id] = BlockFit(
                    frame.block.id, percent=80.0, x=x, y=y, width=box_w, height=box_h
                )
            return
        horizontal = frame.direction == "row"
        span = (box_w if horizontal else box_h) - frame.gap * max(0, len(frame.children) - 1)
        fixed_total = sum(child.fixed for child in frame.children if child.fixed is not None)
        weights = sum(child.weight for child in frame.children if child.fixed is None) or 1.0
        free = max(0.0, span - fixed_total)
        offset = 0.0
        for child in frame.children:
            size = child.fixed if child.fixed is not None else free * child.weight / weights
            if horizontal:
                place(child, x + offset, y, size, box_h)
            else:
                place(child, x, y + offset, box_w, size)
            offset += size + frame.gap

    page = app.page_model
    stack_top = top + (230 if page.show_masthead else 40)
    place(page.root, left, stack_top, width - left - right, height - stack_top - bottom - 30)
