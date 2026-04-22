# mySecureCRT 串口终端工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a SecureCRT-like serial port terminal tool with sidebar layout, dark theme, text/HEX dual display modes, and config persistence.

**Architecture:** Modular MVC — `serial_manager` handles communication via QThread, `terminal_widget` displays data with timestamps/direction markers, `settings_panel` provides controls, `config` persists user preferences, `logger` records sessions. All modules communicate through Qt signals/slots wired in `main.py`.

**Tech Stack:** Python 3.8+, PyQt5, pyserial, JSON for config

---

## File Structure

```
F:\myTools\mySecureCRT\
├── main.py              # App entry, MainWindow, dark theme, signal wiring
├── serial_manager.py    # SerialManager + SerialReadThread (QThread)
├── terminal_widget.py   # TerminalWidget (QPlainTextEdit subclass)
├── settings_panel.py    # SettingsPanel (QWidget, left sidebar)
├── config.py            # ConfigManager (JSON load/save)
├── logger.py            # DataLogger (file logging)
├── requirements.txt     # Dependencies
└── tests\
    ├── test_config.py
    ├── test_serial_manager.py
    ├── test_logger.py
    └── test_terminal_widget.py
```

---

### Task 1: Project Setup

**Files:**
- Create: `F:\myTools\mySecureCRT\requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
PyQt5>=5.15.0
pyserial>=3.5
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed PyQt5 and pyserial

- [ ] **Step 3: Create tests directory**

Run: `mkdir tests` and create empty `tests\__init__.py`

- [ ] **Step 4: Verify imports work**

Run: `python -c "import PyQt5; import serial; print('OK')"`
Expected: `OK`

---

### Task 2: Config Module

**Files:**
- Create: `F:\myTools\mySecureCRT\config.py`
- Test: `F:\myTools\mySecureCRT\tests\test_config.py`

- [ ] **Step 1: Write failing tests for ConfigManager**

```python
# tests/test_config.py
import os
import json
import tempfile
import pytest
from config import ConfigManager


class TestConfigManager:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmp_dir, "config.json")
        self.mgr = ConfigManager(self.config_path)

    def teardown_method(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.tmp_dir)

    def test_default_values(self):
        """Config should have sensible defaults when no file exists."""
        assert self.mgr.get("serial.port") == ""
        assert self.mgr.get("serial.baudrate") == 115200
        assert self.mgr.get("serial.databits") == 8
        assert self.mgr.get("serial.stopbits") == 1
        assert self.mgr.get("serial.parity") == "None"
        assert self.mgr.get("serial.flowcontrol") == "None"
        assert self.mgr.get("display.mode") == "text"
        assert self.mgr.get("window.width") == 900
        assert self.mgr.get("window.height") == 600

    def test_set_and_get(self):
        """Setting a value should be retrievable."""
        self.mgr.set("serial.port", "COM5")
        assert self.mgr.get("serial.port") == "COM5"

    def test_save_and_load(self):
        """Config should persist to disk and reload."""
        self.mgr.set("serial.baudrate", 9600)
        self.mgr.save()
        assert os.path.exists(self.config_path)

        mgr2 = ConfigManager(self.config_path)
        mgr2.load()
        assert mgr2.get("serial.baudrate") == 9600

    def test_load_missing_file_uses_defaults(self):
        """Loading when file doesn't exist should keep defaults."""
        self.mgr.load()
        assert self.mgr.get("serial.baudrate") == 115200

    def test_get_all(self):
        """get_all should return entire config dict."""
        data = self.mgr.get_all()
        assert "serial" in data
        assert "display" in data
        assert "window" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement ConfigManager**

```python
# config.py
import os
import json
import copy


DEFAULT_CONFIG = {
    "serial": {
        "port": "",
        "baudrate": 115200,
        "databits": 8,
        "stopbits": 1,
        "parity": "None",
        "flowcontrol": "None",
    },
    "display": {
        "mode": "text",
    },
    "window": {
        "width": 900,
        "height": 600,
        "x": 100,
        "y": 100,
    },
}


class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".mySecureCRT")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "config.json")
        self._path = config_path
        self._data = copy.deepcopy(DEFAULT_CONFIG)

    def load(self):
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self._merge(self._data, saved)
        except (json.JSONDecodeError, IOError):
            pass

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, dotted_key):
        keys = dotted_key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return None
        return node

    def set(self, dotted_key, value):
        keys = dotted_key.split(".")
        node = self._data
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value

    def get_all(self):
        return copy.deepcopy(self._data)

    @staticmethod
    def _merge(base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._merge(base[k], v)
            else:
                base[k] = v
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py requirements.txt tests/__init__.py
git commit -m "feat: add ConfigManager with JSON persistence and defaults"
```

---

### Task 3: Logger Module

**Files:**
- Create: `F:\myTools\mySecureCRT\logger.py`
- Test: `F:\myTools\mySecureCRT\tests\test_logger.py`

- [ ] **Step 1: Write failing tests for DataLogger**

```python
# tests/test_logger.py
import os
import tempfile
import pytest
from logger import DataLogger


class TestDataLogger:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False
        )
        self.tmp.close()
        self.log_path = self.tmp.name

    def teardown_method(self):
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def test_start_creates_file(self):
        logger = DataLogger()
        logger.start(self.log_path)
        assert logger.is_active
        logger.stop()

    def test_log_entry_written(self):
        logger = DataLogger()
        logger.start(self.log_path)
        logger.log("RX", b"Hello")
        logger.stop()
        content = open(self.log_path, "r", encoding="utf-8").read()
        assert "RX" in content
        assert "Hello" in content

    def test_log_hex_entry(self):
        logger = DataLogger()
        logger.start(self.log_path)
        logger.log("TX", b"\x41\x42\x43")
        logger.stop()
        content = open(self.log_path, "r", encoding="utf-8").read()
        assert "TX" in content

    def test_stop_closes_file(self):
        logger = DataLogger()
        logger.start(self.log_path)
        logger.stop()
        assert not logger.is_active

    def test_log_when_inactive_does_nothing(self):
        logger = DataLogger()
        logger.log("RX", b"data")  # should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_logger.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logger'`

- [ ] **Step 3: Implement DataLogger**

```python
# logger.py
from datetime import datetime


class DataLogger:
    def __init__(self):
        self._file = None
        self._active = False

    @property
    def is_active(self):
        return self._active

    def start(self, file_path):
        self.stop()
        self._file = open(file_path, "a", encoding="utf-8")
        self._active = True
        self._file.write(f"--- Log started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        self._file.flush()

    def stop(self):
        if self._file:
            self._file.write(f"--- Log stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            self._file.flush()
            self._file.close()
            self._file = None
        self._active = False

    def log(self, direction, data):
        if not self._active or not self._file:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            text = data.decode("utf-8", errors="replace")
        except AttributeError:
            text = str(data)
        hex_str = " ".join(f"{b:02X}" for b in data) if isinstance(data, (bytes, bytearray)) else ""
        self._file.write(f"[{timestamp}] {direction}: {text}")
        if hex_str:
            self._file.write(f"  | HEX: {hex_str}")
        self._file.write("\n")
        self._file.flush()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_logger.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add logger.py tests/test_logger.py
git commit -m "feat: add DataLogger for session logging to file"
```

---

### Task 4: Serial Manager Module

**Files:**
- Create: `F:\myTools\mySecureCRT\serial_manager.py`
- Test: `F:\myTools\mySecureCRT\tests\test_serial_manager.py`

- [ ] **Step 1: Write failing tests for SerialManager**

```python
# tests/test_serial_manager.py
import pytest
from unittest.mock import patch, MagicMock
from serial_manager import SerialManager


class TestSerialManager:
    def test_list_ports_returns_list(self):
        mgr = SerialManager()
        ports = mgr.list_ports()
        assert isinstance(ports, list)

    @patch("serial_manager.serial.Serial")
    def test_open_success(self, mock_serial_cls):
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_serial_cls.return_value = mock_ser

        mgr = SerialManager()
        signals = []
        mgr.connection_changed.connect(lambda s: signals.append(s))
        mgr.open("COM1", 115200, 8, 1, "None", "None")

        mock_serial_cls.assert_called_once()
        assert mgr.is_connected

    @patch("serial_manager.serial.Serial")
    def test_open_failure_emits_error(self, mock_serial_cls):
        mock_serial_cls.side_effect = Exception("Port busy")

        mgr = SerialManager()
        errors = []
        mgr.error_occurred.connect(lambda e: errors.append(e))
        mgr.open("COM99", 115200, 8, 1, "None", "None")

        assert len(errors) == 1
        assert "Port busy" in errors[0]
        assert not mgr.is_connected

    @patch("serial_manager.serial.Serial")
    def test_close(self, mock_serial_cls):
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_serial_cls.return_value = mock_ser

        mgr = SerialManager()
        mgr.open("COM1", 115200, 8, 1, "None", "None")
        mgr.close()

        mock_ser.close.assert_called_once()
        assert not mgr.is_connected

    @patch("serial_manager.serial.Serial")
    def test_write_sends_data(self, mock_serial_cls):
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_serial_cls.return_value = mock_ser

        mgr = SerialManager()
        mgr.open("COM1", 115200, 8, 1, "None", "None")
        mgr.write(b"AT\r")

        mock_ser.write.assert_called_with(b"AT\r")

    def test_write_when_disconnected_does_nothing(self):
        mgr = SerialManager()
        mgr.write(b"data")  # should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_serial_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'serial_manager'`

- [ ] **Step 3: Implement SerialManager**

```python
# serial_manager.py
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, QThread, pyqtSignal


class SerialReadThread(QThread):
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)

    def __init__(self, ser):
        super().__init__()
        self._serial = ser
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                if self._serial and self._serial.is_open:
                    waiting = self._serial.in_waiting
                    if waiting > 0:
                        data = self._serial.read(waiting)
                        if data:
                            self.data_received.emit(data)
                    else:
                        self.msleep(10)
                else:
                    break
            except Exception as e:
                if self._running:
                    self.error_occurred.emit(str(e))
                break

    def stop(self):
        self._running = False
        self.wait(2000)


PARITY_MAP = {
    "None": serial.PARITY_NONE,
    "Even": serial.PARITY_EVEN,
    "Odd": serial.PARITY_ODD,
    "Mark": serial.PARITY_MARK,
    "Space": serial.PARITY_SPACE,
}

STOPBITS_MAP = {
    1: serial.STOPBITS_ONE,
    1.5: serial.STOPBITS_ONE_POINT_FIVE,
    2: serial.STOPBITS_TWO,
}


class SerialManager(QObject):
    data_received = pyqtSignal(bytes)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    bytes_sent = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial = None
        self._read_thread = None

    @property
    def is_connected(self):
        return self._serial is not None and self._serial.is_open

    def list_ports(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def open(self, port, baudrate, databits, stopbits, parity, flowcontrol):
        self.close()
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=int(baudrate),
                bytesize=int(databits),
                stopbits=STOPBITS_MAP.get(stopbits, serial.STOPBITS_ONE),
                parity=PARITY_MAP.get(parity, serial.PARITY_NONE),
                xonxoff=(flowcontrol == "XON/XOFF"),
                rtscts=(flowcontrol == "RTS/CTS"),
                timeout=0.1,
            )
            self._read_thread = SerialReadThread(self._serial)
            self._read_thread.data_received.connect(self.data_received.emit)
            self._read_thread.error_occurred.connect(self._on_read_error)
            self._read_thread.start()
            self.connection_changed.emit(True)
        except Exception as e:
            self._serial = None
            self.error_occurred.emit(str(e))

    def close(self):
        if self._read_thread:
            self._read_thread.stop()
            self._read_thread = None
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self.connection_changed.emit(False)

    def write(self, data):
        if not self.is_connected:
            return
        try:
            self._serial.write(data)
            self.bytes_sent.emit(len(data))
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _on_read_error(self, msg):
        self.error_occurred.emit(msg)
        self.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_serial_manager.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add serial_manager.py tests/test_serial_manager.py
git commit -m "feat: add SerialManager with QThread-based reading"
```

---

### Task 5: Terminal Widget

**Files:**
- Create: `F:\myTools\mySecureCRT\terminal_widget.py`
- Test: `F:\myTools\mySecureCRT\tests\test_terminal_widget.py`

- [ ] **Step 1: Write failing tests for TerminalWidget formatting helpers**

```python
# tests/test_terminal_widget.py
import sys
import pytest
from PyQt5.QtWidgets import QApplication

# QApplication must exist before creating any widgets
app = QApplication.instance() or QApplication(sys.argv)

from terminal_widget import TerminalWidget


class TestTerminalWidget:
    def setup_method(self):
        self.widget = TerminalWidget()

    def test_format_text_rx(self):
        line = self.widget.format_line("RX", b"Hello", mode="text")
        assert "RX" in line
        assert "Hello" in line
        # timestamp pattern [HH:MM:SS]
        assert line.startswith("[")

    def test_format_text_tx(self):
        line = self.widget.format_line("TX", b"AT\r", mode="text")
        assert "TX" in line
        assert "AT" in line

    def test_format_hex_rx(self):
        line = self.widget.format_line("RX", b"\x48\x65\x6c", mode="hex")
        assert "RX" in line
        assert "48 65 6C" in line.upper()
        assert "Hel" in line

    def test_clear_terminal(self):
        self.widget.append_data("RX", b"data")
        self.widget.clear_terminal()
        assert self.widget.toPlainText() == ""

    def test_display_mode_switch(self):
        self.widget.set_display_mode("hex")
        assert self.widget.display_mode == "hex"
        self.widget.set_display_mode("text")
        assert self.widget.display_mode == "text"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_terminal_widget.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'terminal_widget'`

- [ ] **Step 3: Implement TerminalWidget**

```python
# terminal_widget.py
from datetime import datetime
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QKeyEvent
from PyQt5.QtCore import pyqtSignal, Qt


class TerminalWidget(QPlainTextEdit):
    key_pressed = pyqtSignal(bytes)

    COLORS = {
        "timestamp": "#666666",
        "rx_tag": "#6a9955",
        "rx_data": "#569cd6",
        "tx_tag": "#ce9178",
        "tx_data": "#ce9178",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = "text"
        self._tx_bytes = 0
        self._rx_bytes = 0
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #1e1e1e;"
            "  color: #cccccc;"
            "  border: none;"
            "  selection-background-color: #264f78;"
            "}"
        )
        self.setMaximumBlockCount(10000)

    @property
    def display_mode(self):
        return self._display_mode

    @property
    def tx_bytes(self):
        return self._tx_bytes

    @property
    def rx_bytes(self):
        return self._rx_bytes

    def set_display_mode(self, mode):
        self._display_mode = mode

    def format_line(self, direction, data, mode=None):
        if mode is None:
            mode = self._display_mode
        timestamp = datetime.now().strftime("%H:%M:%S")
        if mode == "hex":
            hex_part = " ".join(f"{b:02X}" for b in data)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
            return f"[{timestamp}] {direction}: {hex_part} | {ascii_part}"
        else:
            text = data.decode("utf-8", errors="replace")
            return f"[{timestamp}] {direction}: {text}"

    def append_data(self, direction, data):
        if direction == "TX":
            self._tx_bytes += len(data)
        else:
            self._rx_bytes += len(data)
        line = self.format_line(direction, data)
        self._append_colored_line(direction, line)

    def _append_colored_line(self, direction, line):
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)

        # Parse the line: [timestamp] DIRECTION: content
        bracket_end = line.index("]") + 1
        timestamp_part = line[:bracket_end]
        rest = line[bracket_end:]

        # Timestamp in gray
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS["timestamp"]))
        cursor.insertText(timestamp_part, fmt)

        # Direction tag + data
        if direction == "TX":
            tag_fmt = QTextCharFormat()
            tag_fmt.setForeground(QColor(self.COLORS["tx_tag"]))
            data_fmt = QTextCharFormat()
            data_fmt.setForeground(QColor(self.COLORS["tx_data"]))
        else:
            tag_fmt = QTextCharFormat()
            tag_fmt.setForeground(QColor(self.COLORS["rx_tag"]))
            data_fmt = QTextCharFormat()
            data_fmt.setForeground(QColor(self.COLORS["rx_data"]))

        # Find the colon after direction
        colon_pos = rest.index(":")
        tag_part = rest[: colon_pos + 1]
        data_part = rest[colon_pos + 1 :]

        cursor.insertText(tag_part, tag_fmt)
        cursor.insertText(data_part + "\n", data_fmt)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_terminal(self):
        self.clear()
        self._tx_bytes = 0
        self._rx_bytes = 0

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.key_pressed.emit(b"\r\n")
        elif key == Qt.Key_Backspace:
            self.key_pressed.emit(b"\x08")
        elif key == Qt.Key_Tab:
            self.key_pressed.emit(b"\t")
        elif key == Qt.Key_Escape:
            self.key_pressed.emit(b"\x1b")
        elif text:
            self.key_pressed.emit(text.encode("utf-8"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_terminal_widget.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add terminal_widget.py tests/test_terminal_widget.py
git commit -m "feat: add TerminalWidget with text/HEX modes and colored output"
```

---

### Task 6: Settings Panel

**Files:**
- Create: `F:\myTools\mySecureCRT\settings_panel.py`

- [ ] **Step 1: Implement SettingsPanel**

```python
# settings_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout,
)
from PyQt5.QtCore import pyqtSignal, Qt


class SettingsPanel(QWidget):
    connect_clicked = pyqtSignal()
    disconnect_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    display_mode_changed = pyqtSignal(str)
    clear_clicked = pyqtSignal()
    save_log_clicked = pyqtSignal()

    BAUDRATES = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
    DATABITS = ["5", "6", "7", "8"]
    STOPBITS = ["1", "1.5", "2"]
    PARITIES = ["None", "Even", "Odd", "Mark", "Space"]
    FLOWCONTROLS = ["None", "RTS/CTS", "XON/XOFF"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self._connected = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Section: Serial Settings
        layout.addWidget(self._make_section_label("串口设置"))

        self.port_combo = self._add_combo(layout, "端口 Port", [])
        self.baud_combo = self._add_combo(layout, "波特率 Baud Rate", self.BAUDRATES)
        self.baud_combo.setCurrentText("115200")
        self.databits_combo = self._add_combo(layout, "数据位 Data Bits", self.DATABITS)
        self.databits_combo.setCurrentText("8")
        self.stopbits_combo = self._add_combo(layout, "停止位 Stop Bits", self.STOPBITS)
        self.stopbits_combo.setCurrentText("1")
        self.parity_combo = self._add_combo(layout, "校验位 Parity", self.PARITIES)
        self.flow_combo = self._add_combo(layout, "流控 Flow Control", self.FLOWCONTROLS)

        # Connect button
        self.connect_btn = QPushButton("🔗 连接")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setMinimumHeight(32)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)

        # Separator
        layout.addWidget(self._make_separator())

        # Section: Display Settings
        layout.addWidget(self._make_section_label("显示设置"))

        mode_row = QHBoxLayout()
        self.text_btn = QPushButton("文本")
        self.text_btn.setCheckable(True)
        self.text_btn.setChecked(True)
        self.text_btn.clicked.connect(lambda: self._set_mode("text"))
        self.hex_btn = QPushButton("HEX")
        self.hex_btn.setCheckable(True)
        self.hex_btn.clicked.connect(lambda: self._set_mode("hex"))
        mode_row.addWidget(self.text_btn)
        mode_row.addWidget(self.hex_btn)
        layout.addLayout(mode_row)

        action_row = QHBoxLayout()
        self.clear_btn = QPushButton("清屏")
        self.clear_btn.clicked.connect(self.clear_clicked.emit)
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_log_clicked.emit)
        action_row.addWidget(self.clear_btn)
        action_row.addWidget(self.save_btn)
        layout.addLayout(action_row)

        # Separator
        layout.addWidget(self._make_separator())

        # Refresh
        self.refresh_btn = QPushButton("🔄 刷新端口")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()

    def _make_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #4ec9b0; font-size: 11px; font-weight: bold;"
            "text-transform: uppercase; letter-spacing: 1px;"
        )
        return lbl

    def _make_separator(self):
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #444444;")
        return sep

    def _add_combo(self, layout, label_text, items):
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(lbl)
        combo = QComboBox()
        combo.addItems(items)
        layout.addWidget(combo)
        return combo

    def _on_connect_clicked(self):
        if self._connected:
            self.disconnect_clicked.emit()
        else:
            self.connect_clicked.emit()

    def _set_mode(self, mode):
        self.text_btn.setChecked(mode == "text")
        self.hex_btn.setChecked(mode == "hex")
        self.display_mode_changed.emit(mode)

    def set_connected(self, connected):
        self._connected = connected
        if connected:
            self.connect_btn.setText("🔌 断开")
            self.connect_btn.setStyleSheet(
                "background-color: #a1260d; color: white; font-weight: bold;"
                "border: none; border-radius: 4px;"
            )
        else:
            self.connect_btn.setText("🔗 连接")
            self.connect_btn.setStyleSheet(
                "background-color: #0e639c; color: white; font-weight: bold;"
                "border: none; border-radius: 4px;"
            )

    def set_ports(self, ports):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)

    def get_settings(self):
        stopbits = self.stopbits_combo.currentText()
        try:
            stopbits = float(stopbits)
            if stopbits == int(stopbits):
                stopbits = int(stopbits)
        except ValueError:
            stopbits = 1
        return {
            "port": self.port_combo.currentText(),
            "baudrate": int(self.baud_combo.currentText()),
            "databits": int(self.databits_combo.currentText()),
            "stopbits": stopbits,
            "parity": self.parity_combo.currentText(),
            "flowcontrol": self.flow_combo.currentText(),
        }

    def apply_config(self, config):
        if config.get("serial.port"):
            idx = self.port_combo.findText(config.get("serial.port"))
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        self.baud_combo.setCurrentText(str(config.get("serial.baudrate", 115200)))
        self.databits_combo.setCurrentText(str(config.get("serial.databits", 8)))
        stopbits = config.get("serial.stopbits", 1)
        self.stopbits_combo.setCurrentText(str(stopbits))
        self.parity_combo.setCurrentText(config.get("serial.parity", "None"))
        self.flow_combo.setCurrentText(config.get("serial.flowcontrol", "None"))

        mode = config.get("display.mode", "text")
        self._set_mode(mode)
```

- [ ] **Step 2: Visually verify the panel renders correctly (done in Task 7 integration)**

- [ ] **Step 3: Commit**

```bash
git add settings_panel.py
git commit -m "feat: add SettingsPanel sidebar with serial config controls"
```

---

### Task 7: Main Window and Dark Theme

**Files:**
- Create: `F:\myTools\mySecureCRT\main.py`

- [ ] **Step 1: Implement MainWindow with dark theme and full wiring**

```python
# main.py
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QLabel, QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from serial_manager import SerialManager
from terminal_widget import TerminalWidget
from settings_panel import SettingsPanel
from config import ConfigManager
from logger import DataLogger


DARK_THEME = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 12px;
}
QComboBox {
    background-color: #3c3c3c;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px 8px;
    color: #cccccc;
    min-height: 20px;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #252526;
    color: #cccccc;
    selection-background-color: #0e639c;
    border: 1px solid #555555;
}
QPushButton {
    background-color: #3c3c3c;
    color: #cccccc;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 4px 8px;
    min-height: 20px;
}
QPushButton:hover {
    background-color: #4c4c4c;
}
QPushButton:pressed {
    background-color: #2c2c2c;
}
QPushButton:checked {
    background-color: #0e639c;
    color: white;
    border: 1px solid #0e639c;
}
QPushButton#connectBtn {
    background-color: #0e639c;
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
}
QPushButton#connectBtn:hover {
    background-color: #1177bb;
}
QLabel {
    background: transparent;
}
QStatusBar {
    background-color: #007acc;
    color: white;
    font-size: 11px;
}
QStatusBar QLabel {
    color: white;
    margin-right: 16px;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔌 mySecureCRT — 串口终端工具")
        self.config = ConfigManager()
        self.config.load()
        self.serial_mgr = SerialManager()
        self.data_logger = DataLogger()

        self._init_ui()
        self._connect_signals()
        self._apply_saved_config()
        self._refresh_ports()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar
        self.settings_panel = SettingsPanel()
        self.settings_panel.setStyleSheet(
            "SettingsPanel { background-color: #252526; border-right: 1px solid #333333; }"
        )
        main_layout.addWidget(self.settings_panel)

        # Right terminal area
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.terminal = TerminalWidget()
        right_layout.addWidget(self.terminal)
        main_layout.addLayout(right_layout, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("🔴 未连接")
        self.params_label = QLabel("")
        self.stats_label = QLabel("↑TX: 0  ↓RX: 0")
        self.log_label = QLabel("")
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addWidget(self.params_label)
        self.status_bar.addPermanentWidget(self.log_label)
        self.status_bar.addPermanentWidget(self.stats_label)

        # Restore window geometry
        w = self.config.get("window.width") or 900
        h = self.config.get("window.height") or 600
        x = self.config.get("window.x")
        y = self.config.get("window.y")
        self.resize(w, h)
        if x is not None and y is not None:
            self.move(x, y)

    def _connect_signals(self):
        # Settings panel signals
        self.settings_panel.connect_clicked.connect(self._on_connect)
        self.settings_panel.disconnect_clicked.connect(self._on_disconnect)
        self.settings_panel.refresh_clicked.connect(self._refresh_ports)
        self.settings_panel.display_mode_changed.connect(self.terminal.set_display_mode)
        self.settings_panel.clear_clicked.connect(self._on_clear)
        self.settings_panel.save_log_clicked.connect(self._on_save_log)

        # Serial manager signals
        self.serial_mgr.data_received.connect(self._on_data_received)
        self.serial_mgr.connection_changed.connect(self._on_connection_changed)
        self.serial_mgr.error_occurred.connect(self._on_error)

        # Terminal keyboard input
        self.terminal.key_pressed.connect(self._on_key_pressed)

    def _apply_saved_config(self):
        self.settings_panel.apply_config(self.config)
        mode = self.config.get("display.mode") or "text"
        self.terminal.set_display_mode(mode)

    def _refresh_ports(self):
        ports = self.serial_mgr.list_ports()
        self.settings_panel.set_ports(ports)

    def _on_connect(self):
        settings = self.settings_panel.get_settings()
        if not settings["port"]:
            QMessageBox.warning(self, "提示", "请先选择串口端口")
            return
        self.serial_mgr.open(
            settings["port"], settings["baudrate"], settings["databits"],
            settings["stopbits"], settings["parity"], settings["flowcontrol"],
        )

    def _on_disconnect(self):
        self.serial_mgr.close()

    def _on_connection_changed(self, connected):
        self.settings_panel.set_connected(connected)
        if connected:
            settings = self.settings_panel.get_settings()
            self.status_label.setText("🟢 已连接")
            p = settings
            self.params_label.setText(
                f"{p['port']} | {p['baudrate']} {p['databits']}"
                f"{'N' if p['parity'] == 'None' else p['parity'][0]}"
                f"{p['stopbits']}"
            )
        else:
            self.status_label.setText("🔴 未连接")
            self.params_label.setText("")

    def _on_data_received(self, data):
        self.terminal.append_data("RX", data)
        if self.data_logger.is_active:
            self.data_logger.log("RX", data)
        self._update_stats()

    def _on_key_pressed(self, data):
        self.serial_mgr.write(data)
        self.terminal.append_data("TX", data)
        if self.data_logger.is_active:
            self.data_logger.log("TX", data)
        self._update_stats()

    def _on_error(self, msg):
        QMessageBox.critical(self, "串口错误", msg)

    def _on_clear(self):
        self.terminal.clear_terminal()
        self._update_stats()

    def _on_save_log(self):
        if self.data_logger.is_active:
            self.data_logger.stop()
            self.log_label.setText("")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "日志文件 (*.log *.txt);;所有文件 (*)"
        )
        if path:
            self.data_logger.start(path)
            self.log_label.setText("📝 日志记录中")

    def _update_stats(self):
        tx = self.terminal.tx_bytes
        rx = self.terminal.rx_bytes
        self.stats_label.setText(f"↑TX: {tx}  ↓RX: {rx}")

    def _save_config(self):
        settings = self.settings_panel.get_settings()
        self.config.set("serial.port", settings["port"])
        self.config.set("serial.baudrate", settings["baudrate"])
        self.config.set("serial.databits", settings["databits"])
        self.config.set("serial.stopbits", settings["stopbits"])
        self.config.set("serial.parity", settings["parity"])
        self.config.set("serial.flowcontrol", settings["flowcontrol"])
        self.config.set("display.mode", self.terminal.display_mode)
        geo = self.geometry()
        self.config.set("window.width", geo.width())
        self.config.set("window.height", geo.height())
        self.config.set("window.x", geo.x())
        self.config.set("window.y", geo.y())
        self.config.save()

    def closeEvent(self, event):
        self._save_config()
        if self.data_logger.is_active:
            self.data_logger.stop()
        self.serial_mgr.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    window = MainWindow()
    window.show()
    # Focus the terminal for keyboard input
    window.terminal.setFocus()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Launch and verify visually**

Run: `cd F:\myTools\mySecureCRT && python main.py`

Expected:
- Dark themed window appears (900x600)
- Left sidebar with serial settings, dropdowns, connect button
- Right area is empty terminal with dark background
- Status bar shows "🔴 未连接"
- Text/HEX toggle buttons work
- Refresh ports populates port dropdown
- Close window exits cleanly

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add MainWindow with dark theme, status bar, and full signal wiring"
```

---

### Task 8: Integration Testing and Polish

**Files:**
- Modify: `F:\myTools\mySecureCRT\settings_panel.py` (apply_config fix)

- [ ] **Step 1: Run all unit tests**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\ -v`
Expected: All tests pass (16 total)

- [ ] **Step 2: Manual integration test (if serial device available)**

1. Connect a serial device (e.g., USB-to-TTL adapter with loopback TX→RX)
2. Run: `python main.py`
3. Select the COM port from dropdown, click 连接
4. Type characters — they should appear as TX and echo back as RX (if loopback)
5. Toggle to HEX mode — data shows hex bytes
6. Click 保存 — choose log file — verify log is written
7. Click 清屏 — terminal clears, byte counters reset
8. Click 断开 — status updates to 🔴
9. Close app — reopen — verify settings are restored

- [ ] **Step 3: Fix any issues found during integration test**

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: mySecureCRT v1.0 - serial terminal tool with text/HEX modes"
```

---

## Summary

| Task | Component          | Tests | Files Created        |
| ---- | ------------------ | ----- | -------------------- |
| 1    | Project Setup      | 0     | requirements.txt     |
| 2    | Config Module      | 5     | config.py            |
| 3    | Logger Module      | 5     | logger.py            |
| 4    | Serial Manager     | 6     | serial_manager.py    |
| 5    | Terminal Widget    | 5     | terminal_widget.py   |
| 6    | Settings Panel     | 0     | settings_panel.py    |
| 7    | Main Window        | 0     | main.py              |
| 8    | Integration Test   | 0     | —                    |
| **Total** |               | **21**|                      |

Dependency order: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7 → Task 8
