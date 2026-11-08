import gc
import time
import tkinter as tk

import pytest

import gui.app as app_module
from gui.app import OrganizerApp, summarize_results


def make_files(folder, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_text(f"contents of {name}")


#  pure logic (no window needed)

def test_summarize_counts_statuses_and_categories():
    results = [
        {"file": "a.pdf", "category": "Documents", "status": "Moved"},
        {"file": "b.pdf", "category": "Documents", "status": "Error"},
        {"file": "c.jpg", "category": "Images", "status": "Moved"},
    ]

    summary = summarize_results(results)

    assert summary == {
        "total": 3,
        "planned": 0,
        "moved": 2,
        "errors": 1,
        "by_category": {"Documents": 2, "Images": 1},
    }


def test_summarize_empty_list():
    assert summarize_results([]) == {
        "total": 0, "planned": 0, "moved": 0, "errors": 0, "by_category": {},
    }


#  window tests (need a display; skipped otherwise) 

@pytest.fixture
def app(monkeypatch, tmp_path):
    # Replace message boxes so tests never block waiting for a click.
    calls = {"askyesno": True, "messages": []}

    def record(name):
        def fake(title, message, **kwargs):
            calls["messages"].append((name, title, message))
            return calls["askyesno"] if name == "askyesno" else None
        return fake

    for name in ("showinfo", "showwarning", "showerror", "askyesno"):
        monkeypatch.setattr(app_module.messagebox, name, record(name))

    try:
        window = OrganizerApp()
    except tk.TclError as error:
        pytest.skip(f"No display available: {error}")

    window.calls = calls
    yield window
    window.destroy()
    del window
    gc.collect()


def wait_until(window, condition, timeout=10):
    """Run the real Tk event loop until condition() is true, or fail after timeout seconds."""
    deadline = time.time() + timeout
    outcome = {"ok": False}

    def check():
        if condition():
            outcome["ok"] = True
            window.quit()
        elif time.time() > deadline:
            window.quit()
        else:
            window.after(10, check)

    window.after(10, check)
    window.mainloop()
    if not outcome["ok"]:
        raise AssertionError("timed out waiting for the GUI")


def test_window_builds_with_expected_controls(app):
    assert app.title() == "Smart File Organizer"
    assert app.table["columns"] == ("file", "category", "status", "destination")


def test_results_table_has_horizontal_scrollbar_for_long_paths(app):
    # The destination column is wide and does not shrink, so the table
    # must be connected to a horizontal scrollbar to reach the full path.
    assert app.table.cget("xscrollcommand") != ""
    assert app.table.column("destination", "stretch") in (False, 0, "0")
    assert int(app.table.column("destination", "width")) >= 900


def test_preview_fills_table_and_moves_nothing(app, tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["report.pdf", "photo.jpg"])
    app.source_var.set(str(source))
    app.destination_var.set(str(tmp_path / "Organized"))

    app.preview()
    wait_until(app, lambda: not app._busy)

    assert len(app.table.get_children()) == 2
    assert sorted(p.name for p in source.iterdir()) == ["photo.jpg", "report.pdf"]
    assert not (tmp_path / "Organized").exists()


def test_organize_moves_files_after_confirmation(app, tmp_path):
    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["report.pdf", "photo.jpg"])
    app.source_var.set(str(source))
    app.destination_var.set(str(destination))

    app.organize()
    wait_until(app, lambda: not app._busy and "Done" in app.status_var.get())

    assert (destination / "Documents" / "report.pdf").exists()
    assert (destination / "Images" / "photo.jpg").exists()


def test_declining_confirmation_moves_nothing(app, tmp_path):
    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["report.pdf"])
    app.source_var.set(str(source))
    app.destination_var.set(str(destination))
    app.calls["askyesno"] = False

    app.organize()
    wait_until(app, lambda: not app._busy and "Cancelled" in app.status_var.get())

    assert (source / "report.pdf").exists()
    assert not destination.exists()


def test_missing_folder_shows_warning_and_does_nothing(app):
    app.source_var.set("")
    app.destination_var.set("")

    app.preview()

    assert app.calls["messages"][-1][0] == "showwarning"
    assert not app._busy


def test_duplicates_are_reported_not_deleted(app, tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["a.txt", "b.txt"])
    (source / "b.txt").write_text("contents of a.txt")  # now identical to a.txt
    app.source_var.set(str(source))

    app.find_duplicates()
    wait_until(app, lambda: not app._busy and "duplicate" in app.status_var.get().lower())

    assert sorted(p.name for p in source.iterdir()) == ["a.txt", "b.txt"]
    assert "Duplicate groups: 1" in app.stats_var.get()
