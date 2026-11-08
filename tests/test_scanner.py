from datetime import datetime

import pytest

from organizer.scanner import scan_directory


def test_scans_files_and_skips_subfolders(tmp_path):
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "photo.JPG").write_bytes(b"\x00" * 10)
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "inside.txt").write_text("nested")

    files = scan_directory(tmp_path)
    names = sorted(f["name"] for f in files)

    assert names == ["notes.txt", "photo.JPG"]


def test_returns_expected_fields(tmp_path):
    (tmp_path / "notes.txt").write_text("hello")

    (info,) = scan_directory(tmp_path)

    assert info["name"] == "notes.txt"
    assert info["path"] == str(tmp_path / "notes.txt")
    assert info["extension"] == ".txt"
    assert info["size"] == 5
    assert isinstance(info["modified"], datetime)


def test_extension_is_lowercased(tmp_path):
    (tmp_path / "photo.JPG").write_bytes(b"x")

    (info,) = scan_directory(tmp_path)

    assert info["extension"] == ".jpg"


def test_empty_folder_returns_empty_list(tmp_path):
    assert scan_directory(tmp_path) == []


def test_missing_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan_directory(tmp_path / "does_not_exist")


def test_file_path_raises_not_a_directory(tmp_path):
    file_path = tmp_path / "notes.txt"
    file_path.write_text("hello")

    with pytest.raises(NotADirectoryError):
        scan_directory(file_path)
