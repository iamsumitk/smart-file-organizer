import logging
import shutil
from pathlib import Path

from organizer.classifier import classify_file
from organizer.scanner import scan_directory

logger = logging.getLogger(__name__)


# Returns a file path that is free to use: "photo.jpg", then "photo_1.jpg", "photo_2.jpg"...
# Also skips names listed in `taken`, which are reserved for files planned in the same run.
def get_unique_path(destination, taken=()):

    
    destination = Path(destination)
    if not destination.exists() and destination not in taken:
        return destination

    counter = 1
    while True:
        new_path = destination.with_name(
            f"{destination.stem}_{counter}{destination.suffix}"
        )
        if not new_path.exists() and new_path not in taken:
            return new_path
        counter += 1


# Checks the destination is safe to use: it must not be a file, the source folder itself,
# or inside the source folder. Raises an error if any of these is true.
def validate_destination(source, destination):

    if destination.exists() and not destination.is_dir():
        raise NotADirectoryError(
            f"Destination exists and is not a folder: {destination}"
        )

    resolved_source = source.resolve()
    resolved_destination = destination.resolve()

    if resolved_destination == resolved_source:
        raise ValueError("Destination must be different from the source folder.")
    if resolved_source in resolved_destination.parents:
        raise ValueError("Destination must not be inside the source folder.")


# organizer files into appropriate folders
#  if dry_run=True then just show what would happen
#  if dry_run=False then actually move files to destination
def organize_files(source, destination, dry_run=True, by_date=False):
    
    source = Path(source)
    destination = Path(destination)

    files = scan_directory(source) 
    validate_destination(source, destination)

    results = []
    reserved = set()  # destinations already planned in this run

    for info in sorted(files, key=lambda item: item["name"]):
        category = classify_file(info["extension"])
        category_folder = destination / category
        if by_date:
            category_folder = category_folder / str(info["modified"].year)
        target = get_unique_path(category_folder / info["name"], taken=reserved)
        reserved.add(target)

        result = {
            "file": info["name"],
            "category": category,
            "destination": str(target),
            "status": "Planned",
            "message": "",
        }

        if not dry_run:
            try:
                category_folder.mkdir(parents=True, exist_ok=True)
                shutil.move(info["path"], target)
                result["status"] = "Moved"
            except OSError as error:
                result["status"] = "Error"
                result["message"] = str(error)
                logger.error("Could not move %s: %s", info["name"], error)

        results.append(result)

    return results
