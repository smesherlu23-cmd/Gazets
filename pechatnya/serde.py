"""Сериализация датаклассов проекта в JSON и обратно.

Формат проекта — обычный JSON (см. ТЗ, п. 4.8), поэтому нужен предсказуемый
переход «датакласс ↔ словарь», терпимый к файлам, записанным прошлыми версиями:
незнакомые ключи игнорируются, отсутствующие берутся из значений по умолчанию.
"""

from __future__ import annotations

import dataclasses
import enum
import types
import typing
from typing import Any, TypeVar, Union, get_args, get_origin

T = TypeVar("T")

_HINTS_CACHE: dict[type, dict[str, Any]] = {}


def _hints(cls: type) -> dict[str, Any]:
    if cls not in _HINTS_CACHE:
        _HINTS_CACHE[cls] = typing.get_type_hints(cls)
    return _HINTS_CACHE[cls]


def to_dict(value: Any) -> Any:
    """Разворачивает датаклассы, списки, словари и enum-ы в JSON-совместимый вид."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_dict(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_dict(item) for key, item in value.items()}
    return value


def _is_optional(annotation: Any) -> bool:
    return get_origin(annotation) in (Union, types.UnionType) and type(None) in get_args(annotation)


def _unwrap_optional(annotation: Any) -> Any:
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    return args[0] if len(args) == 1 else annotation


def from_value(annotation: Any, raw: Any) -> Any:
    if raw is None:
        return None
    if _is_optional(annotation):
        annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)
    if origin in (list, tuple):
        (item_type,) = get_args(annotation) or (Any,)
        return [from_value(item_type, item) for item in raw]
    if origin is dict:
        key_type, item_type = get_args(annotation) or (str, Any)
        return {key_type(key): from_value(item_type, item) for key, item in raw.items()}
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return annotation(raw)
    if dataclasses.is_dataclass(annotation) and isinstance(raw, dict):
        return from_dict(annotation, raw)
    if annotation is float and isinstance(raw, int):
        return float(raw)
    return raw


def from_dict(cls: type[T], data: dict[str, Any]) -> T:
    """Собирает датакласс из словаря, пропуская лишние и подставляя недостающие поля."""
    if not isinstance(data, dict):
        raise TypeError(f"ожидался объект для {cls.__name__}, получено {type(data).__name__}")
    hints = _hints(cls)
    kwargs: dict[str, Any] = {}
    for field in dataclasses.fields(cls):
        if field.name not in data:
            continue
        kwargs[field.name] = from_value(hints[field.name], data[field.name])
    return cls(**kwargs)  # type: ignore[return-value]
