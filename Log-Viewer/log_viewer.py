import csv
import math
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)
from matplotlib.figure import Figure


TIMESTAMP_COLUMN = "timestamp"
VALUE_COLUMN = "measured_value_kg"


def read_log(path):
    timestamps = []
    values = []

    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {TIMESTAMP_COLUMN, VALUE_COLUMN}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                "The CSV must contain 'timestamp' and 'measured_value_kg' columns."
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                timestamp = datetime.fromisoformat(row[TIMESTAMP_COLUMN].strip())
                value = float(row[VALUE_COLUMN])
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid timestamp or weight on CSV row {line_number}."
                ) from exc

            if not math.isfinite(value):
                raise ValueError(
                    f"Weight on CSV row {line_number} is not a finite number."
                )
            timestamps.append(timestamp)
            values.append(value)

    if not values:
        raise ValueError("The CSV contains no weight readings.")
    return timestamps, values


class LogViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Load Cell Log Viewer")
        self.root.minsize(800, 520)

        self.default_directory = Path(__file__).resolve().parent.parent / "Serial-Logger"
        self.path_var = tk.StringVar(value="No log loaded.")
        self.summary_var = tk.StringVar(value="Open a logger CSV to view its graph.")

        controls = ttk.Frame(root, padding=10)
        controls.pack(fill="x")
        self.open_button = ttk.Button(
            controls, text="Open CSV...", command=self.open_csv
        )
        self.open_button.pack(side="left")
        ttk.Label(
            controls, textvariable=self.path_var, anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=(10, 0))

        plot_frame = ttk.Frame(root, padding=(10, 0, 10, 10))
        plot_frame.pack(fill="both", expand=True)
        self.figure = Figure(figsize=(8, 5), dpi=100, tight_layout=True)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.toolbar = NavigationToolbar2Tk(
            self.canvas, plot_frame, pack_toolbar=False
        )
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")

        ttk.Label(
            root,
            textvariable=self.summary_var,
            padding=(10, 0, 10, 10),
        ).pack(fill="x")
        self._show_empty_plot()

    def open_csv(self):
        initial_directory = (
            self.default_directory
            if self.default_directory.is_dir()
            else Path.cwd()
        )
        selected = filedialog.askopenfilename(
            title="Open load-cell log",
            initialdir=str(initial_directory),
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not selected:
            return

        path = Path(selected)
        try:
            timestamps, values = read_log(path)
        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
            messagebox.showerror("Could not open log", str(exc))
            return

        self._plot_log(path, timestamps, values)

    def _show_empty_plot(self):
        self.axes.clear()
        self.axes.set_title("Load Cell Log")
        self.axes.set_xlabel("Time")
        self.axes.set_ylabel("Measured weight (kg)")
        self.axes.grid(True, alpha=0.3)
        self.canvas.draw_idle()

    def _plot_log(self, path, timestamps, values):
        maximum_index = max(range(len(values)), key=values.__getitem__)
        maximum_time = timestamps[maximum_index]
        maximum_value = values[maximum_index]

        self.axes.clear()
        self.axes.plot(
            timestamps,
            values,
            color="#1976d2",
            linewidth=1.5,
            label="_nolegend_",
        )
        self.axes.plot(
            [],
            [],
            linestyle="none",
            label=f"Maximum: {maximum_value:.2f} kg",
        )
        self.axes.set_title(path.name)
        self.axes.set_xlabel("Time")
        self.axes.set_ylabel("Measured weight (kg)")
        date_locator = mdates.AutoDateLocator()
        self.axes.xaxis.set_major_locator(date_locator)
        self.axes.xaxis.set_major_formatter(mdates.ConciseDateFormatter(date_locator))
        self.axes.grid(True, alpha=0.3)
        self.axes.legend(loc="upper left")
        self.figure.autofmt_xdate()

        self.path_var.set(str(path))
        self.summary_var.set(
            f"Readings: {len(values)}    "
            f"Maximum: {maximum_value:.2f} kg at "
            f"{maximum_time.isoformat(sep=' ', timespec='milliseconds')}"
        )
        self.canvas.draw_idle()


if __name__ == "__main__":
    root = tk.Tk()
    LogViewerApp(root)
    root.mainloop()
