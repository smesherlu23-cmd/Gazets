"""Проверка выпуска перед выгрузкой."""

from __future__ import annotations

from pechatnya import checks
from pechatnya.models import Article, ImageRef
from pechatnya.presets import make_module, new_project
from tests.fixtures import sample_project


def test_clean_issue_has_no_blocking_findings(tmp_path) -> None:
    project = sample_project()
    for page in project.pages[1:]:
        project.pages = project.pages[:1]  # оставляем только свёрстанную полосу
    project.articles[0].image = None

    findings = checks.inspect(project, tmp_path)

    assert [item for item in findings if item.level == checks.ERROR] == []


def test_missing_image_is_an_error(tmp_path) -> None:
    project = sample_project()
    project.articles[0].image = ImageRef(path="пропавший.png", caption="подпись")

    findings = checks.inspect(project, tmp_path)

    assert any(item.level == checks.ERROR and "снимок" in item.text for item in findings)


def test_existing_image_passes(tmp_path) -> None:
    picture = tmp_path / "снимок.png"
    picture.write_bytes(b"\x89PNG\r\n\x1a\n")
    project = sample_project()
    project.articles[0].image = ImageRef(path="снимок.png", caption="подпись")

    findings = checks.inspect(project, tmp_path)

    assert not any("не найден" in item.text for item in findings)


def test_unplaced_article_and_empty_module_are_reported() -> None:
    project = sample_project()
    project.articles.append(Article(title="Забытый материал"))
    block = project.free_block_on(1)
    block.modules = [make_module("ad")]
    block.kind = "module"

    findings = checks.inspect(project)
    texts = [item.text for item in findings]

    assert any("Забытый материал" in text for text in texts)
    assert any("пустой" in text for text in texts)


def test_missing_issue_details_are_reported() -> None:
    project = new_project()

    findings = checks.inspect(project)
    levels = {item.level for item in findings}

    assert checks.ERROR in levels  # нет названия издания
    assert any("номер" in item.text for item in findings)


def test_summary_counts_by_level() -> None:
    findings = [
        checks.Finding(checks.ERROR, "раз"),
        checks.Finding(checks.WARNING, "два"),
        checks.Finding(checks.WARNING, "три"),
        checks.Finding(checks.NOTE, "четыре"),
    ]

    assert checks.summary(findings) == "ошибок: 1 · предупреждений: 2 · заметок: 1"
    assert checks.summary([]) == "замечаний нет"


def test_finding_label_mentions_the_page() -> None:
    assert checks.Finding(checks.NOTE, "пусто", page=3).label.startswith("Полоса 3:")
    assert checks.Finding(checks.NOTE, "пусто").label == "пусто"
