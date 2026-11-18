## General Agent Rules and Guidelines

- The Project Directory is the present directory (Arduino-LoadCell-Scale) and everything below it
- You are not authorized to read or write outside of the Project Directory. You are only authorized to work in the Project Directory 
- Do not look, access, read or write files in directories other than this one.
- If extra modules, submodules or dependencies are needed, inform the user, tell him what you need to install and why and give him step by step instructions on how to do so
- Do not install or add to the project modules, submodules or dependencies without asking the user
- Do not commit changes without asking the user
- The code is pushed into a public repo. Make sure not include any personal information, such as names, local paths, etc...

## Project Notes

- `Serial-Logger/logger.py` is a Tkinter GUI that reads numeric weight values from a selected serial port at 115200 baud. It uses `pyserial`; the GUI, including its live graph, uses Python's standard-library Tkinter and Canvas.
- `Log-Viewer/log_viewer.py` is a Tkinter CSV viewer using Matplotlib. It reads the logger's `timestamp` and `measured_value_kg` columns, graphs weight over time, and marks the maximum reading.
- The app has a COM-port dropdown with a manual refresh button, an editable output directory with a folder picker, and graph windows of 10, 30, 60, or 120 seconds.
- Connection and capture are separate: **Connect** opens the selected port and starts a live preview without writing a CSV; **Start logging** is enabled only after a recent valid numeric reading arrives. **Stop logging** closes the current CSV but keeps preview active; **Disconnect** closes the serial port. A reading older than two seconds makes logging unavailable until readings resume.
- Each capture creates a timestamped CSV with `timestamp` and `measured_value_kg` columns. The default output directory is the executable's folder when frozen (for example, with PyInstaller), and the script's folder when run from source. Users can select another directory in the GUI.
- The logger expects one numeric weight value per serial line. The `load-cell-300kg-lcd/load-cell-300kg-lcd.ino` sketch prints the weight over serial at 115200 baud.
- `Serial-Logger/tests/arduino_tester` is a PlatformIO project for the official Arduino Nano Every (`atmelmegaavr`, `nano_every`). Its `src/main.cpp` sends a simulated 50-150 kg sine-wave reading at 10 Hz and 115200 baud, with no HX711 or load cell required.
- In `load-cell-300kg-lcd/load-cell-300kg-lcd.ino`, the tare-button check is in `setup()`, so it runs only at startup. If changing this behavior, keep `scale.tare()` and LCD work out of interrupt handlers.
- For a standalone Windows build, run PyInstaller on Windows in the Python environment that has `pyserial`. The default one-folder build needs the whole `dist/LoadCellLogger` folder; `--onefile` produces a single executable. The target machine does not need Python, but may need the USB-serial adapter's driver.