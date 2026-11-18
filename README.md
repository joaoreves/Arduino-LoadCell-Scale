# Arduino-LoadCell-Scale
A scale create using a Load Cell (with a HX711) and an Arduino.

## Serial Logger

Run `python Serial-Logger/logger.py` to open the desktop logger. Select the
Arduino's COM port (use **Refresh ports** after connecting it), then click
**Connect**. The app waits for a valid reading and shows a live weight and graph
preview without creating a CSV, so the operator can verify the readings first.
Once the preview looks right, choose an output directory and click
**Start logging**. The graph window can be set to 10, 30, 60, or 120 seconds.
Click **Stop logging** to finish the CSV while keeping the live preview running;
click **Disconnect** when finished with the serial port.

Each capture creates a timestamped CSV in the selected directory. The logger
expects numeric weight readings, one per line, at 115200 baud. It uses Python's
Tkinter GUI library and `pyserial`. When packaged, the default output directory
is the executable's folder; when run from source, it is the script's folder.

## Log Viewer

Run `python Log-Viewer\log_viewer.py` to open the CSV viewer. Click **Open CSV**
and select a log created by the Serial Logger. The viewer plots measured weight
over time, highlights and annotates the maximum reading, and shows its value and
timestamp. It uses Python's Tkinter GUI library and Matplotlib.

If Matplotlib is not installed in the Python environment used to run the app,
install it with `python -m pip install matplotlib`.

### Test with a spare Arduino

The PlatformIO project for the official Arduino Nano Every is in
`Serial-Logger/tests/arduino_tester`. Its `src/main.cpp` needs no load cell or
HX711; it sends a simulated weight that varies between 50 kg and 150 kg at
115200 baud, 10 readings per second.

Open that folder as the PlatformIO project in VS Code, select the Nano Every's
COM port if PlatformIO does not detect it, then use **PlatformIO: Upload**. Or
run this from the project folder:

```powershell
pio run -t upload
```

If needed, set `upload_port = COM5` under `[env:nano_every]` in
`platformio.ini`, replacing `COM5` with the board's port.

After uploading, close the Arduino IDE Serial Monitor or Serial Plotter so the
GUI can open the board's COM port. In the logger, refresh the port list, select
the Arduino's port, and click **Connect**. The live weight and graph should
change; click **Start logging** to test CSV capture.

### Build a standalone Windows app

Build on Windows with the same Python environment used to run the logger. That
environment must have `pyserial` and Tkinter available. Install PyInstaller as
a build-time tool:

```powershell
python -m pip install pyinstaller
```

If `pyserial` is not present in that same environment, install it with
`python -m pip install pyserial`. Tkinter is included with most standard
Windows Python installations.

From the repository root, create a windowed app using PyInstaller's default
one-folder layout:

```powershell
python -m PyInstaller --noconfirm --clean --windowed --name LoadCellLogger Serial-Logger\logger.py
```

The executable will be `dist\LoadCellLogger\LoadCellLogger.exe`. Copy and
distribute the entire `dist\LoadCellLogger` folder, not just the executable.
The intermediate `build` folder and `LoadCellLogger.spec` file are not needed
to run the app.

To create a single executable instead, add `--onefile`:

```powershell
python -m PyInstaller --noconfirm --clean --windowed --onefile --name LoadCellLogger Serial-Logger\logger.py
```

That produces `dist\LoadCellLogger.exe`. A one-file build may start more slowly
and can trigger antivirus warnings. Neither build requires Python on the target
machine, but the Arduino's USB-serial adapter may still need its Windows driver.
Test the packaged app on the target machine before relying on it.
