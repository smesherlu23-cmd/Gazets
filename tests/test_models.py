"""Модель проекта: сохранение, размещение статей, новый номер издания."""

from __future__ import annotations

from pechatnya.models import Article, Project
from pechatnya.presets import apply_preset, apply_template, new_project
from tests.fixtures import sample_project


def test_json_roundtrip_preserves_content() -> None:
    project = sample_project()
    restored = Project.from_json_dict(project.to_json_dict())

    assert restored.issue.title == project.issue.title
    assert [item.title for item in restored.articles] == [item.title for item in project.articles]
    assert len(list(restored.pages[0].blocks())) == len(list(project.pages[0].blocks()))
    sidebar = list(restored.pages[0].blocks())[1]
    assert [module.kind for module in sidebar.modules] == ["weather", "rates", "quote", "ad",
                                                           "obituary"]


def test_unknown_fields_are_ignored() -> None:
    data = sample_project().to_json_dict()
    data["какое-то-новое-поле"] = 42
    data["issue"]["ещё-одно"] = "x"

    restored = Project.from_json_dict(data)

    assert restored.issue.title == "Вечерний вестник"


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


def test_publication_is_inherited_by_issue() -> None:
    """Издание задаёт облик, выпуск его наследует — это основной сценарий."""
    from pechatnya.models import Publication

    publication = Publication(name="Голос дока")
    publication.brand.name_cyrillic = "ГОЛОС ДОКА"
    publication.style.paper_color = "#e4ded0"
    publication.typography.body_pt = 9.0
    publication.city = "Нижний док"

    project = new_project(publication=publication)

    assert project.publication_id == publication.id
    assert project.brand.display_name == "ГОЛОС ДОКА"
    assert project.style.paper_color == "#e4ded0"
    assert project.issue.city == "Нижний док"

    # правка издания не влияет на уже созданный снимок, пока его не наследуют заново
    publication.style.paper_color = "#efe7d4"
    assert project.style.paper_color == "#e4ded0"
    project.inherit(publication)
    assert project.style.paper_color == "#efe7d4"


def test_new_project_is_empty() -> None:
    """Новый выпуск не приносит чужого содержимого."""
    project = new_project()

    assert project.articles == []
    assert project.issue.title == ""
    assert project.issue.number == ""
    assert all(block.is_empty for block in project.pages[0].blocks())


def test_new_issue_inherits_design_but_not_texts() -> None:
    project = sample_project()
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
    project = sample_project()
    placed = [block.article_id for block in project.pages[0].blocks() if block.article_id]

    apply_template(project.pages[0], "quadrants")

    kept = [block.article_id for block in project.pages[0].blocks() if block.article_id]
    assert kept == placed[: len(kept)]
    assert len(kept) >= 4


def test_preset_replaces_style_and_typography() -> None:
    project = sample_project()

    apply_preset(project, "agitprop")

    assert project.style.preset_id == "agitprop"
    assert project.typography.heading_font == "Oswald"
    assert project.style.invert_rubrics is True
    # тексты и вёрстка не тронуты
    assert len(project.articles) == 4


# ------------------------------------------------------------------- сетка


def test_block_splits_and_neighbours_take_the_space() -> None:
    """Основа конструктора: любой блок делится в любую сторону."""
    project = new_project()
    page = project.pages[0]
    first = next(page.blocks())
    before = len(list(page.blocks()))

    right = page.split_block(first.id, "row")
    assert right is not None
    assert len(list(page.blocks())) == before + 1

    below = page.split_block(right.id, "column")
    assert below is not None
    labels = [block.label for block in page.blocks()]
    assert labels.count("Новый блок") == 2


def test_removing_a_block_collapses_the_tree() -> None:
    project = new_project()
    page = project.pages[0]
    first = next(page.blocks())
    fresh = page.split_block(first.id, "row")
    depth_before = sum(1 for _ in page.frames())

    assert page.remove_block(fresh.id) is True

    assert [block.id for block in page.blocks()].count(first.id) == 1
    # контейнер с одним ребёнком не остаётся в дереве
    assert sum(1 for _ in page.frames()) < depth_before


def test_last_block_cannot_be_removed() -> None:
    project = new_project()
    page = project.pages[0]
    while len(list(page.blocks())) > 1:
        page.remove_block(list(page.blocks())[-1].id)

    assert page.remove_block(next(page.blocks()).id) is False
    assert len(list(page.blocks())) == 1


def test_blocks_can_be_reordered() -> None:
    project = new_project()
    page = project.pages[0]
    labels = [block.label for block in page.blocks()]
    first = next(page.blocks())

    assert page.move_block(first.id, 1) is True

    assert [block.label for block in page.blocks()] != labels


def test_adding_a_block_extends_the_page() -> None:
    project = new_project()
    page = project.pages[0]
    before = len(list(page.blocks()))

    page.add_block("column")
    page.add_block("row")

    assert len(list(page.blocks())) == before + 2


# -------------------------------------------------------------------- лист


def test_sheet_size_follows_format_and_orientation() -> None:
    project = new_project()

    project.page_format = "A4"
    assert project.sheet_px() == (794, 1123)

    project.page_format = "A3"
    assert project.sheet_px() == (1123, 1587)

    project.orientation = "landscape"
    assert project.sheet_px() == (1587, 1123)

    project.page_format = "Свой размер"
    project.custom_size_mm = [250.0, 350.0]
    project.orientation = "portrait"
    assert project.sheet_px() == (945, 1323)


def test_margins_are_real_millimetres() -> None:
    project = new_project()
    project.margins_mm = [20.0, 10.0, 15.0, 5.0]

    top, bottom, left, right = project.margins_px()

    assert round(top) == 76 and round(bottom) == 38
    assert round(left) == 57 and round(right) == 19


# ------------------------------------------------------ файлы прошлых версий


def test_old_project_with_flat_rows_is_migrated() -> None:
    """Файл прошлой версии (строки полосы) открывается как дерево."""
    old = {
        "format_version": 1,
        "issue": {"title": "Старый выпуск", "number": "7"},
        "articles": [{"id": "art-1", "title": "Материал", "body": "Текст"}],
        "pages": [
            {
                "id": "pg-1",
                "kind": "front",
                "show_masthead": True,
                "rows": [
                    {
                        "weight": 1.0,
                        "gap": 16.0,
                        "blocks": [
                            {"id": "blk-1", "label": "Главная", "weight": 2.0,
                             "columns": 3, "article_id": "art-1", "kind": "article"},
                            {"id": "blk-2", "label": "Бок", "fixed_width": 196.0, "columns": 1},
                        ],
                    },
                    {"fixed_height": 120.0, "blocks": [{"id": "blk-3", "label": "Подвал"}]},
                ],
            }
        ],
    }

    project = Project.from_json_dict(old)

    page = project.pages[0]
    assert [block.label for block in page.blocks()] == ["Главная", "Бок", "Подвал"]
    assert page.root.direction == "column"
    side = page.root.leaf_of_block("blk-2")
    assert side is not None and side.fixed == 196.0
    assert page.root.children[1].fixed == 120.0
    assert project.article("art-1") is not None


# --------------------------------------------- продолжение и перестановки


def test_reassigning_a_split_article_cancels_the_continuation() -> None:
    """Перетащили статью в другой блок — остаток текста не должен пропасть."""
    from tests.fixtures import sample_project

    project = sample_project()
    lead = project.articles[0]
    project.place_continuation(lead.id, 1, 900)
    target = project.free_block_on(2)

    project.assign(lead.id, target.id)

    assert lead.split_at is None
    assert lead.continued_on is None
    assert project.block_of(lead.id, part=1) is None
    assert lead.part_text(0) == lead.body  # текст снова целый


def test_releasing_the_tail_block_keeps_the_article_whole() -> None:
    from tests.fixtures import sample_project

    project = sample_project()
    lead = project.articles[0]
    project.place_continuation(lead.id, 1, 900)
    tail = project.block_of(lead.id, part=1)

    project.release_block(tail)

    assert lead.split_at is None
    assert project.block_of(lead.id, part=0) is not None  # начало осталось на полосе


def test_releasing_the_head_block_takes_the_article_off_the_page() -> None:
    from tests.fixtures import sample_project

    project = sample_project()
    lead = project.articles[0]
    project.place_continuation(lead.id, 1, 900)
    head = project.block_of(lead.id, part=0)

    project.release_block(head)

    assert project.block_of(lead.id, part=0) is None
    assert project.block_of(lead.id, part=1) is None
    assert lead in project.unplaced_articles()


def test_template_change_keeps_continuation_parts() -> None:
    """Смена сетки не должна превращать продолжение во второй экземпляр начала."""
    from tests.fixtures import sample_project

    project = sample_project()
    lead = project.articles[0]
    page = project.pages[1]
    project.place_continuation(lead.id, 1, 900)
    apply_template(page, "gallery")

    parts = sorted(block.article_part for block in page.blocks() if block.article_id == lead.id)
    assert parts == [1]  # продолжение осталось продолжением, дубля начала нет
