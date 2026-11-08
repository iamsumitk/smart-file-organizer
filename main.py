from organizer.duplicate_detector import find_duplicates
from organizer.organizer import organize_files


# Asks a yes/no question in the terminal again and again until the answer is y/n.
# Returns True for yes and False for no
def ask_yes_no(question):
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


# Asks for a folder path in the terminal until something non-empty is typed, then returns it
def ask_folder(question):
    while True:
        path = input(f"{question}: ").strip()
        if path:
            return path
        print("Please enter a folder path.")


# Prints one line per result: status, file name and destination. Prints the error message on a second line if there is one
def print_results(results):
    for result in results:
        print(f"  {result['status']:<8} {result['file']:<25} -> {result['destination']}")
        if result["message"]:
            print(f"           {result['message']}")


# Terminal flow: ask for the folders, list duplicates, show a preview, ask for confirmation,
# then move the files. Nothing moves until the user says yes
def main():
    source = ask_folder("Folder to organize (full path)")
    destination = ask_folder("Destination folder (full path)")
    by_date = ask_yes_no("Also sort into year folders by file date?")

    # Step 1: report duplicates. Nothing is deleted
    try:
        duplicate_groups = find_duplicates(source)
    except (FileNotFoundError, NotADirectoryError) as error:
        print("Error:", error)
        return

    if duplicate_groups:
        print(f"\nFound {len(duplicate_groups)} group(s) of duplicate files (not deleted):")
        for group in duplicate_groups:
            for path in group:
                print("   ", path)
            print()
    else:
        print("\nNo duplicate files found.")

    # Step 2: preview. dry_run=True changes nothing
    try:
        plan = organize_files(source, destination, dry_run=True, by_date=by_date)
    except (FileNotFoundError, NotADirectoryError, ValueError) as error:
        print("Error:", error)
        return

    if not plan:
        print("No files to organize.")
        return

    print("\nPREVIEW (nothing has been moved yet):")
    print_results(plan)

    # Step 3: confirm, then move
    if not ask_yes_no("\nMove these files now?"):
        print("Cancelled. Nothing was moved.")
        return

    results = organize_files(source, destination, dry_run=False, by_date=by_date)

    print("\nRESULTS:")
    print_results(results)

    moved = sum(1 for r in results if r["status"] == "Moved")
    errors = sum(1 for r in results if r["status"] == "Error")
    print(f"\nMoved: {moved}   Errors: {errors}")


if __name__ == "__main__":
    main()
