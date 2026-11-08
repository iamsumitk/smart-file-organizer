# Smart File Organizer

A Python desktop app that scans a folder, sorts its files into category folders such as Documents, Images and Videos, can also sort them by year, and finds duplicate files.

The app never deletes files and always shows a preview before anything is moved.

## Project status

Written in 2024 as a learning project, updated recently. 
Tested with Python 3.12 on Linux Mint.

## Features

- Sorts files into categories based on their extension: Documents, Images, Videos, Audio, Archives, Code and Others
- Optional year folders, based on each file's modified date (for example `Images/2024/photo.jpg`)
- Preview of every planned move before anything changes
- Never overwrites: if a name is already taken, the file is saved as `photo_1.jpg`, `photo_2.jpg`, and so on
- Finds duplicate files by comparing SHA-256 hashes. Duplicates are shown, never deleted
- Basic graphical interface (Tkinter) and a terminal version
- File work runs in the background, so the window stays responsive
- 52 automated tests (pytest)

## Requirements

- Python 3 (tested with Python 3.12)
- Tkinter, for the graphical interface:
  - **Windows:** Tkinter is included with Python
  - **Debian, Ubuntu or Linux Mint:** install it with:
    ```bash
    sudo apt install python3-tk
    ```

To check that Tkinter works, run this command. A small test window should open:

```bash
python -m tkinter
```

The Python packages the project needs are listed in `requirements.txt`. They are installed in the setup steps below.

## Setup

Open a terminal in the project folder (the folder that contains `main.py`), then run:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the app

Run these commands from the project folder, with the virtual environment active.

Graphical interface:

```bash
python -m gui.app
```

Terminal version:

```bash
python main.py
```

## Using the graphical interface

1. Click **Browse...** to choose the folder to organize (source) and the folder to put the sorted files in (destination).
2. Tick **Also sort into year folders** if you want year folders.
3. Click **Find Duplicates** to list identical files. Nothing is deleted.
4. Click **Preview** to see every planned move in the table. Nothing is moved.
5. Click **Organize**. The app shows a preview, asks you to confirm, and only then moves the files.
6. When it finishes, the results appear in the table.

The table has a horizontal scrollbar, so long destination paths can be read in full.

## How it works

```
1. Choose the SOURCE and DESTINATION folders
        |
2. SCAN the source (top-level files only; subfolders are skipped)
        |
3. FIND DUPLICATES (SHA-256)  -> shown to you, nothing deleted
        |
4. PREVIEW the plan (dry run) -> for each file: category, optional year folder,
        |                         final name (_1, _2 added if the name is taken)
        |                         nothing is moved yet
        |
5. CONFIRM -> "Move N files?" -> no: stop, nothing changes
        |
6. MOVE each file; a file that fails is marked Error and the rest continue
```

## Project structure

```
Smart File Organizer/
  main.py                    terminal version
  gui/
    app.py                   graphical interface (Tkinter)
  organizer/
    scanner.py               lists the files in a folder
    classifier.py            maps file extensions to categories
    organizer.py             plans and performs the moves
    duplicate_detector.py    finds identical files
  tests/                     automated tests
  pytest.ini                 pytest settings
  requirements.txt           Python packages needed
```

Each function has a short comment describing what it does.

## Running the tests

```bash
pytest -v
```

All tests use temporary folders, so your own files are never touched.
