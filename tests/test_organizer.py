import shutil
from datetime import datetime
from pathlib import Path

import pytest

from organizer import organizer
from organizer.organizer import get_unique_path, organize_files


def make_files(folder, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_text(f"contents of {name}")


#  get_unique_path

def test_unique_path_returns_same_name_when_free(tmp_path):
    target = tmp_path / "photo.jpg"
    assert get_unique_path(target) == target


def test_unique_path_adds_counter_when_taken(tmp_path):
    (tmp_path / "photo.jpg").write_text("x")
    assert get_unique_path(tmp_path / "photo.jpg") == tmp_path / "photo_1.jpg"


def test_unique_path_skips_reserved_names(tmp_path):
    reserved = {tmp_path / "photo.jpg", tmp_path / "photo_1.jpg"}
    assert get_unique_path(tmp_path / "photo.jpg", taken=reserved) == tmp_path / "photo_2.jpg"


#  dry run (preview)

def test_dry_run_moves_nothing(tmp_path):
    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["report.pdf", "photo.jpg"])

    results = organize_files(source, destination)  # dry_run defaults to True

    assert sorted(p.name for p in source.iterdir()) == ["photo.jpg", "report.pdf"]
    assert not destination.exists()  # not even the folder is created
    assert {r["status"] for r in results} == {"Planned"}


def test_dry_run_reports_correct_categories(tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["report.pdf", "photo.jpg", "weird.xyz"])

    results = organize_files(source, tmp_path / "Organized", dry_run=True)
    by_file = {r["file"]: r["category"] for r in results}

    assert by_file == {
        "report.pdf": "Documents",
        "photo.jpg": "Images",
        "weird.xyz": "Others",
    }


def test_dry_run_predicts_clashes_within_the_run(tmp_path):

    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["a.jpg", "a_1.jpg"])
    make_files(destination / "Images", ["a.jpg"])  # already there

    results = organize_files(source, destination, dry_run=True)
    targets = {r["file"]: Path(r["destination"]).name for r in results}

    assert targets == {"a.jpg": "a_1.jpg", "a_1.jpg": "a_1_1.jpg"}


#  real run 

def test_moves_files_into_category_folders(tmp_path):
    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["report.pdf", "photo.jpg", "music.mp3"])

    results = organize_files(source, destination, dry_run=False)

    assert (destination / "Documents" / "report.pdf").exists()
    assert (destination / "Images" / "photo.jpg").exists()
    assert (destination / "Audio" / "music.mp3").exists()
    assert list(source.iterdir()) == []
    assert {r["status"] for r in results} == {"Moved"}


def test_existing_destination_file_is_never_overwritten(tmp_path):
    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["photo.jpg"])
    make_files(destination / "Images", ["photo.jpg"])
    original = destination / "Images" / "photo.jpg"

    results = organize_files(source, destination, dry_run=False)

    assert original.read_text() == "contents of photo.jpg"  # untouched
    assert (destination / "Images" / "photo_1.jpg").read_text() == "contents of photo.jpg"
    assert results[0]["destination"] == str(destination / "Images" / "photo_1.jpg")


def test_by_date_adds_year_folder(tmp_path):
    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["photo.jpg"])
    year = str(datetime.fromtimestamp((source / "photo.jpg").stat().st_mtime).year)

    organize_files(source, destination, dry_run=False, by_date=True)

    assert (destination / "Images" / year / "photo.jpg").exists()


def test_by_date_dry_run_plans_year_folder(tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["photo.jpg"])
    year = str(datetime.fromtimestamp((source / "photo.jpg").stat().st_mtime).year)

    (result,) = organize_files(source, tmp_path / "Organized", by_date=True)

    assert result["destination"] == str(tmp_path / "Organized" / "Images" / year / "photo.jpg")


def test_subfolders_are_left_alone(tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["report.pdf"])
    make_files(source / "keep_me", ["inside.txt"])

    organize_files(source, tmp_path / "Organized", dry_run=False)

    assert (source / "keep_me" / "inside.txt").exists()


def test_one_failed_move_does_not_stop_the_others(tmp_path, monkeypatch):
    source = tmp_path / "Input"
    destination = tmp_path / "Organized"
    make_files(source, ["bad.pdf", "good.pdf"])

    real_move = shutil.move

    def failing_move(src, dst):
        if Path(src).name == "bad.pdf":
            raise OSError("simulated disk error")
        return real_move(src, dst)

    monkeypatch.setattr(organizer.shutil, "move", failing_move)

    results = organize_files(source, destination, dry_run=False)
    by_file = {r["file"]: r for r in results}

    assert by_file["bad.pdf"]["status"] == "Error"
    assert "simulated disk error" in by_file["bad.pdf"]["message"]
    assert by_file["good.pdf"]["status"] == "Moved"
    assert (destination / "Documents" / "good.pdf").exists()
    assert (source / "bad.pdf").exists()  # the failed file stays where it was


# invalid inputs

def test_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        organize_files(tmp_path / "nope", tmp_path / "Organized")


def test_destination_same_as_source_raises(tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["report.pdf"])

    with pytest.raises(ValueError):
        organize_files(source, source, dry_run=False)
    assert (source / "report.pdf").exists()


def test_destination_inside_source_raises(tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["report.pdf"])

    with pytest.raises(ValueError):
        organize_files(source, source / "Organized", dry_run=False)
    assert (source / "report.pdf").exists()


def test_destination_that_is_a_file_raises(tmp_path):
    source = tmp_path / "Input"
    make_files(source, ["report.pdf"])
    not_a_folder = tmp_path / "file.txt"
    not_a_folder.write_text("I am a file")

    with pytest.raises(NotADirectoryError):
        organize_files(source, not_a_folder, dry_run=False)
