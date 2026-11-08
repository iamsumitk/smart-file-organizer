import pytest

from organizer.classifier import FILE_CATEGORIES, classify_file


def test_pdf_is_document():
    assert classify_file(".pdf") == "Documents"


def test_jpg_is_image():
    assert classify_file(".jpg") == "Images"


def test_mp4_is_video():
    assert classify_file(".mp4") == "Videos"


def test_unknown_extension():
    assert classify_file(".xyz") == "Others"


def test_uppercase_extension():
    assert classify_file(".PDF") == "Documents"


def test_empty_extension_is_others():
    assert classify_file("") == "Others"


@pytest.mark.parametrize(
    "extension, expected",
    [
        (".mp3", "Audio"),
        (".zip", "Archives"),
        (".py", "Code"),
        (".docx", "Documents"),
    ],
)
def test_other_categories(extension, expected):
    assert classify_file(extension) == expected


def test_every_listed_extension_classifies_to_its_category():
    for category, extensions in FILE_CATEGORIES.items():
        for extension in extensions:
            assert classify_file(extension) == category


def test_no_extension_is_listed_in_two_categories():
    seen = {}
    for category, extensions in FILE_CATEGORIES.items():
        for extension in extensions:
            assert extension not in seen, (
                f"{extension} is in both {seen.get(extension)} and {category}"
            )
            seen[extension] = category
