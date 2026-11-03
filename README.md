# Project Notes for MoleditPy

Keep Markdown notes inside your MoleditPy 5 project, alongside your molecule.

- Open **View > Note Editor...** to write your first note.
- Switch between **Edit** (Markdown source) and **Preview** (rendered Markdown) tabs. The preview follows your current edits.
- Editing notes marks the project as modified.
- Use **Save Project**, **Ctrl+S** (**Cmd+S** on macOS) in the editor, or the application's project save command to save the molecule and notes together.
- Opening a project containing notes automatically opens the editor.
- Closing the editor keeps the text in memory. Save the project to persist changes.
- Starting a new project or opening another file clears the previous project's notes.
- To remove a note, delete all its text and save the project.

## Installation

Copy `project_notes.py` into the MoleditPy plugins folder (usually `~/.moleditpy/plugins/`) and restart MoleditPy. No additional runtime dependencies are required.

## Storage

The plugin uses `register_save_handler` and `register_load_handler`. Notes are embedded in the project's `plugins` data; no separate Markdown file is needed.

```json
{
  "Project Notes": {
    "schema_version": 1,
    "markdown": "# Notes\n\nExperimental conditions"
  }
}
```

Markdown is a plain string, without Base64 encoding or encryption. The plugin returns a Python dictionary and lets MoleditPy's JSON serializer escape quotes, brackets, newlines, backslashes, and Unicode. It never builds JSON through string concatenation. The application controls the overall project file format and compression.

Preview resource loading and automatic link opening are disabled.

## Development

```console
python -m pip install PySide6-Essentials pytest ruff
python -m pytest -q
python -m ruff check .
```

Tests use Qt's offscreen platform and cover JSON round trips, persistence hooks, automatic opening, and document changes.

CI runs on Windows and Linux with Python 3.11 and 3.13. It checks formatting,
lint, at least 90% plugin coverage, and API compatibility against MoleditPy.
The API checker and shared release helper are copied from
[moleditpy-plugin-template](https://github.com/HiroYokoyama/moleditpy-plugin-template).
Release workflows publish the single-file plugin and license notices when a
version tag is pushed, after validating the version and running the checks.

## License

LGPL-3.0-or-later. See `LICENSE`, `COPYING`, and `LICENSING.md`.
