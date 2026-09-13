"""Состояние приложения: отмена, сохранение, издания, выделение блоков."""

from __future__ import annotations

import pathlib

import pytest

from pechatnya import storage
from pechatnya.models import ImageRef, Publication
from pechatnya.presets import make_module
from tests.fixtures import sample_project
from tests.ui_harness import make_app


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "профиль"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PECHATNYA_HOME", str(home))
    monkeypatch.setattr(storage, "app_dir", lambda: home)
    monkeypatch.setattr(storage, "documents_dir", lambda: tmp_path / "Документы")
    yield


# ------------------------------------------------------------------- отмена


def test_undo_and_redo_restore_layout() -> None:
    app = make_app()
    app.set_project(sample_project())
    lead = app.project.articles[0]
    assert app.can_undo is False

    app.project.detach(lead.id)
    app.touch()

    assert app.can_undo is True
    assert app.project.block_of(lead.id) is None

    assert app.undo() is True
    assert app.project.block_of(lead.id) is not None  # статья вернулась на полосу
    assert app.can_redo is True

    assert app.redo() is True
    assert app.project.block_of(lead.id) is None


def test_undo_stops_at_the_beginning() -> None:
    app = make_app()
    app.set_project(sample_project())

    assert app.undo() is False
    assert app.redo() is False


def test_rapid_edits_collapse_into_one_undo_step(monkeypatch) -> None:
    """Набор текста не должен превращать отмену в посимвольную."""
    app = make_app()
    app.set_project(sample_project())
    article = app.project.articles[0]
    original = article.body

    clock = [1000.0]
    monkeypatch.setattr("pechatnya.ui.state.time.monotonic", lambda: clock[0])
    for index in range(5):
        article.body = original + "а" * (index + 1)
        clock[0] += 0.2  # правки подряд, быстрее порога склейки
        app.touch()

    assert len(app._undo) == 1
    app.undo()
    assert app.project.articles[0].body == original


def test_edits_apart_in_time_are_separate_steps(monkeypatch) -> None:
    app = make_app()
    app.set_project(sample_project())
    article = app.project.articles[0]

    clock = [1000.0]
    monkeypatch.setattr("pechatnya.ui.state.time.monotonic", lambda: clock[0])
    for index in range(3):
        article.title = f"Заголовок {index}"
        clock[0] += 5.0
        app.touch()

    assert len(app._undo) == 3
    app.undo()
    assert app.project.articles[0].title == "Заголовок 1"


def test_undo_drops_stale_selection() -> None:
    app = make_app()
    app.set_project(sample_project())
    page = app.page_model
    page.rows[0].blocks.pop()  # убрали блок целиком
    app.touch()
    app.selected_block_id = "blk-которого-нет"

    app.undo()

    assert app.selected_block_id is None


# --------------------------------------------------------------- сохранение


def test_save_moves_images_into_project_folder(tmp_path) -> None:
    source = tmp_path / "снимок.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 40)
    app = make_app()
    app.set_project(sample_project())
    # картинка вставлена до первого сохранения — лежит в профиле по абсолютному пути
    app.project.articles[0].image = ImageRef(path=storage.import_image(source, None))
    assert pathlib.Path(app.project.articles[0].image.path).is_absolute()

    path = app.save(tmp_path / "вечерний-14")

    stored = app.project.articles[0].image.path
    assert not pathlib.Path(stored).is_absolute()
    assert (path.parent / stored).exists()
    assert app.dirty is False


def test_save_as_carries_images_to_the_new_place(tmp_path) -> None:
    source = tmp_path / "док.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"y" * 40)
    app = make_app()
    app.set_project(sample_project())
    app.project.articles[0].image = ImageRef(path=storage.import_image(source, None))
    app.save(tmp_path / "первое-место")

    moved = app.save(tmp_path / "другая-папка" / "второе-место")

    stored = app.project.articles[0].image.path
    assert (moved.parent / stored).exists()
    assert moved.parent.name == "другая-папка"


def test_module_images_move_too(tmp_path) -> None:
    source = tmp_path / "реклама.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"z" * 40)
    app = make_app()
    app.set_project(sample_project())
    block = app.project.free_block_on(1)
    module = make_module("photo")
    module.image = ImageRef(path=storage.import_image(source, None))
    block.modules = [module]
    block.kind = "module"

    path = app.save(tmp_path / "выпуск")

    stored = block.modules[0].image.path
    assert not pathlib.Path(stored).is_absolute()
    assert (path.parent / stored).exists()


def test_save_without_path_lands_in_documents(tmp_path) -> None:
    app = make_app()
    app.set_project(sample_project())

    path = app.save()

    assert path.parent == tmp_path / "Документы"
    assert storage.recent_projects()[0].path == str(path)


# ------------------------------------------------------------------ издания


def test_saving_publication_updates_current_issue() -> None:
    app = make_app()
    app.set_project(sample_project())
    app.open_publications("layout")
    app.editing_publication.name = "Голос дока"
    app.editing_publication.brand.name_cyrillic = "ГОЛОС ДОКА"
    app.editing_publication.style.paper_color = "#e4ded0"

    app.save_publication()

    assert app.project.brand.display_name == "ГОЛОС ДОКА"
    assert app.project.style.paper_color == "#e4ded0"
    assert [item.display_name for item in app.publications] == ["Голос дока"]
    assert app.publication_dirty is False


def test_publication_duplicate_and_delete() -> None:
    app = make_app()
    app.editing_publication = Publication(name="Вечерний вестник")
    app.save_publication()

    app.duplicate_publication()
    assert len(app.publications) == 2
    assert app.editing_publication.name.endswith("копия")

    app.delete_publication()
    assert len(app.publications) == 1


def test_new_publication_returns_to_the_wizard() -> None:
    app = make_app(route="issue")
    app.new_publication(from_wizard=True)
    app.editing_publication.name = "Портовый листок"

    app.save_publication()

    assert app.wizard.publication_id == app.editing_publication.id
    app.leave_publications()
    assert app.route == "issue"


# ------------------------------------------------------------------- блоки


def test_block_selection_toggles_and_opens_block_tab() -> None:
    app = make_app()
    app.set_project(sample_project())
    block = list(app.page_model.blocks())[0]
    app.panel_tab = "paper"

    app.select_block(block.id)
    assert app.selected_block is block
    assert app.panel_tab == "block"

    app.select_block(None)
    assert app.selected_block is None


def test_overflow_is_reported_for_status_bar() -> None:
    from pechatnya.models import BlockFit

    app = make_app()
    app.set_project(sample_project())
    block = list(app.page_model.blocks())[0]
    app.fits = {block.id: BlockFit(block.id, percent=124.0, overflow_chars=310)}

    assert [fit.block_id for fit in app.overflowing_blocks()] == [block.id]
    assert app.article_fit(block.article_id).overflow_chars == 310


def test_split_needs_a_free_block() -> None:
    """Перенос на забитую полосу не делается молча — состояние сообщает причину."""
    app = make_app()
    app.set_project(sample_project())
    lead = app.project.articles[0]
    for block in app.project.pages[1].blocks():
        block.kind = "module"
        block.modules = [make_module("ad")]

    app.split_article(lead.id, 1)

    assert "нет свободного блока" in app.busy_note
    assert app.project.block_of(lead.id, part=1) is None
