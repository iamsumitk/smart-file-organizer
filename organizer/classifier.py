FILE_CATEGORIES = {
    "Documents": [
        ".pdf", ".doc", ".docx", ".txt",
        ".ppt", ".pptx", ".xls", ".xlsx",
        ".csv",
    ],
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif",
        ".svg", ".webp", ".bmp",
    ],
    "Videos": [
        ".mp4", ".mkv", ".avi", ".mov",
    ],
    "Audio": [
        ".mp3", ".wav", ".flac", ".aac",
    ],
    "Archives": [
        ".zip", ".rar", ".7z", ".tar", ".gz",
    ],
    "Code": [
        ".py", ".js", ".ts", ".java",
        ".cpp", ".c", ".html", ".css",
        ".json",
    ],
}

DEFAULT_CATEGORY = "Others"

# Reverse lookup i.e .pdf returns "Documents"
# classify_file() is a single dictionary lookup per call
extension_to_category = {
    extension: category
    for category, extensions in FILE_CATEGORIES.items()
    for extension in extensions
}


# Returns the category name for a file extension, ignoring case (".PDF" and ".pdf" both give "Documents")
# Any extension not in FILE_CATEGORIES returns "Others"
def classify_file(extension):
   
    return extension_to_category.get(extension.lower(), DEFAULT_CATEGORY)
