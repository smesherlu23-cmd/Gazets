"""Случайные последовательности правок не должны ломать полосу.

Тест прогоняет вёрстку через типичные действия пользователя в случайном
порядке и после каждого проверяет, что полоса остаётся целой. Так нашлись
пустые узлы сетки и переносы, потерявшие одну из частей.
"""

from __future__ import annotations

import random

import pytest

from pechatnya.presets import GRID_TEMPLATES, apply_template, make_module
from tests.fixtures import sample_project

OPERATIONS = (
    "split", "remove", "move", "assign", "detach", "modules", "template", "continue", "drop"
)


def check(project) -> None:
    for page in project.pages:
        for frame in page.frames():
            if frame.is_leaf:
                assert frame.block is not None, "лист сетки без блока"
            else:
                assert frame.children, "пустой контейнер в сетке"
        blocks = list(page.blocks())
        assert blocks, "полоса осталась без блоков"
        assert len({block.id for block in blocks}) == len(blocks), "блоки задвоились"
    for article in project.articles:
        parts = [
            block.article_part
            for page in project.pages
            for block in page.blocks()
            if block.article_id == article.id
        ]
        assert len(parts) == len(set(parts)), "одна и та же часть статьи стоит дважды"
        if article.split_at is not None:
            assert sorted(parts) == [0, 1], "перенос остался без начала или без остатка"


def step(project, generator: random.Random) -> None:
    page = project.pages[generator.randrange(len(project.pages))]
    blocks = list(page.blocks())
    operation = generator.choice(OPERATIONS)
    if operation == "split":
        page.split_block(generator.choice(blocks).id, generator.choice(["row", "column"]))
    elif operation == "remove":
        block = generator.choice(blocks)
        project.release_block(block)
        page.remove_block(block.id)
    elif operation == "move":
        page.move_block(generator.choice(blocks).id, generator.choice([-1, 1]))
    elif operation == "assign" and project.articles:
        project.assign(generator.choice(project.articles).id, generator.choice(blocks).id)
    elif operation == "detach" and project.articles:
        project.detach(generator.choice(project.articles).id)
    elif operation == "modules":
        block = generator.choice(blocks)
        project.release_block(block)
        block.article_id = None
        block.modules = [make_module(generator.choice(["ad", "list", "schedule", "fact"]))]
        block.kind = "module"
    elif operation == "template":
        apply_template(page, generator.choice(GRID_TEMPLATES).id)
        project.repair_continuations()
    elif operation == "continue" and project.articles:
        project.place_continuation(
            generator.choice(project.articles).id, generator.randrange(len(project.pages)), 500
        )
    elif operation == "drop" and project.articles:
        project.drop_continuation(generator.choice(project.articles).id)


@pytest.mark.parametrize("seed", [1, 7, 13, 42, 99])
def test_random_editing_keeps_the_page_consistent(seed: int) -> None:
    generator = random.Random(seed)
    project = sample_project()

    for _ in range(40):
        step(project, generator)
        check(project)


def test_empty_container_is_pruned() -> None:
    """Шаблон может содержать контейнер с одним блоком — после удаления он исчезает."""
    from pechatnya.models import Block, Page, column, leaf, row

    page = Page(root=column(leaf(Block(label="Афиша")), row(leaf(Block(label="Подробности")))))
    page.remove_block(list(page.blocks())[1].id)

    assert [frame.direction for frame in page.frames()] == [""]
    assert [block.label for block in page.blocks()] == ["Афиша"]


def test_assigning_over_a_split_head_clears_the_continuation() -> None:
    project = sample_project()
    lead, other = project.articles[0], project.articles[1]
    project.place_continuation(lead.id, 1, 900)
    head = project.block_of(lead.id, part=0)

    project.assign(other.id, head.id)

    assert lead.split_at is None
    assert project.block_of(lead.id, part=1) is None
    check(project)
