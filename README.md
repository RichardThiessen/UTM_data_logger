# UTM Data Logger

A Python application for real-time data acquisition, visualization, and analysis from Thwing Albert Universal Testing Machines (UTS/UTM).

## Overview

UTM Data Logger captures load cell measurements during material testing (tensile, compression, peel tests, etc.) and provides:

- Real-time data visualization
- Statistical analysis (mean, peak, min, standard deviation)
- Multi-test session management
- Clipboard export for spreadsheet integration
- Both GUI and CLI interfaces
- Portable Windows distribution (no installation required)

## Requirements

- Python 2.7+ or Python 3.x
- pyserial (for serial port communication)
- tkinter (included with most Python installations)

## Installation

### Development Setup

```bash
git clone <repository-url>
cd UTM_data_logger/app
python main.py
```

### Windows Portable Distribution

Download the pre-built zip package or build your own (see [Building for Windows](#building-for-windows)). Extract and run `UTM_Logger.bat` - no Python installation required.

## Usage

### GUI Mode

```bash
cd app
python main.py
```

Or use the convenience script:
```bash
./run.sh
```

**On Windows (portable distribution):**
Double-click `UTM_Logger.bat`

**Workflow:**
1. Open **File → Settings**
2. Select COM port (e.g., `/dev/ttyACM0` or `COM3`) and baudrate (default: 9600)
3. Enable auto-reconnect if desired
4. Click OK to connect
5. Tests appear in the left panel as data streams in
6. Click a test to view its graph
7. Use **Edit → Copy** (Ctrl+C) to export selected test statistics

### CLI Mode

For headless operation or scripting:

```bash
python reader_cli.py --serial /dev/ttyACM0 --baudrate 9600
```

**On Windows (portable distribution):**
```
UTM_Logger_CLI.bat --serial COM3 --baudrate 9600
```

Output format:
```
[SAMPLE] 45.123456 @ 1702000000.123
[TEST_COMPLETE] @ 1702000010.456
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python main.py --debug reader,stream
python main.py --debug all
```

Available debug modules: `reader`, `ui`, `graph`, `stats`, `models`, `stream`, `all`

## Configuration

Settings are persisted in `settings.ini` (created in the app directory).

### Serial Settings
| Setting | Default | Description |
|---------|---------|-------------|
| port | (none) | Serial port path |
| baudrate | 9600 | Communication speed |
| auto_reconnect | True | Reconnect on disconnect |

### Export Settings
| Setting | Default | Description |
|---------|---------|-------------|
| columns | mean,peak,low,stdev | Statistics to export |
| headers | True | Include column headers |
| transpose | False | Tests as columns instead of rows |
| datapoints | False | Include raw sample values |

Available columns: `test`, `mean`, `peak`, `low`, `stdev`, `points`

## Data Format

### Input (from UTM)

The application expects ASCII float values, one per line:

```
45.123456
46.234567
47.345678
```

Tests are automatically delimited by gaps in data transmission (adaptive timeout detection).

### Export

Tab-separated values suitable for pasting into spreadsheets:

```
Mean    Peak    Low     Stdev
45.5    50.2    41.1    2.34
48.3    52.1    44.5    2.11
```

## Building for Windows

The `dist/` directory contains tooling for creating a portable Windows distribution that includes a bundled Python interpreter.

### Prerequisites: Creating python32_base.zip

Python 3.4.4 does not have an embeddable distribution, so you need to create a portable version manually:

1. Install Python 3.4.4 (32-bit) on Windows from:
   https://www.python.org/downloads/release/python-344/

2. Copy the entire install directory (e.g., `C:\Python34`) to a working folder

3. Copy these DLLs into the Python directory (they're not included in the install):
   - `python34.dll` (from `C:\Windows\System32` or `SysWOW64`)
   - `msvcr100.dll` (from `C:\Windows\System32` or `SysWOW64`)

4. Remove unnecessary directories to reduce size:
   - `Doc/`
   - `include/`
   - `libs/`
   - `Tools/`
   - `Scripts/`

5. Create `python32_base.zip` with this structure:
   ```
   UTM_Data_Logger/
   └── python32/
       ├── python.exe
       ├── pythonw.exe
       ├── python34.dll
       ├── msvcr100.dll
       ├── DLLs/
       ├── Lib/
       └── ...
   ```

Place `python32_base.zip` in the `dist/` directory.

### Building

```bash
cd dist
python build.py
```

The build script:
1. Copies `python32_base.zip` as the starting point
2. Appends the `app/` directory and launcher scripts
3. Outputs a timestamped zip (e.g., `UTM_Data_Logger_20251216.zip`)

### Distribution Contents

```
UTM_Data_Logger/
├── app/                    # Application source
├── python32/               # Portable Python 3.4.4 (32-bit)
├── UTM_Logger.bat          # Double-click to launch GUI
└── UTM_Logger_CLI.bat      # CLI launcher (run from command prompt)
```

## Project Structure

```
UTM_data_logger/
├── app/
│   ├── main.py              # GUI entry point
│   ├── reader_cli.py        # CLI entry point
│   ├── simulator.py         # Test data generator
│   ├── run.sh               # Linux/Mac launch script
│   ├── tests/               # Unit tests
│   └── utm_data_logger/     # Main package
│       ├── models.py        # Test/TestSession data models
│       ├── reader.py        # Stream data parser
│       ├── stream.py        # Serial/socket abstractions
│       ├── ui.py            # Tkinter GUI
│       ├── graph.py         # Data visualization
│       ├── stats.py         # Statistical calculations
│       └── settings.py      # Configuration persistence
├── dist/
│   ├── build.py             # Windows distribution builder
│   ├── python32/            # Portable Python (user-supplied)
│   ├── UTM_Logger.bat       # Windows GUI launcher
│   └── UTM_Logger_CLI.bat   # Windows CLI launcher
└── firmware/
    └── src/main.cpp         # Arduino Due simulator
```

## Development

### Running the Simulator

For development without hardware:

```bash
# Terminal 1: Start simulator
python simulator.py --socket /tmp/utm.sock --samples 100 --rate 10 --pattern sine

# Terminal 2: Connect app
python main.py --socket /tmp/utm.sock
```

Simulator options:
- `--samples N` - Samples per test (default: 100)
- `--rate HZ` - Sample rate (default: 10)
- `--pause SEC` - Pause between tests (default: 2)
- `--pattern TYPE` - sine, walk, or ramp (default: sine)
- `--tests N` - Number of tests, 0 for infinite (default: 0)

### Running Tests

```bash
cd app/tests
python -m pytest
# or
python -m unittest discover
```

## Architecture

The application uses an event-driven architecture:

1. **StreamReader** (separate thread) parses serial/socket data and pushes events to a queue
2. **TestSession** manages the event queue and test lifecycle
3. **UI** polls the session every 100ms for updates (non-blocking)

This separation ensures responsive UI during data acquisition.

## Hardware Compatibility

Designed for Thwing Albert Universal Testing Systems. Connect via USB serial adapter. Default baudrate is 9600 - adjust in settings if your machine uses a different rate.

## License

MIT License. See [LICENSE](LICENSE) for details.
