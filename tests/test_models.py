"""Модель проекта: сохранение, размещение статей, новый номер издания."""

from __future__ import annotations

from pechatnya.models import Article, Project
from pechatnya.presets import apply_preset, apply_template, demo_project, new_project


def test_json_roundtrip_preserves_content() -> None:
    project = demo_project()
    restored = Project.from_json_dict(project.to_json_dict())

    assert restored.issue.title == project.issue.title
    assert [item.title for item in restored.articles] == [item.title for item in project.articles]
    assert len(list(restored.pages[0].blocks())) == len(list(project.pages[0].blocks()))
    sidebar = list(restored.pages[0].blocks())[1]
    assert [module.kind for module in sidebar.modules] == ["weather", "rates", "quote", "ad",
                                                           "obituary", "photo"]


def test_unknown_fields_are_ignored() -> None:
    data = demo_project().to_json_dict()
    data["какое-то-новое-поле"] = 42
    data["issue"]["ещё-одно"] = "x"

    restored = Project.from_json_dict(data)

    assert restored.issue.title == "Вечернiй Вестникъ"


def test_assign_moves_article_between_blocks() -> None:
    project = new_project()
    article = Article(title="Проба")
    project.articles.append(article)
    blocks = list(project.pages[0].blocks())

    project.assign(article.id, blocks[0].id)
    assert blocks[0].article_id == article.id
    assert article not in project.unplaced_articles()

    project.assign(article.id, blocks[2].id)
    assert blocks[0].article_id is None
    assert blocks[2].article_id == article.id

    project.detach(article.id)
    assert blocks[2].article_id is None
    assert article in project.unplaced_articles()


def test_new_issue_inherits_design_but_not_texts() -> None:
    project = demo_project()
    project.style.paper_color = "#e4ded0"

    copy = project.clone_for_new_issue("15", "Четвергъ, 13 iюня")

    assert copy.issue.number == "15"
    assert copy.style.paper_color == "#e4ded0"
    assert copy.brand.display_name == project.brand.display_name
    assert copy.articles == []
    assert all(block.article_id is None for block in copy.pages[0].blocks())
    assert {block.id for block in copy.pages[0].blocks()}.isdisjoint(
        {block.id for block in project.pages[0].blocks()}
    )


def test_template_change_keeps_placed_articles() -> None:
    project = demo_project()
    placed = [block.article_id for block in project.pages[0].blocks() if block.article_id]

    apply_template(project.pages[0], "quadrants")

    kept = [block.article_id for block in project.pages[0].blocks() if block.article_id]
    assert kept == placed[: len(kept)]
    assert len(kept) >= 4


def test_preset_replaces_style_and_typography() -> None:
    project = demo_project()

    apply_preset(project, "agitprop")

    assert project.style.preset_id == "agitprop"
    assert project.typography.heading_font == "Oswald"
    assert project.style.invert_rubrics is True
    # тексты и вёрстка не тронуты
    assert len(project.articles) == 6
