"""Markdown notes embedded in MoleditPy projects through persistence hooks."""

from __future__ import annotations

import logging
from typing import Any

PLUGIN_NAME = "Project Notes"
PLUGIN_VERSION = "0.1.0"
PLUGIN_AUTHOR = "HiroYokoyama"
PLUGIN_DESCRIPTION = "Markdown project notes with live preview and automatic reopening."
PLUGIN_CATEGORY = "Utility"
PLUGIN_TAGS = ["Utility", "Markdown", "Notes"]
PLUGIN_DEPENDENCIES = []
PLUGIN_SUPPORTED_MOLEDITPY_VERSION = ">=5.0.0, <6.0.0"
WINDOW_ID = "project_notes_editor"
LOGGER = logging.getLogger(__name__)


class ProjectNotes:
    """Keep note state independent of the editor's visibility."""

    def __init__(self, context: Any) -> None:
        self.context = context
        self.markdown = ""
        self.dialog = None
        self._generation = 0

    def save_state(self) -> dict:
        """Return data, never hand-built JSON; the host escapes all text."""
        if not self.markdown:
            return {}
        return {"schema_version": 1, "markdown": self.markdown}

    def load_state(self, data: Any) -> None:
        """Replace state and defer opening until the host finishes loading."""
        self.reset()
        if not isinstance(data, dict):
            LOGGER.warning("Project Notes: ignored invalid project note data")
            return
        text = data.get("markdown", "")
        if not isinstance(text, str):
            LOGGER.warning("Project Notes: ignored non-text Markdown data")
            return
        self.markdown = text
        if self.dialog is not None:
            self.dialog.set_markdown(text)
        if text:
            from PySide6.QtCore import QTimer

            generation = self._generation
            QTimer.singleShot(0, lambda: self._open_loaded_note(generation))

    def _open_loaded_note(self, generation: int) -> None:
        if generation == self._generation and self.markdown:
            self.open_editor()

    def reset(self) -> None:
        """Clear previous project notes, including pending automatic opens."""
        self._generation += 1
        self.markdown = ""
        if self.dialog is not None:
            self.dialog.set_markdown("")
            self.dialog.hide()

    def update_markdown(self, text: str) -> None:
        if text != self.markdown:
            self.markdown = text
            self.context.mark_project_modified()

    def open_editor(self) -> None:
        if self.dialog is None:
            self.dialog = _make_dialog(self)
            self.context.register_window(WINDOW_ID, self.dialog)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()


def _make_dialog(notes: ProjectNotes) -> Any:
    """Import Qt lazily so metadata discovery needs no GUI application."""
    from PySide6.QtCore import QSignalBlocker
    from PySide6.QtGui import QFontDatabase, QKeySequence, QShortcut
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QPlainTextEdit,
        QPushButton,
        QTabWidget,
        QTextBrowser,
        QVBoxLayout,
    )

    class Preview(QTextBrowser):
        def loadResource(self, resource_type: int, name: Any) -> Any:
            # Project text must not fetch remote images or read local resources.
            return None

    class Editor(QDialog):
        def __init__(self) -> None:
            super().__init__(notes.context.get_main_window())
            self.setWindowTitle("Project Notes — Markdown")
            self.resize(960, 620)
            layout = QVBoxLayout(self)
            hint = QLabel(
                "Notes are stored inside the project. Save the project to keep changes."
            )
            hint.setWordWrap(True)
            layout.addWidget(hint)
            self.tabs = QTabWidget()
            self.editor = QPlainTextEdit()
            self.editor.setPlaceholderText("# Project notes\n\nWrite Markdown here…")
            self.editor.setFont(
                QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
            )
            self.preview = Preview()
            self.preview.setOpenLinks(False)
            self.preview.setOpenExternalLinks(False)
            self.tabs.addTab(self.editor, "Edit")
            self.tabs.addTab(self.preview, "Preview")
            layout.addWidget(self.tabs)
            buttons = QHBoxLayout()
            save = QPushButton("Save Project")
            save.clicked.connect(self.save_project)
            buttons.addWidget(save)
            buttons.addStretch()
            close = QPushButton("Close")
            close.clicked.connect(self.close)
            buttons.addWidget(close)
            layout.addLayout(buttons)
            self.save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self)
            self.save_shortcut.activated.connect(self.save_project)
            self.editor.textChanged.connect(self.text_changed)
            self.set_markdown(notes.markdown)

        def set_markdown(self, text: str) -> None:
            with QSignalBlocker(self.editor):
                self.editor.setPlainText(text)
            self.preview.setMarkdown(text)

        def text_changed(self) -> None:
            text = self.editor.toPlainText()
            notes.update_markdown(text)
            self.preview.setMarkdown(text)

        def save_project(self) -> None:
            notes.context.get_main_window().io_manager.save_project()

    return Editor()


def initialize(context: Any) -> None:
    """Register the menu and project lifecycle hooks."""
    notes = ProjectNotes(context)
    context.add_menu_action("View/Note Editor...", notes.open_editor)
    context.register_save_handler(notes.save_state)
    context.register_load_handler(notes.load_state)
    context.register_document_reset_handler(notes.reset)
