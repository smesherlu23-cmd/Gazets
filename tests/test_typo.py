"""Наборная типографика: кавычки, тире, неразрывные пробелы."""

from __future__ import annotations

import pytest

from pechatnya.render import typo
from pechatnya.render.html import page_document
from tests.fixtures import sample_project

NBSP = typo.NBSP
THIN = typo.THIN


@pytest.mark.parametrize(
    "source, expected",
    [
        ('Артель "Три якоря"', "Артель «Три якоря»"),
        ("Сторож - и балка", f"Сторож{NBSP}— и{NBSP}балка"),
        ("Смета -- вдвое", f"Смета{NBSP}— вдвое"),
        ("Ждём...", "Ждём…"),
        ("№ 14", f"№{NBSP}14"),
        ("1 200 рублей", f"1{THIN}200 рублей"),
        ("и т. д.", f"и{NBSP}т.{NBSP}д."),
        ("- пункт списка", "— пункт списка"),
    ],
)
def test_typographic_replacements(source: str, expected: str) -> None:
    assert typo.apply(source) == expected


def test_short_words_stick_to_the_next_word() -> None:
    """Предлог не должен оставаться один в конце строки."""
    result = typo.apply("в доке и на пристани у ворот")

    assert result == f"в{NBSP}доке и{NBSP}на{NBSP}пристани у{NBSP}ворот"


def test_initials_keep_the_surname() -> None:
    assert typo.apply("М. П. Гроув") == f"М.{THIN}П.{NBSP}Гроув"
    assert typo.apply("П. Рогов") == f"П.{NBSP}Рогов"


def test_markup_and_empty_text_survive() -> None:
    assert typo.apply("") == ""
    assert "**жирный**" in typo.apply("совсем **жирный** текст")


def test_polish_is_applied_to_the_page_and_can_be_switched_off() -> None:
    project = sample_project()
    project.articles[0].body = 'Сторож сказал "стой" - и ушёл.'

    polished = page_document(project, 0)
    assert "«стой»" in polished
    assert NBSP in polished

    project.style.typography_polish = False
    plain = page_document(project, 0)
    assert "«стой»" not in plain
    assert "&quot;стой&quot;" in plain or '"стой"' in plain


def test_partial_line_trimming_is_switchable() -> None:
    project = sample_project()

    assert "data-fit" in page_document(project, 0)
    assert "maxHeight" in page_document(project, 0)

    project.style.trim_partial_lines = False
    assert "maxHeight" not in page_document(project, 0)
