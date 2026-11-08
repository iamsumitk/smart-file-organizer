import hashlib

import pytest

from organizer.duplicate_detector import calculate_file_hash, find_duplicates


def test_hash_matches_hashlib(tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"some contents")

    assert calculate_file_hash(file_path) == hashlib.sha256(b"some contents").hexdigest()


def test_hash_is_correct_for_file_larger_than_one_chunk(tmp_path):
    # 64 KB chunk size; this file spans several chunks plus a remainder.
    content = bytes(range(256)) * 1000
    file_path = tmp_path / "big.bin"
    file_path.write_bytes(content)

    assert calculate_file_hash(file_path) == hashlib.sha256(content).hexdigest()


def test_identical_files_with_different_names_are_grouped(tmp_path):
    (tmp_path / "photo.jpg").write_bytes(b"same bytes")
    (tmp_path / "photo_copy.jpg").write_bytes(b"same bytes")
    (tmp_path / "unique.jpg").write_bytes(b"different bytes")

    groups = find_duplicates(tmp_path)

    assert groups == [[
        str(tmp_path / "photo.jpg"),
        str(tmp_path / "photo_copy.jpg"),
    ]]


def test_no_duplicates_returns_empty_list(tmp_path):
    (tmp_path / "a.txt").write_text("one")
    (tmp_path / "b.txt").write_text("two")

    assert find_duplicates(tmp_path) == []


def test_empty_folder_returns_empty_list(tmp_path):
    assert find_duplicates(tmp_path) == []


def test_several_groups_are_each_reported(tmp_path):
    (tmp_path / "a1.txt").write_text("alpha")
    (tmp_path / "a2.txt").write_text("alpha")
    (tmp_path / "b1.txt").write_text("beta")
    (tmp_path / "b2.txt").write_text("beta")
    (tmp_path / "b3.txt").write_text("beta")

    groups = find_duplicates(tmp_path)

    assert len(groups) == 2
    assert sorted(len(group) for group in groups) == [2, 3]


def test_subfolders_are_not_searched(tmp_path):
    (tmp_path / "top.txt").write_text("same")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.txt").write_text("same")

    assert find_duplicates(tmp_path) == []


def test_detection_does_not_delete_anything(tmp_path):
    (tmp_path / "a.txt").write_text("same")
    (tmp_path / "b.txt").write_text("same")

    find_duplicates(tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.txt", "b.txt"]


def test_missing_folder_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_duplicates(tmp_path / "nope")
