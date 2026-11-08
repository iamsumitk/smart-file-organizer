from datetime import datetime
from pathlib import Path

# Scans a directory and returns information about all files inside it (subfolders not included)
# returns list of dict like name, path, extension, size, last modified.
def scan_directory(directory_path):
 
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files = []

    for item in directory.iterdir():
        if not item.is_file():
            continue

        stats = item.stat()  # one system call, reused for size and date
        files.append({
            "name": item.name,
            "path": str(item),
            "extension": item.suffix.lower(),
            "size": stats.st_size,
            "modified": datetime.fromtimestamp(stats.st_mtime),
        })

    return files
