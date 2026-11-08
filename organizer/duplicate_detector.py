import hashlib
import logging

from organizer.scanner import scan_directory

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024  # read files in 64 KB pieces so large files fit in memory


# Computes the SHA-256 fingerprint of a file's contents. Two files with the same fingerprint are duplicate
# The file is read in 64 KB chunks, so large files do not need to fit in memory
def calculate_file_hash(file_path):
   
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

# find files directly inside directory whose contents are same
# it never deletes or moves anything
def find_duplicates(directory):
    
    files = scan_directory(directory)  

    hashes = {}  # digest -> list of paths with that digest
    for info in files:
        try:
            digest = calculate_file_hash(info["path"])
        except OSError as error:
            logger.warning("Skipping %s, could not read it: %s", info["path"], error)
            continue
        hashes.setdefault(digest, []).append(info["path"])

    groups = [sorted(paths) for paths in hashes.values() if len(paths) > 1]
    return sorted(groups)
