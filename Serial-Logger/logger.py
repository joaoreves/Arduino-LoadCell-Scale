import csv
import queue
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import serial
from serial.tools import list_ports


BAUD_RATE = 115200
READ_TIMEOUT = 0.2
GRAPH_WINDOWS = ("10", "30", "60", "120")
READING_STALE_SECONDS = 2.0


def _default_output_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


class SerialLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Load Cell Serial Logger")
        self.root.minsize(720, 480)

        self.events = queue.Queue()
        self.stop_event = None
        self.reader_thread = None
        self.last_error = None
        self.closing = False
        self.points = deque()
        self.connected = False
        self.has_reading = False
        self.last_reading_at = None
        self.is_logging = False
        self.log_started_at = None
        self.csv_file = None
        self.csv_writer = None
        self.current_output_path = None
        self.disconnecting = False

        self.port_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(
            value=str(_default_output_directory())
        )
        self.window_var = tk.StringVar(value="30")
        self.status_var = tk.StringVar(value="Select a serial port.")
        self.file_var = tk.StringVar(value="Not logging.")
        self.weight_var = tk.StringVar(value="--.-- kg")

        self._create_widgets()
        self.refresh_ports()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._process_events)

    def _create_widgets(self):
        controls = ttk.Frame(self.root, padding=10)
        controls.pack(fill="x")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Serial port:").grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=4
        )
        self.port_combo = ttk.Combobox(
            controls, textvariable=self.port_var, state="readonly", width=18
        )
        self.port_combo.grid(row=0, column=1, sticky="ew", pady=4)
        self.refresh_button = ttk.Button(
            controls, text="Refresh ports", command=self.refresh_ports
        )
        self.refresh_button.grid(row=0, column=2, padx=6, pady=4)

        ttk.Label(controls, text="Output directory:").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=4
        )
        self.output_entry = ttk.Entry(
            controls, textvariable=self.output_dir_var
        )
        self.output_entry.grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        self.browse_button = ttk.Button(
            controls, text="Browse...", command=self.choose_output_directory
        )
        self.browse_button.grid(row=1, column=4, padx=(6, 0), pady=4)

        self.connect_button = ttk.Button(
            controls, text="Connect", command=self.connect
        )
        self.connect_button.grid(row=2, column=1, padx=(0, 6), pady=4, sticky="w")
        self.start_button = ttk.Button(
            controls,
            text="Start logging",
            command=self.start_logging,
            state="disabled",
        )
        self.start_button.grid(row=2, column=2, padx=6, pady=4, sticky="w")
        self.stop_button = ttk.Button(
            controls,
            text="Stop logging",
            command=self.stop_logging,
            state="disabled",
        )
        self.stop_button.grid(row=2, column=3, padx=6, pady=4, sticky="w")
        self.disconnect_button = ttk.Button(
            controls,
            text="Disconnect",
            command=self.disconnect,
            state="disabled",
        )
        self.disconnect_button.grid(row=2, column=4, pady=4, sticky="w")

        graph_controls = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        graph_controls.pack(fill="x")
        ttk.Label(graph_controls, text="Graph window:").pack(side="left")
        self.window_combo = ttk.Combobox(
            graph_controls,
            textvariable=self.window_var,
            values=GRAPH_WINDOWS,
            state="readonly",
            width=6,
        )
        self.window_combo.pack(side="left", padx=6)
        ttk.Label(graph_controls, text="seconds").pack(side="left")
        ttk.Label(
            graph_controls,
            textvariable=self.weight_var,
            font=("Segoe UI", 18, "bold"),
        ).pack(side="right")

        self.graph = tk.Canvas(
            self.root,
            background="white",
            highlightthickness=1,
            highlightbackground="#b8b8b8",
        )
        self.graph.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.graph.bind("<Configure>", self._on_graph_resize)

        footer = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var).pack(anchor="w")
        ttk.Label(footer, textvariable=self.file_var).pack(anchor="w")

    def refresh_ports(self):
        try:
            ports = sorted(list_ports.comports(), key=lambda port: port.device)
        except serial.SerialException as exc:
            self.status_var.set(f"Could not scan serial ports: {exc}")
            return

        available = [port.device for port in ports]
        self.port_combo["values"] = available
        if self.port_var.get() not in available:
            self.port_var.set(available[0] if available else "")

        if available:
            self.status_var.set(f"Found {len(available)} serial port(s).")
        else:
            self.status_var.set("No serial ports found. Connect the Arduino and refresh.")

    def choose_output_directory(self):
        current = Path(self.output_dir_var.get()).expanduser()
        initial_dir = current if current.is_dir() else _default_output_directory()
        selected = filedialog.askdirectory(
            title="Choose output directory",
            initialdir=str(initial_dir),
        )
        if selected:
            self.output_dir_var.set(selected)

    def _new_output_path(self, output_dir):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"scale_{timestamp}.csv"
        suffix = 1
        while path.exists():
            path = output_dir / f"scale_{timestamp}_{suffix}.csv"
            suffix += 1
        return path

    def connect(self):
        port_name = self.port_var.get()
        if not port_name:
            messagebox.showerror("No serial port", "Select an available serial port.")
            return

        self.last_error = None
        self.connected = False
        self.has_reading = False
        self.last_reading_at = None
        self.disconnecting = False
        self.points.clear()
        self.weight_var.set("--.-- kg")
        self.file_var.set("Not logging.")
        self.graph.delete("all")
        self.stop_event = threading.Event()
        self.reader_thread = threading.Thread(
            target=self._read_serial,
            args=(port_name, self.stop_event),
            daemon=True,
        )
        self.status_var.set(f"Connecting to {port_name}...")
        self._update_controls()
        self.reader_thread.start()

    def _read_serial(self, port_name, stop_event):
        try:
            with serial.Serial(
                port_name, BAUD_RATE, timeout=READ_TIMEOUT
            ) as port:
                if stop_event.wait(2):
                    return

                self.events.put(("connected", port_name))
                while not stop_event.is_set():
                    line = port.readline().decode(
                        "utf-8", errors="replace"
                    ).strip()
                    if not line:
                        continue

                    try:
                        value = float(line)
                    except ValueError:
                        continue

                    timestamp = datetime.now().astimezone().isoformat(
                        timespec="milliseconds"
                    )
                    self.events.put(
                        ("reading", (time.monotonic(), timestamp, value))
                    )
        except (serial.SerialException, OSError) as exc:
            self.events.put(("error", str(exc)))
        finally:
            self.events.put(("disconnected", None))

    def start_logging(self):
        if not self.connected or not self.has_reading:
            self.status_var.set("Connect and wait for a live reading before logging.")
            return

        if (
            self.last_reading_at is None
            or time.monotonic() - self.last_reading_at > READING_STALE_SECONDS
        ):
            self.status_var.set("No recent reading. Logging is not ready to start.")
            self._update_controls()
            return

        output_dir = Path(self.output_dir_var.get()).expanduser()
        if not output_dir.is_dir():
            messagebox.showerror(
                "Invalid output directory",
                "Choose an existing output directory.",
            )
            return

        output_path = self._new_output_path(output_dir)
        output_file = None
        try:
            output_file = output_path.open(
                "x", newline="", encoding="utf-8"
            )
            writer = csv.writer(output_file)
            writer.writerow(["timestamp", "measured_value_kg"])
            output_file.flush()
        except OSError as exc:
            error_message = str(exc)
            if output_file is not None:
                try:
                    output_file.close()
                except OSError as close_error:
                    error_message += f"\nCould not close the partial file: {close_error}"
            messagebox.showerror("Could not create CSV", error_message)
            return

        self.csv_file = output_file
        self.csv_writer = writer
        self.current_output_path = output_path
        self.log_started_at = time.monotonic()
        self.is_logging = True
        self.file_var.set(f"Saving to: {output_path}")
        self.status_var.set("Logging; live readings continue.")
        self._update_controls()

    def stop_logging(self):
        if not self.is_logging:
            return
        self._finish_logging()
        if self.connected:
            self.status_var.set("Logging stopped; live preview continues.")

    def _finish_logging(self):
        self.is_logging = False
        self.log_started_at = None
        output_file = self.csv_file
        self.csv_file = None
        self.csv_writer = None
        close_error = None
        if output_file is not None:
            try:
                output_file.close()
            except OSError as exc:
                close_error = exc
                self.status_var.set(f"CSV close error: {exc}")
                messagebox.showerror("CSV close error", str(exc))

        if self.current_output_path is not None:
            if close_error is None:
                self.file_var.set(f"Saved: {self.current_output_path}")
            else:
                self.file_var.set(f"CSV may be incomplete: {self.current_output_path}")
        self._update_controls()

    def disconnect(self):
        if self.stop_event is None:
            return
        if self.is_logging:
            self._finish_logging()
        self.disconnecting = True
        self.stop_event.set()
        self.status_var.set("Disconnecting...")
        self._update_controls()

    def _update_controls(self):
        connection_active = self.reader_thread is not None
        recent_reading = (
            self.last_reading_at is not None
            and time.monotonic() - self.last_reading_at <= READING_STALE_SECONDS
        )
        self.port_combo.configure(
            state="disabled" if connection_active else "readonly"
        )
        self.refresh_button.configure(
            state="disabled" if connection_active else "normal"
        )
        self.connect_button.configure(
            state="disabled" if connection_active else "normal"
        )
        self.disconnect_button.configure(
            state=(
                "normal"
                if connection_active and not self.disconnecting
                else "disabled"
            )
        )
        self.start_button.configure(
            state=(
                "normal"
                if self.connected
                and self.has_reading
                and recent_reading
                and not self.is_logging
                else "disabled"
            )
        )
        self.stop_button.configure(
            state="normal" if self.is_logging else "disabled"
        )
        output_state = "disabled" if self.is_logging else "normal"
        self.output_entry.configure(state=output_state)
        self.browse_button.configure(state=output_state)

    def _process_events(self):
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "connected":
                self.connected = True
                self.status_var.set(
                    f"Connected to {payload}; waiting for a valid reading..."
                )
                self._update_controls()
            elif event == "reading":
                sample_time, timestamp, value = payload
                if (
                    self.is_logging
                    and self.log_started_at is not None
                    and sample_time >= self.log_started_at
                ):
                    try:
                        self.csv_writer.writerow([timestamp, value])
                        self.csv_file.flush()
                    except OSError as exc:
                        self._finish_logging()
                        messagebox.showerror("CSV write error", str(exc))

                self.points.append((sample_time, value))
                self.weight_var.set(f"{value:.2f} kg")
                self.has_reading = True
                self.last_reading_at = time.monotonic()
                if self.connected and not self.is_logging:
                    self.status_var.set(
                        "Live preview ready. Check the reading, then start logging."
                    )
                self._update_controls()
            elif event == "error":
                self.last_error = payload
                self.status_var.set(f"Error: {payload}")
            elif event == "disconnected":
                if self.is_logging:
                    self._finish_logging()
                self.connected = False
                self.has_reading = False
                self.last_reading_at = None
                self.disconnecting = False
                self.stop_event = None
                self.reader_thread = None
                if self.last_error is None:
                    if not self.closing:
                        self.status_var.set("Disconnected.")
                else:
                    self.status_var.set(f"Disconnected: {self.last_error}")
                    messagebox.showerror("Serial connection error", self.last_error)
                    self.last_error = None
                self._update_controls()

        if (
            self.connected
            and self.has_reading
            and not self.is_logging
            and (
                self.last_reading_at is None
                or time.monotonic() - self.last_reading_at > READING_STALE_SECONDS
            )
        ):
            self.status_var.set("No recent reading. Logging is not ready to start.")
        self._update_controls()
        self._draw_graph()
        if self.closing and self.reader_thread is None:
            self.root.destroy()
            return
        self.root.after(100, self._process_events)

    def _draw_graph(self):
        self.graph.delete("all")
        width = self.graph.winfo_width()
        height = self.graph.winfo_height()
        left, right, top, bottom = 62, 16, 16, 32
        plot_width = width - left - right
        plot_height = height - top - bottom
        if plot_width <= 0 or plot_height <= 0:
            return

        window_seconds = int(self.window_var.get())
        now = time.monotonic()
        cutoff = now - window_seconds
        while self.points and self.points[0][0] < cutoff:
            self.points.popleft()
        visible = [point for point in self.points if point[0] >= cutoff]

        if visible:
            values = [point[1] for point in visible]
            low, high = min(values), max(values)
            if low == high:
                padding = max(abs(low) * 0.05, 0.5)
            else:
                padding = (high - low) * 0.1
            low -= padding
            high += padding
        else:
            low, high = 0.0, 1.0

        for index in range(5):
            fraction = index / 4
            y = top + fraction * plot_height
            value = high - fraction * (high - low)
            self.graph.create_line(left, y, width - right, y, fill="#e2e2e2")
            self.graph.create_text(
                left - 8, y, text=f"{value:.2f}", anchor="e", fill="#444444"
            )

        self.graph.create_line(left, top, left, height - bottom, fill="#555555")
        self.graph.create_line(
            left, height - bottom, width - right, height - bottom, fill="#555555"
        )
        for index in range(5):
            fraction = index / 4
            x = left + fraction * plot_width
            seconds_ago = window_seconds * (1 - fraction)
            self.graph.create_text(
                x,
                height - bottom + 14,
                text=f"-{seconds_ago:g}s",
                anchor="n",
                fill="#444444",
            )

        if not visible:
            self.graph.create_text(
                left + plot_width / 2,
                top + plot_height / 2,
                text="Waiting for readings...",
                fill="#666666",
            )
            return

        coordinates = []
        for timestamp, value in visible:
            x = left + (timestamp - cutoff) / window_seconds * plot_width
            y = top + (high - value) / (high - low) * plot_height
            coordinates.extend((x, y))
        if len(coordinates) >= 4:
            self.graph.create_line(
                *coordinates, fill="#1976d2", width=2, smooth=False
            )
        else:
            x, y = coordinates
            self.graph.create_oval(
                x - 3, y - 3, x + 3, y + 3, fill="#1976d2", outline=""
            )

    def _on_graph_resize(self, event):
        if event.widget is self.graph:
            self._draw_graph()

    def _on_close(self):
        self.closing = True
        if self.is_logging:
            self._finish_logging()
        if self.stop_event is not None:
            self.disconnecting = True
            self.stop_event.set()
            self._update_controls()
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialLoggerApp(root)
    root.mainloop()
