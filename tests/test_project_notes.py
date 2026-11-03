"""Exercise persistence and editor lifecycle with real Qt widgets."""

import json
import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

from project_notes import ProjectNotes, initialize


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def context(app):
    window = QMainWindow()
    window.io_manager = Mock()
    ctx = Mock()
    ctx.get_main_window.return_value = window
    yield ctx
    window.close()
    window.deleteLater()
    app.processEvents()


@pytest.fixture
def notes(context, app):
    controller = ProjectNotes(context)
    yield controller
    controller.reset()
    if controller.dialog is not None:
        controller.dialog.close()
        controller.dialog.deleteLater()
    app.processEvents()


def test_registers_view_menu_and_hooks(context):
    initialize(context)
    assert context.add_menu_action.call_args.args[0] == "View/Note Editor..."
    context.register_save_handler.assert_called_once()
    context.register_load_handler.assert_called_once()
    context.register_document_reset_handler.assert_called_once()
    assert context.register_save_handler.call_args.args[0]() == {}
    context.register_window.assert_not_called()


@pytest.mark.parametrize(
    "text",
    [
        'Quotes: "double" and (parentheses) [brackets] {braces}',
        'Injection-like text: "}, "plugins": {"other": "changed"}',
        "# 日本語のメモ 🧪\n\n- 条件: 25°C\n- 溶媒: 水\n",
        "Windows path: C:\\notes\\test.md\nTab:\tNull:\x00\r\n",
        '```json\n{"array": [1, 2], "text": "\\\\"}\n```\n',
    ],
)
def test_json_round_trip_preserves_text_and_neighbor_data(notes, app, text):
    notes.update_markdown(text)
    project = {
        "2d_structure": {"atoms": [1, 2]},
        "plugins": {"Other Plugin": {"value": 42}, "Project Notes": notes.save_state()},
    }
    restored = json.loads(json.dumps(project, ensure_ascii=False))
    assert restored["2d_structure"] == project["2d_structure"]
    assert restored["plugins"]["Other Plugin"] == {"value": 42}
    notes.load_state(restored["plugins"]["Project Notes"])
    app.processEvents()
    assert notes.markdown == text
    assert notes.save_state()["markdown"] == text


def test_edit_marks_project_modified_but_load_does_not(notes, context, app):
    notes.load_state({"markdown": "# Saved"})
    app.processEvents()
    context.mark_project_modified.assert_not_called()
    notes.dialog.editor.setPlainText("# Updated")
    context.mark_project_modified.assert_called_once()
    assert notes.save_state()["markdown"] == "# Updated"
    assert "Updated" in notes.dialog.preview.toPlainText()


def test_load_opens_existing_note_and_reuses_editor(notes, app):
    notes.load_state({"schema_version": 1, "markdown": "# Loaded"})
    assert notes.dialog is None
    app.processEvents()
    editor = notes.dialog
    assert editor.isVisible()
    assert editor.editor.toPlainText() == "# Loaded"
    notes.open_editor()
    assert notes.dialog is editor
    notes.load_state({"markdown": "Next project"})
    app.processEvents()
    assert notes.dialog is editor
    assert editor.editor.toPlainText() == "Next project"


def test_closed_editor_keeps_note_for_project_save(notes):
    notes.open_editor()
    notes.dialog.editor.setPlainText("Keep me")
    notes.dialog.close()
    assert not notes.dialog.isVisible()
    assert notes.save_state()["markdown"] == "Keep me"
    notes.open_editor()
    assert notes.dialog.editor.toPlainText() == "Keep me"


def test_reset_clears_open_editor_without_dirtying_project(notes, context, app):
    notes.load_state({"markdown": "Old project"})
    app.processEvents()
    notes.reset()
    assert notes.markdown == ""
    assert notes.save_state() == {}
    assert notes.dialog.editor.toPlainText() == ""
    assert not notes.dialog.isVisible()
    context.mark_project_modified.assert_not_called()


@pytest.mark.parametrize("data", [{}, {"markdown": ""}, None, [], {"markdown": 42}])
def test_missing_or_invalid_notes_do_not_open_editor(notes, app, data):
    notes.update_markdown("Previous project")
    notes.load_state(data)
    app.processEvents()
    assert notes.save_state() == {}
    assert notes.dialog is None


def test_reset_cancels_pending_auto_open(notes, app):
    notes.load_state({"markdown": "Old"})
    notes.reset()
    app.processEvents()
    assert notes.dialog is None


def test_newer_project_wins_over_pending_auto_open(notes, app):
    notes.load_state({"markdown": "Old"})
    notes.load_state({"markdown": "New"})
    app.processEvents()
    assert notes.dialog.editor.toPlainText() == "New"


def test_clear_note_removes_payload(notes):
    notes.open_editor()
    notes.dialog.editor.setPlainText("Temporary")
    notes.dialog.editor.clear()
    assert notes.save_state() == {}


def test_editor_save_delegates_to_host(notes, context):
    notes.open_editor()
    notes.dialog.save_project()
    context.get_main_window().io_manager.save_project.assert_called_once()


def test_preview_does_not_load_resources_or_open_links(notes):
    notes.open_editor()
    assert not notes.dialog.preview.openLinks()
    assert not notes.dialog.preview.openExternalLinks()
    assert notes.dialog.preview.loadResource(2, "file:///private/image.png") is None


def test_edit_and_preview_modes_show_current_content(notes):
    notes.open_editor()
    dialog = notes.dialog
    assert dialog.tabs.tabText(0) == "Edit"
    assert dialog.tabs.tabText(1) == "Preview"
    assert dialog.tabs.currentWidget() is dialog.editor
    dialog.editor.setPlainText("# Heading\n\n**Bold** and `code`")
    dialog.tabs.setCurrentIndex(1)
    assert dialog.tabs.currentWidget() is dialog.preview
    assert dialog.preview.isReadOnly()
    assert "Heading" in dialog.preview.toPlainText()
    assert "**Bold**" not in dialog.preview.toPlainText()
    dialog.tabs.setCurrentIndex(0)
    assert "**Bold**" in dialog.editor.toPlainText()
