import queue
import threading
import tkinter as tk
from collections import Counter
from tkinter import filedialog, messagebox, ttk

from organizer.duplicate_detector import find_duplicates
from organizer.organizer import organize_files

RESULT_COLUMNS = ("file", "category", "status", "destination")


# Counts the results: total, planned, moved, errors, and how many files are in each category.
# Used to fill the statistics panel.
def summarize_results(results):

    statuses = Counter(result["status"] for result in results)
    categories = Counter(result["category"] for result in results)
    return {
        "total": len(results),
        "planned": statuses.get("Planned", 0),
        "moved": statuses.get("Moved", 0),
        "errors": statuses.get("Error", 0),
        "by_category": dict(sorted(categories.items())),
    }


class OrganizerApp(tk.Tk):
    POLL_MS = 100

    # Creates the window, the shared state (folder fields, year checkbox, status text, job queue)
    # then builds the controls
    def __init__(self):
        super().__init__()
        self.title("Smart File Organizer")
        self.minsize(820, 520)

        self._jobs = queue.Queue()
        self._busy = False

        self.source_var = tk.StringVar()
        self.destination_var = tk.StringVar()
        self.by_date_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Choose a source folder to begin.")
        self.stats_var = tk.StringVar(value="")

        self.build_widgets()

    #  layout 

    # Lays out every control: the two folder fields with Browse buttons, the year-folder checkbox,
    # the action buttons, the results table with scrollbars
    def build_widgets(self):
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Source folder").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=6)
        self.browse_source_btn = ttk.Button(frame, text="Browse…", command=self.browse_source)
        self.browse_source_btn.grid(row=0, column=2)

        ttk.Label(frame, text="Destination folder").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.destination_var).grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        self.browse_dest_btn = ttk.Button(frame, text="Browse…", command=self.browse_destination)
        self.browse_dest_btn.grid(row=1, column=2, pady=6)

        ttk.Checkbutton(
            frame, text="Also sort into year folders (by file date)", variable=self.by_date_var
        ).grid(row=2, column=1, sticky="w", padx=6)

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=3, sticky="w", pady=10)
        self.duplicates_btn = ttk.Button(buttons, text="Find Duplicates", command=self.find_duplicates)
        self.preview_btn = ttk.Button(buttons, text="Preview", command=self.preview)
        self.organize_btn = ttk.Button(buttons, text="Organize", command=self.organize)
        for button in (self.duplicates_btn, self.preview_btn, self.organize_btn):
            button.pack(side="left", padx=(0, 8))
        self._action_buttons = (
            self.browse_source_btn, self.browse_dest_btn,
            self.duplicates_btn, self.preview_btn, self.organize_btn,
        )

        table_frame = ttk.Frame(frame)
        table_frame.grid(row=4, column=0, columnspan=3, sticky="nsew")
        frame.rowconfigure(4, weight=1)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.table = ttk.Treeview(table_frame, columns=RESULT_COLUMNS, show="headings")
        # stretch=False keeps each column at its set width, so long paths
        # overflow and the horizontal scrollbar can reach them
        for column, width in zip(RESULT_COLUMNS, (220, 110, 90, 900)):
            self.table.heading(column, text=column.capitalize())
            self.table.column(column, width=width, anchor="w", stretch=False)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.table.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        ttk.Label(frame, textvariable=self.stats_var, justify="left").grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )
        ttk.Label(frame, textvariable=self.status_var, foreground="gray").grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

    #  helpers

    # Opens a folder picker and puts the chosen folder in the Source field
    def browse_source(self):
        path = filedialog.askdirectory(title="Choose the folder to organize")
        if path:
            self.source_var.set(path)

    # Opens a folder picker and puts the chosen folder in the Destination field
    def browse_destination(self):
        path = filedialog.askdirectory(title="Choose the destination folder")
        if path:
            self.destination_var.set(path)

    # Checks that every folder field has a value
    # If one is empty, shows a warning and returns None
    # Otherwise returns the values with surrounding spaces removed
    def require(self, *values):

        cleaned = [value.strip() for value in values]
        if not all(cleaned):
            messagebox.showwarning("Missing folder", "Please choose the folder(s) first.")
            return None
        return cleaned

    # Switches the app between busy and idle. When busy, the buttons are disabled and the cursor is a wait cursor
    # An optional message is shown in the status line
    def set_busy(self, busy, message=""):
        self._busy = busy
        state = "disabled" if busy else "normal"
        for button in self._action_buttons:
            button.configure(state=state)
        if message:
            self.status_var.set(message)
        self.configure(cursor="watch" if busy else "")

    # Runs a slow task in a separate thread so the window stays responsive. Checks for the result every
    # 100 ms, then calls on_success(result) on the window's own thread
    def run_in_background(self, task, on_success, working_message):
        if self._busy:
            return
        self.set_busy(True, working_message)

        # Runs in the background thread: performs the task and puts its result (or its error) in the queue
        def worker():
            try:
                self._jobs.put(("ok", task()))
            except Exception as error:  # reported to the user, never silently dropped
                self._jobs.put(("error", error))

        threading.Thread(target=worker, daemon=True).start()
        self.after(self.POLL_MS, lambda: self.poll(on_success))

    # Checks the job queue. If nothing is ready, schedules another check. When a result arrives, leaves busy
    # mode and calls on_success with it, or shows an error message
    def poll(self, on_success):
        try:
            status, value = self._jobs.get_nowait()
        except queue.Empty:
            self.after(self.POLL_MS, lambda: self.poll(on_success))
            return

        self.set_busy(False)
        if status == "ok":
            on_success(value)
        else:
            self.status_var.set("Something went wrong.")
            messagebox.showerror("Error", str(value))

    # Replaces the rows of the results table with the given results, then updates the statistics
    def show_results(self, results):
        self.table.delete(*self.table.get_children())
        for result in results:
            self.table.insert(
                "", "end",
                values=(result["file"], result["category"], result["status"], result["destination"]),
            )
        self.show_stats(results)

    # Writes the statistics label: totals, per-category counts, and the number of duplicate groups if known
    def show_stats(self, results, duplicate_groups=None):
        summary = summarize_results(results)
        lines = [
            f"Files: {summary['total']}   Planned: {summary['planned']}   "
            f"Moved: {summary['moved']}   Errors: {summary['errors']}"
        ]
        if summary["by_category"]:
            per_category = ", ".join(f"{name}: {count}" for name, count in summary["by_category"].items())
            lines.append(f"By category: {per_category}")
        if duplicate_groups is not None:
            lines.append(f"Duplicate groups: {len(duplicate_groups)} (not deleted)")
        self.stats_var.set("\n".join(lines))

    #  actions

    # Button action for "Find Duplicates": looks for identical files in the source folder in the background
    # then shows the groups. Nothing is deleted
    def find_duplicates(self):
        paths = self.require(self.source_var.get())
        if not paths:
            return
        (source,) = paths

        # Runs when the duplicate search finishes: shows the groups in a message box and the status line
        def on_success(groups):
            if groups:
                self.status_var.set(f"Found {len(groups)} group(s) of duplicate files. Nothing was deleted.")
                details = "\n\n".join("\n".join(group) for group in groups)
                messagebox.showinfo("Duplicate files", f"Identical files (not deleted):\n\n{details}")
            else:
                self.status_var.set("No duplicate files found.")
                messagebox.showinfo("Duplicate files", "No duplicate files found.")
            self.stats_var.set(f"Duplicate groups: {len(groups)} (not deleted)")

        self.run_in_background(lambda: find_duplicates(source), on_success, "Looking for duplicates…")

    # Button action for "Preview": builds the move plan in the background and shows it in the table
    # Nothing is moved
    def preview(self):
        paths = self.require(self.source_var.get(), self.destination_var.get())
        if not paths:
            return
        source, destination = paths
        by_date = self.by_date_var.get()

        # Runs when the preview is ready: shows the planned moves in the table
        def on_success(plan):
            self.show_results(plan)
            self.status_var.set("Preview ready. Nothing has been moved yet.")

        self.run_in_background(
            lambda: organize_files(source, destination, dry_run=True, by_date=by_date),
            on_success,
            "Building preview…",
        )

    # Button action for "Organize": builds a preview first, asks the user to confirm with the file count
    # and only then moves the files
    def organize(self):
        paths = self.require(self.source_var.get(), self.destination_var.get())
        if not paths:
            return
        source, destination = paths
        by_date = self.by_date_var.get()

        # Runs when the preview for "Organize" is ready: shows it, asks for confirmation
        # and starts the real move only if the user says yes
        def on_preview(plan):
            self.show_results(plan)
            if not plan:
                self.status_var.set("No files to organize.")
                return
            confirmed = messagebox.askyesno(
                "Confirm",
                f"Move {len(plan)} file(s) into:\n{destination}\n\nContinue?",
            )
            if not confirmed:
                self.status_var.set("Cancelled. Nothing was moved.")
                return
            self.move_files(source, destination, by_date)

        self.run_in_background(
            lambda: organize_files(source, destination, dry_run=True, by_date=by_date),
            on_preview,
            "Building preview…",
        )

    # Moves the files in the background, then shows the outcome
    def move_files(self, source, destination, by_date):
        # Runs in the background thread: moves the files for real
        def task():
            return organize_files(source, destination, dry_run=False, by_date=by_date)

        # Runs when the move finishes: shows the final results, and a warning if any file failed
        def on_success(results):
            self.show_results(results)
            summary = summarize_results(results)
            self.status_var.set(f"Done. Moved {summary['moved']} file(s).")
            if summary["errors"]:
                messagebox.showwarning(
                    "Finished with errors",
                    f"Moved {summary['moved']} file(s), {summary['errors']} could not be moved.",
                )

        self.run_in_background(task, on_success, "Moving files…")


# Starts the app: creates the window and runs its event loop until the window is closed
def main():
    app = OrganizerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
