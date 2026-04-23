# Multi-Tab / Multi-Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-tab support to mySecureCRT so users can simultaneously connect and manage 4-8 serial ports in a single window, with shared sidebar that follows the active tab.

**Architecture:** Introduce a `Session` class in `session.py` that bundles (SerialManager + TerminalWidget + DataLogger) per tab. MainWindow replaces its single TerminalWidget with a QTabWidget, each tab holding one Session's terminal. SettingsPanel remains a single instance whose controls update when the active tab changes. ConfigManager gains a `sessions` array for multi-session persistence with V1 backward compatibility.

**Tech Stack:** Python 3.8+, PyQt5, pyserial, pyte, pytest

---

## File Structure

```
F:\myTools\mySecureCRT\
├── session.py           # NEW — Session class: bundles SerialManager + TerminalWidget + DataLogger
├── config.py            # MODIFY — V2 multi-session schema, migration from V1
├── settings_panel.py    # MODIFY — add apply_session_config / get_session_config
├── main.py              # REWRITE — QTabWidget, tab management, session switching
├── serial_manager.py    # UNCHANGED
├── terminal_widget.py   # UNCHANGED
├── logger.py            # UNCHANGED
└── tests\
    ├── conftest.py              # UNCHANGED
    ├── test_session.py          # NEW — Session lifecycle tests
    ├── test_config.py           # MODIFY — add V2 schema + migration tests
    ├── test_settings_panel.py   # NEW — apply_session_config / get_session_config tests
    ├── test_serial_manager.py   # UNCHANGED
    ├── test_terminal_widget.py  # UNCHANGED
    └── test_logger.py           # UNCHANGED
```

---

### Task 1: ConfigManager V2 — Multi-Session Schema + Migration

**Files:**
- Modify: `F:\myTools\mySecureCRT\config.py`
- Modify: `F:\myTools\mySecureCRT\tests\test_config.py`

- [ ] **Step 1: Write failing tests for V2 config**

Add these test methods to the existing `TestConfigManager` class in `tests/test_config.py`:

```python
# Add at top of file, alongside existing imports:
import uuid

# Add these methods to class TestConfigManager:

    def test_v2_sessions_save_and_load(self):
        """V2 config should save and load multiple sessions."""
        sessions = [
            {
                "id": "abc123",
                "name": "COM3",
                "renamed": False,
                "serial": {
                    "port": "COM3",
                    "baudrate": 115200,
                    "databits": 8,
                    "stopbits": 1,
                    "parity": "None",
                    "flowcontrol": "None",
                },
                "display": {"mode": "terminal", "font_size": 14},
            },
            {
                "id": "def456",
                "name": "传感器",
                "renamed": True,
                "serial": {
                    "port": "COM5",
                    "baudrate": 9600,
                    "databits": 8,
                    "stopbits": 1,
                    "parity": "None",
                    "flowcontrol": "None",
                },
                "display": {"mode": "monitor", "font_size": 12},
            },
        ]
        self.mgr.set("sessions", sessions)
        self.mgr.set("active_session", "abc123")
        self.mgr.save()

        mgr2 = ConfigManager(self.config_path)
        mgr2.load()
        loaded = mgr2.get("sessions")
        assert len(loaded) == 2
        assert loaded[0]["id"] == "abc123"
        assert loaded[1]["name"] == "传感器"
        assert mgr2.get("active_session") == "abc123"

    def test_v1_to_v2_migration(self):
        """Loading a V1 config (no 'sessions' key) should auto-migrate to V2."""
        v1_config = {
            "serial": {
                "port": "COM3",
                "baudrate": 115200,
                "databits": 8,
                "stopbits": 1,
                "parity": "None",
                "flowcontrol": "None",
            },
            "display": {"mode": "text"},
            "window": {"width": 900, "height": 600, "x": 100, "y": 100},
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(v1_config, f)

        mgr = ConfigManager(self.config_path)
        mgr.load()

        sessions = mgr.get("sessions")
        assert isinstance(sessions, list)
        assert len(sessions) == 1
        s = sessions[0]
        assert "id" in s
        assert s["serial"]["port"] == "COM3"
        assert s["serial"]["baudrate"] == 115200
        assert s["display"]["mode"] == "text"
        assert s["renamed"] is False
        assert mgr.get("active_session") == s["id"]
        assert mgr.get("window.width") == 900

    def test_v1_migration_empty_serial(self):
        """V1 migration with no port should still produce a valid session."""
        v1_config = {
            "serial": {"port": "", "baudrate": 115200, "databits": 8, "stopbits": 1, "parity": "None", "flowcontrol": "None"},
            "display": {"mode": "terminal"},
            "window": {"width": 900, "height": 600, "x": 100, "y": 100},
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(v1_config, f)

        mgr = ConfigManager(self.config_path)
        mgr.load()

        sessions = mgr.get("sessions")
        assert len(sessions) == 1
        assert sessions[0]["name"] == "新会话"

    def test_v2_default_config_has_sessions(self):
        """Fresh V2 ConfigManager should have an empty sessions list."""
        mgr = ConfigManager(self.config_path)
        sessions = mgr.get("sessions")
        assert isinstance(sessions, list)
        assert len(sessions) == 0

    def test_existing_v1_tests_still_pass_via_get_set(self):
        """V2 ConfigManager must still support dotted get/set for window config."""
        self.mgr.set("window.width", 1200)
        assert self.mgr.get("window.width") == 1200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_config.py -v`
Expected: New tests fail (V2 schema doesn't exist yet), old tests still pass.

- [ ] **Step 3: Implement V2 ConfigManager**

Replace the full content of `config.py` with:

```python
import os
import json
import copy
import uuid


DEFAULT_CONFIG = {
    "sessions": [],
    "active_session": "",
    "window": {
        "width": 900,
        "height": 600,
        "x": 100,
        "y": 100,
    },
}

DEFAULT_SESSION = {
    "id": "",
    "name": "新会话",
    "renamed": False,
    "serial": {
        "port": "",
        "baudrate": 115200,
        "databits": 8,
        "stopbits": 1,
        "parity": "None",
        "flowcontrol": "None",
    },
    "display": {
        "mode": "terminal",
        "font_size": 14,
    },
}


def new_session_config(name="新会话"):
    """Create a new session config dict with a unique ID."""
    session = copy.deepcopy(DEFAULT_SESSION)
    session["id"] = uuid.uuid4().hex[:8]
    session["name"] = name
    return session


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
        except (json.JSONDecodeError, IOError):
            return

        if "sessions" not in saved:
            saved = self._migrate_v1(saved)

        self._merge(self._data, saved)

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, dotted_key, default=None):
        keys = dotted_key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
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
    def _migrate_v1(old_config):
        """Migrate V1 single-session config to V2 multi-session format."""
        serial_cfg = old_config.get("serial", {})
        display_cfg = old_config.get("display", {})
        port = serial_cfg.get("port", "")
        session = copy.deepcopy(DEFAULT_SESSION)
        session["id"] = uuid.uuid4().hex[:8]
        session["name"] = port if port else "新会话"
        session["renamed"] = False
        session["serial"] = {**DEFAULT_SESSION["serial"], **serial_cfg}
        session["display"] = {**DEFAULT_SESSION["display"], **display_cfg}
        return {
            "sessions": [session],
            "active_session": session["id"],
            "window": old_config.get("window", copy.deepcopy(DEFAULT_CONFIG["window"])),
        }

    @staticmethod
    def _merge(base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._merge(base[k], v)
            else:
                base[k] = v
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_config.py -v`
Expected: All tests pass (both old and new).

- [ ] **Step 5: Commit**

```bash
cd F:\myTools\mySecureCRT
git add config.py tests\test_config.py
git commit -m "feat: V2 multi-session config schema with V1 migration

- ConfigManager now uses sessions[] array for multi-session support
- Auto-migrates V1 single-session configs on load
- new_session_config() helper for creating session configs
- DEFAULT_SESSION template for session defaults

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: Session Module — Bundle Per-Tab Components

**Files:**
- Create: `F:\myTools\mySecureCRT\session.py`
- Create: `F:\myTools\mySecureCRT\tests\test_session.py`

- [ ] **Step 1: Write failing tests for Session**

Create `tests/test_session.py`:

```python
import sys
import copy
import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from session import Session
from config import DEFAULT_SESSION


class TestSession:
    def test_create_session_initializes_components(self):
        """Session should create SerialManager, TerminalWidget, and DataLogger."""
        config = copy.deepcopy(DEFAULT_SESSION)
        config["id"] = "test1"
        config["name"] = "TestPort"
        session = Session(config)

        assert session.id == "test1"
        assert session.name == "TestPort"
        assert session.serial_manager is not None
        assert session.terminal is not None
        assert session.logger is not None
        assert session.serial_manager.is_connected is False

        session.destroy()

    def test_session_internal_signals_connected(self):
        """RX data from serial_manager should reach terminal via session wiring."""
        config = copy.deepcopy(DEFAULT_SESSION)
        config["id"] = "test2"
        session = Session(config)

        received = []
        original_append = session.terminal.append_data
        session.terminal.append_data = lambda d, data: received.append((d, data))

        session._on_data_received(b"hello")
        assert len(received) == 1
        assert received[0] == ("RX", b"hello")

        session.destroy()

    def test_session_keyboard_sends_to_serial(self):
        """key_pressed from terminal should call serial_manager.write."""
        config = copy.deepcopy(DEFAULT_SESSION)
        config["id"] = "test3"
        session = Session(config)

        session.serial_manager.write = MagicMock()
        session.serial_manager._serial = MagicMock()
        session.serial_manager._serial.is_open = True

        session._on_key_pressed(b"A")
        session.serial_manager.write.assert_called_once_with(b"A")

        session.destroy()

    def test_multiple_sessions_independent(self):
        """Two sessions should have separate SerialManager instances."""
        config1 = copy.deepcopy(DEFAULT_SESSION)
        config1["id"] = "s1"
        config2 = copy.deepcopy(DEFAULT_SESSION)
        config2["id"] = "s2"

        s1 = Session(config1)
        s2 = Session(config2)

        assert s1.serial_manager is not s2.serial_manager
        assert s1.terminal is not s2.terminal
        assert s1.logger is not s2.logger

        s1.destroy()
        s2.destroy()

    def test_destroy_closes_serial(self):
        """Destroying a session should close its serial connection."""
        config = copy.deepcopy(DEFAULT_SESSION)
        config["id"] = "test4"
        session = Session(config)

        session.serial_manager.close = MagicMock()
        session.logger.stop = MagicMock()

        session.destroy()
        session.serial_manager.close.assert_called_once()
        session.logger.stop.assert_called_once()

    def test_session_config_property(self):
        """Session.config should return the current config dict."""
        config = copy.deepcopy(DEFAULT_SESSION)
        config["id"] = "test5"
        config["serial"]["port"] = "COM7"
        session = Session(config)

        assert session.config["serial"]["port"] == "COM7"

        session.destroy()

    def test_session_renamed_flag(self):
        """Session should track renamed state."""
        config = copy.deepcopy(DEFAULT_SESSION)
        config["id"] = "test6"
        config["renamed"] = False
        session = Session(config)

        assert session.renamed is False
        session.renamed = True
        assert session.renamed is True

        session.destroy()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_session.py -v`
Expected: ImportError — `session` module does not exist.

- [ ] **Step 3: Implement Session class**

Create `session.py`:

```python
import copy
from PyQt5.QtCore import QObject, pyqtSignal

from serial_manager import SerialManager
from terminal_widget import TerminalWidget
from logger import DataLogger


class Session(QObject):
    """Bundles a SerialManager + TerminalWidget + DataLogger for one tab."""

    connection_changed = pyqtSignal(object, bool)  # (session, connected)
    error_occurred = pyqtSignal(object, str)        # (session, message)
    name_changed = pyqtSignal(object)               # (session,)
    data_activity = pyqtSignal(object)              # (session,) — for stats update

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = copy.deepcopy(config)
        self._renamed = config.get("renamed", False)

        self.serial_manager = SerialManager()
        self.terminal = TerminalWidget()
        self.logger = DataLogger()

        # Apply display settings
        mode = self._config.get("display", {}).get("mode", "terminal")
        if mode == "text":
            mode = "terminal"
        self.terminal.set_display_mode(mode)
        font_size = self._config.get("display", {}).get("font_size", 14)
        self.terminal.set_font_size(int(font_size))

        self._connect_internal_signals()

    def _connect_internal_signals(self):
        self.serial_manager.data_received.connect(self._on_data_received)
        self.serial_manager.connection_changed.connect(self._on_connection_changed)
        self.serial_manager.error_occurred.connect(self._on_error)
        self.terminal.key_pressed.connect(self._on_key_pressed)

    @property
    def id(self):
        return self._config["id"]

    @property
    def name(self):
        return self._config.get("name", "新会话")

    @name.setter
    def name(self, value):
        self._config["name"] = value
        self.name_changed.emit(self)

    @property
    def renamed(self):
        return self._renamed

    @renamed.setter
    def renamed(self, value):
        self._renamed = value
        self._config["renamed"] = value

    @property
    def config(self):
        return self._config

    def update_config_from_settings(self, settings: dict):
        """Update serial and display config from sidebar settings dict."""
        for key in ("port", "baudrate", "databits", "stopbits", "parity", "flowcontrol"):
            if key in settings:
                self._config["serial"][key] = settings[key]
        if "display_mode" in settings:
            self._config["display"]["mode"] = settings["display_mode"]
        if "font_size" in settings:
            self._config["display"]["font_size"] = settings["font_size"]

    def _on_data_received(self, data):
        self.terminal.append_data("RX", data)
        if self.logger.is_active:
            self.logger.log("RX", data)
        self.data_activity.emit(self)

    def _on_key_pressed(self, data):
        self.serial_manager.write(data)
        self.terminal.append_data("TX", data)
        if self.logger.is_active:
            self.logger.log("TX", data)
        self.data_activity.emit(self)

    def _on_connection_changed(self, connected):
        if connected and not self._renamed:
            port = self._config["serial"].get("port", "")
            if port:
                self.name = port
        self.connection_changed.emit(self, connected)

    def _on_error(self, msg):
        self.error_occurred.emit(self, msg)

    def destroy(self):
        """Clean up all resources."""
        self.logger.stop()
        self.serial_manager.close()
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_session.py -v`
Expected: All 7 tests pass.

- [ ] **Step 5: Commit**

```bash
cd F:\myTools\mySecureCRT
git add session.py tests\test_session.py
git commit -m "feat: add Session class bundling SerialManager + TerminalWidget + DataLogger

- Each Session owns independent serial, terminal, and logger instances
- Internal signal wiring: RX data → terminal, keyboard → serial write
- Auto-names tab from port on connect (unless manually renamed)
- Emits connection_changed, error_occurred, name_changed, data_activity

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: SettingsPanel — Session Config Methods

**Files:**
- Modify: `F:\myTools\mySecureCRT\settings_panel.py`
- Create: `F:\myTools\mySecureCRT\tests\test_settings_panel.py`

- [ ] **Step 1: Write failing tests for new SettingsPanel methods**

Create `tests/test_settings_panel.py`:

```python
import sys
import pytest
from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from settings_panel import SettingsPanel


class TestSettingsPanel:
    def setup_method(self):
        self.panel = SettingsPanel()
        self.panel.set_ports(["COM3", "COM5", "COM8"])

    def test_apply_session_config_serial(self):
        """apply_session_config should set all serial controls."""
        config = {
            "serial": {
                "port": "COM5",
                "baudrate": 9600,
                "databits": 7,
                "stopbits": 2,
                "parity": "Even",
                "flowcontrol": "RTS/CTS",
            },
            "display": {"mode": "monitor", "font_size": 16},
        }
        self.panel.apply_session_config(config)

        assert self.panel.port_combo.currentText() == "COM5"
        assert self.panel.baud_combo.currentText() == "9600"
        assert self.panel.databits_combo.currentText() == "7"
        assert self.panel.stopbits_combo.currentText() == "2"
        assert self.panel.parity_combo.currentText() == "Even"
        assert self.panel.flow_combo.currentText() == "RTS/CTS"
        assert self.panel.font_spin.value() == 16

    def test_apply_session_config_display_mode(self):
        """apply_session_config should set display mode buttons."""
        config = {
            "serial": {"port": "", "baudrate": 115200, "databits": 8, "stopbits": 1, "parity": "None", "flowcontrol": "None"},
            "display": {"mode": "hex", "font_size": 14},
        }
        self.panel.apply_session_config(config)
        assert self.panel.hex_btn.isChecked()
        assert not self.panel.terminal_btn.isChecked()
        assert not self.panel.monitor_btn.isChecked()

    def test_apply_session_config_missing_port(self):
        """apply_session_config should handle a port not in the list."""
        config = {
            "serial": {"port": "COM99", "baudrate": 115200, "databits": 8, "stopbits": 1, "parity": "None", "flowcontrol": "None"},
            "display": {"mode": "terminal", "font_size": 14},
        }
        self.panel.apply_session_config(config)
        # Port not found — combo stays at whatever was there before
        assert self.panel.port_combo.currentText() != "COM99"

    def test_get_session_config(self):
        """get_session_config should return serial + display settings."""
        config = {
            "serial": {"port": "COM3", "baudrate": 115200, "databits": 8, "stopbits": 1, "parity": "None", "flowcontrol": "None"},
            "display": {"mode": "terminal", "font_size": 14},
        }
        self.panel.apply_session_config(config)
        result = self.panel.get_session_config()

        assert result["port"] == "COM3"
        assert result["baudrate"] == 115200
        assert result["display_mode"] == "terminal"
        assert result["font_size"] == 14

    def test_apply_session_config_text_mode_maps_to_terminal(self):
        """V1 'text' mode should map to 'terminal'."""
        config = {
            "serial": {"port": "", "baudrate": 115200, "databits": 8, "stopbits": 1, "parity": "None", "flowcontrol": "None"},
            "display": {"mode": "text", "font_size": 14},
        }
        self.panel.apply_session_config(config)
        assert self.panel.terminal_btn.isChecked()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_settings_panel.py -v`
Expected: AttributeError — `apply_session_config` not found.

- [ ] **Step 3: Add apply_session_config and get_session_config to SettingsPanel**

Add these methods at the end of the `SettingsPanel` class in `settings_panel.py` (after the existing `apply_config` method):

```python
    def apply_session_config(self, config):
        """Load a Session's config dict into all sidebar controls.

        Args:
            config: dict with 'serial' and 'display' sub-dicts.
        """
        serial = config.get("serial", {})
        display = config.get("display", {})

        # Block signals to avoid triggering side effects during bulk update
        self.blockSignals(True)

        idx = self.port_combo.findText(serial.get("port", ""))
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
        self.baud_combo.setCurrentText(str(serial.get("baudrate", 115200)))
        self.databits_combo.setCurrentText(str(serial.get("databits", 8)))
        self.stopbits_combo.setCurrentText(str(serial.get("stopbits", 1)))
        self.parity_combo.setCurrentText(serial.get("parity", "None"))
        self.flow_combo.setCurrentText(serial.get("flowcontrol", "None"))

        mode = display.get("mode", "terminal")
        if mode == "text":
            mode = "terminal"
        self._set_mode(mode)

        self.font_spin.blockSignals(True)
        self.font_spin.setValue(int(display.get("font_size", 14)))
        self.font_spin.blockSignals(False)

        self.blockSignals(False)

    def get_session_config(self):
        """Export current sidebar controls as a session config snippet.

        Returns:
            dict with keys: port, baudrate, databits, stopbits, parity,
            flowcontrol, display_mode, font_size.
        """
        settings = self.get_settings()
        if self.terminal_btn.isChecked():
            settings["display_mode"] = "terminal"
        elif self.monitor_btn.isChecked():
            settings["display_mode"] = "monitor"
        else:
            settings["display_mode"] = "hex"
        settings["font_size"] = self.font_spin.value()
        return settings
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_settings_panel.py -v`
Expected: All 5 tests pass.

- [ ] **Step 5: Run all existing tests to verify no regressions**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\ -v`
Expected: All tests pass (config, terminal, serial_manager, logger, settings_panel, session).

- [ ] **Step 6: Commit**

```bash
cd F:\myTools\mySecureCRT
git add settings_panel.py tests\test_settings_panel.py
git commit -m "feat: add apply_session_config / get_session_config to SettingsPanel

- apply_session_config() loads a Session's serial + display config into controls
- get_session_config() exports current controls as a session config dict
- Blocks signals during bulk update to avoid side effects

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: MainWindow Rewrite — QTabWidget + Session Management

**Files:**
- Modify: `F:\myTools\mySecureCRT\main.py`

- [ ] **Step 1: Rewrite main.py with multi-tab support**

Replace the full content of `main.py`:

```python
import sys
import os
import copy
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QLabel, QMessageBox, QFileDialog, QTabWidget,
    QTabBar, QPushButton, QInputDialog, QShortcut,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence

from serial_manager import SerialManager
from settings_panel import SettingsPanel
from config import ConfigManager, new_session_config
from session import Session


DARK_THEME = """
QMainWindow {
    background-color: #1e1e1e;
}
QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
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
    font-size: 13px;
}
QStatusBar QLabel {
    color: white;
    margin-right: 16px;
}
QTabWidget::pane {
    border: none;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #888888;
    padding: 6px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    border-bottom: 2px solid #007acc;
}
QTabBar::tab:hover:!selected {
    background-color: #353535;
    color: #cccccc;
}
QTabBar::close-button {
    image: none;
    subcontrol-position: right;
}
"""


def _resource_path(relative_path):
    """Get path to resource, works for dev and PyInstaller bundle."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mySecureCRT — 串口终端工具")
        self.setWindowIcon(QIcon(_resource_path("app_icon.ico")))
        self.config = ConfigManager()
        self.config.load()

        self._sessions = {}          # id → Session
        self._active_session = None  # current Session or None
        self._active_connections = []

        self._init_ui()
        self._setup_shortcuts()
        self._restore_sessions()
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

        # Right area: tab widget
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)

        # "+" button in tab bar corner
        add_btn = QPushButton("＋")
        add_btn.setFixedSize(28, 28)
        add_btn.setToolTip("新建会话 (Ctrl+T)")
        add_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #cccccc; border: none; font-size: 16px; }"
            "QPushButton:hover { color: #ffffff; background-color: #3c3c3c; border-radius: 4px; }"
        )
        add_btn.clicked.connect(self._on_new_tab)
        self.tab_widget.setCornerWidget(add_btn, Qt.TopRightCorner)

        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close)
        self.tab_widget.tabBar().doubleClicked.connect(self._on_tab_double_clicked)

        right_layout.addWidget(self.tab_widget)
        main_layout.addLayout(right_layout, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("🔴 未连接")
        self.params_label = QLabel("")
        self.stats_label = QLabel("↑TX: 0  ↓RX: 0")
        self.log_label = QLabel("")
        self.session_count_label = QLabel("")
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addWidget(self.params_label)
        self.status_bar.addPermanentWidget(self.log_label)
        self.status_bar.addPermanentWidget(self.stats_label)
        self.status_bar.addPermanentWidget(self.session_count_label)

        # Connect settings panel signals (these route to active session)
        self.settings_panel.connect_clicked.connect(self._on_connect)
        self.settings_panel.disconnect_clicked.connect(self._on_disconnect)
        self.settings_panel.refresh_clicked.connect(self._refresh_ports)
        self.settings_panel.display_mode_changed.connect(self._on_display_mode_changed)
        self.settings_panel.font_size_changed.connect(self._on_font_size_changed)
        self.settings_panel.clear_clicked.connect(self._on_clear)
        self.settings_panel.save_log_clicked.connect(self._on_save_log)

        # Restore window geometry
        w = self.config.get("window.width") or 900
        h = self.config.get("window.height") or 600
        x = self.config.get("window.x")
        y = self.config.get("window.y")
        self.resize(w, h)
        if x is not None and y is not None:
            self.move(x, y)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, self._on_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, self._on_close_current_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._on_next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._on_prev_tab)

    # ── Session Lifecycle ──

    def _create_session(self, config=None):
        """Create a new Session and add it as a tab. Returns the Session."""
        if config is None:
            config = new_session_config()
        session = Session(config)
        self._sessions[session.id] = session

        # Connect session signals
        session.connection_changed.connect(self._on_session_connection_changed)
        session.error_occurred.connect(self._on_session_error)
        session.name_changed.connect(self._on_session_name_changed)
        session.data_activity.connect(self._on_session_data_activity)
        session.terminal.font_size_changed.connect(self._on_terminal_font_size_changed)

        tab_index = self.tab_widget.addTab(session.terminal, self._tab_label(session))
        self.tab_widget.setCurrentIndex(tab_index)
        self._update_session_count()
        return session

    def _close_session(self, tab_index):
        """Close session at the given tab index."""
        terminal = self.tab_widget.widget(tab_index)
        session = self._session_for_terminal(terminal)
        if session is None:
            return

        session.destroy()
        del self._sessions[session.id]
        self.tab_widget.removeTab(tab_index)

        # Ensure at least one tab exists
        if self.tab_widget.count() == 0:
            self._create_session()

        self._update_session_count()

    def _session_for_terminal(self, terminal):
        """Find the Session that owns a given TerminalWidget."""
        for session in self._sessions.values():
            if session.terminal is terminal:
                return session
        return None

    def _active_session_obj(self):
        """Get the Session for the currently active tab."""
        terminal = self.tab_widget.currentWidget()
        if terminal is None:
            return None
        return self._session_for_terminal(terminal)

    # ── Tab Events ──

    def _on_new_tab(self):
        session = self._create_session()
        session.terminal.setFocus()

    def _on_close_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0:
            self._on_tab_close(idx)

    def _on_next_tab(self):
        count = self.tab_widget.count()
        if count > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % count)

    def _on_prev_tab(self):
        count = self.tab_widget.count()
        if count > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1) % count)

    def _on_tab_close(self, index):
        self._close_session(index)

    def _on_tab_changed(self, index):
        """Switch sidebar and status bar to the newly active tab."""
        session = self._active_session_obj()
        if session is None:
            return

        self._active_session = session

        # Sync sidebar controls to this session's config
        self.settings_panel.apply_session_config(session.config)
        self.settings_panel.set_connected(session.serial_manager.is_connected)

        # Sync status bar
        self._update_status_bar(session)
        self._update_stats(session)

        session.terminal.setFocus()

    def _on_tab_double_clicked(self, index):
        """Rename a tab via dialog."""
        terminal = self.tab_widget.widget(index)
        session = self._session_for_terminal(terminal)
        if session is None:
            return

        new_name, ok = QInputDialog.getText(
            self, "重命名会话", "会话名称:", text=session.name
        )
        if ok and new_name.strip():
            session.name = new_name.strip()
            session.renamed = True
            self.tab_widget.setTabText(index, self._tab_label(session))

    # ── Session Signal Handlers ──

    def _on_session_connection_changed(self, session, connected):
        # Update tab label
        idx = self.tab_widget.indexOf(session.terminal)
        if idx >= 0:
            self.tab_widget.setTabText(idx, self._tab_label(session))

        # Update sidebar and status bar only if this is the active session
        if session is self._active_session:
            self.settings_panel.set_connected(connected)
            self._update_status_bar(session)

    def _on_session_error(self, session, msg):
        QMessageBox.critical(self, "串口错误", f"[{session.name}] {msg}")

    def _on_session_name_changed(self, session):
        idx = self.tab_widget.indexOf(session.terminal)
        if idx >= 0:
            self.tab_widget.setTabText(idx, self._tab_label(session))

    def _on_session_data_activity(self, session):
        if session is self._active_session:
            self._update_stats(session)

    def _on_terminal_font_size_changed(self, size):
        """Sync font size spinner when terminal font changes (Ctrl+scroll)."""
        session = self._active_session_obj()
        if session and session.terminal.font_size == size:
            self.settings_panel.set_font_size(size)
            session.config["display"]["font_size"] = size

    # ── Settings Panel Actions (route to active session) ──

    def _on_connect(self):
        session = self._active_session
        if session is None:
            return
        settings = self.settings_panel.get_settings()
        if not settings["port"]:
            QMessageBox.warning(self, "提示", "请先选择串口端口")
            return
        # Save settings to session config before connecting
        session.update_config_from_settings(self.settings_panel.get_session_config())
        session.serial_manager.open(
            settings["port"], settings["baudrate"], settings["databits"],
            settings["stopbits"], settings["parity"], settings["flowcontrol"],
        )

    def _on_disconnect(self):
        session = self._active_session
        if session is None:
            return
        session.serial_manager.close()

    def _on_display_mode_changed(self, mode):
        session = self._active_session
        if session is None:
            return
        session.terminal.set_display_mode(mode)
        session.config["display"]["mode"] = mode

    def _on_font_size_changed(self, size):
        session = self._active_session
        if session is None:
            return
        session.terminal.set_font_size(size)
        session.config["display"]["font_size"] = size

    def _on_clear(self):
        session = self._active_session
        if session is None:
            return
        session.terminal.clear_terminal()
        self._update_stats(session)

    def _on_save_log(self):
        session = self._active_session
        if session is None:
            return
        if session.logger.is_active:
            session.logger.stop()
            self.log_label.setText("")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "日志文件 (*.log *.txt);;所有文件 (*)"
        )
        if path:
            session.logger.start(path)
            self.log_label.setText("📝 日志记录中")

    def _refresh_ports(self):
        mgr = SerialManager()
        ports = mgr.list_ports()
        self.settings_panel.set_ports(ports)

    # ── UI Helpers ──

    def _tab_label(self, session):
        icon = "🟢" if session.serial_manager.is_connected else "🔴"
        return f"{icon} {session.name}"

    def _update_status_bar(self, session):
        if session.serial_manager.is_connected:
            cfg = session.config["serial"]
            parity_short = "N" if cfg["parity"] == "None" else cfg["parity"][0]
            self.status_label.setText("🟢 已连接")
            self.params_label.setText(
                f"{cfg['port']} | {cfg['baudrate']} {cfg['databits']}{parity_short}{cfg['stopbits']}"
            )
        else:
            self.status_label.setText("🔴 未连接")
            self.params_label.setText("")

    def _update_stats(self, session):
        tx = session.terminal.tx_bytes
        rx = session.terminal.rx_bytes
        self.stats_label.setText(f"↑TX: {tx}  ↓RX: {rx}")

    def _update_session_count(self):
        count = len(self._sessions)
        self.session_count_label.setText(f"{count} 个会话")

    # ── Config Persistence ──

    def _restore_sessions(self):
        """Restore tabs from saved config, or create one default tab."""
        sessions_config = self.config.get("sessions") or []
        active_id = self.config.get("active_session", "")

        if not sessions_config:
            self._create_session()
            return

        active_index = 0
        for i, cfg in enumerate(sessions_config):
            self._create_session(cfg)
            if cfg.get("id") == active_id:
                active_index = i

        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(active_index)

    def _save_config(self):
        """Save all session configs and window geometry."""
        sessions_list = []
        for i in range(self.tab_widget.count()):
            terminal = self.tab_widget.widget(i)
            session = self._session_for_terminal(terminal)
            if session is None:
                continue
            # Sync current sidebar settings to active session
            if session is self._active_session:
                session.update_config_from_settings(
                    self.settings_panel.get_session_config()
                )
            # Sync terminal display state
            session.config["display"]["mode"] = session.terminal.display_mode
            session.config["display"]["font_size"] = session.terminal.font_size
            sessions_list.append(copy.deepcopy(session.config))

        self.config.set("sessions", sessions_list)
        active = self._active_session
        self.config.set("active_session", active.id if active else "")

        geo = self.geometry()
        self.config.set("window.width", geo.width())
        self.config.set("window.height", geo.height())
        self.config.set("window.x", geo.x())
        self.config.set("window.y", geo.y())
        self.config.save()

    def closeEvent(self, event):
        self._save_config()
        for session in list(self._sessions.values()):
            session.destroy()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    window = MainWindow()
    window.show()
    # Focus the active terminal
    active = window._active_session
    if active:
        active.terminal.setFocus()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests to verify no regressions**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\ -v`
Expected: All tests pass. (MainWindow itself is not unit-tested, but no import errors and existing tests remain green.)

- [ ] **Step 3: Commit**

```bash
cd F:\myTools\mySecureCRT
git add main.py
git commit -m "feat: rewrite MainWindow with QTabWidget for multi-tab sessions

- Replace single TerminalWidget with QTabWidget
- Each tab is a Session (SerialManager + TerminalWidget + DataLogger)
- Shared sidebar updates when switching tabs
- Tab operations: new (Ctrl+T), close (Ctrl+W), rename (double-click)
- Restore all tabs from config on startup, save on exit
- Status bar shows active session info + session count

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Manual Smoke Test + Tab Close Button Fix

**Files:**
- Possibly modify: `F:\myTools\mySecureCRT\main.py` (tab close button styling)

- [ ] **Step 1: Run the application**

Run: `cd F:\myTools\mySecureCRT && python main.py`

Verify manually:
1. Application launches with one tab labeled `🔴 新会话`
2. Click ＋ button — a second tab appears
3. Switch between tabs — sidebar controls update
4. Double-click a tab — rename dialog appears
5. Close a tab via × button — tab removed
6. Close the last tab — a new empty tab is auto-created
7. Ctrl+T creates a new tab, Ctrl+W closes the current tab
8. Status bar shows "N 个会话" count
9. Close the app and reopen — tabs are restored

- [ ] **Step 2: Fix any visual issues found during smoke test**

Common issue: QTabBar close button may be invisible in dark theme. If close buttons aren't visible, add this CSS to the `DARK_THEME` string in `main.py`:

```css
QTabBar::close-button {
    image: url(none);
    width: 16px;
    height: 16px;
    subcontrol-position: right;
    border: none;
    background: transparent;
}
```

If needed, switch to using `QTabBar.ButtonPosition` to add custom close buttons.

- [ ] **Step 3: Commit any fixes**

```bash
cd F:\myTools\mySecureCRT
git add -A
git commit -m "fix: polish multi-tab UI after smoke test

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 6: Update README

**Files:**
- Modify: `F:\myTools\mySecureCRT\README.md`

- [ ] **Step 1: Update README feature list and screenshot**

In `README.md`, add multi-tab to the feature list. Under `## ✨ 功能特性`, add a new top-level bullet:

```markdown
- **多标签/多会话**
  - 🗂️ 同时连接多个串口设备（支持 4-8 个标签页）
  - 🔄 共享侧边栏，自动跟随活动标签切换设置
  - ⌨️ Ctrl+T 新建 / Ctrl+W 关闭 / 双击重命名标签
  - 💾 所有标签页配置自动持久化，下次启动恢复
```

Update the ASCII diagram under `## 📸 界面预览` to show tabs:

```
┌──────────────────────────────────────────────────────────┐
│  串口设置    │ [🟢 COM3] [🟢 COM5] [🔴 COM8] [＋]       │
│  端口 COM3   │                                            │
│  波特率 115200│  [0.270] <I> Entering Startup State       │
│  数据位 8    │  [0.471] <W> deserial chip link not locked│
│  ...         │  [1.571] <E> Set error code 0x00000100    │
│  显示设置    │  #DK> help                                │
│  [终端][监控] │  misc     - misc test                     │
│  [HEX]       │  log      - global log level              │
│  字号 14pt   │  help     - print command description     │
│  [清屏][保存] │  #DK> _                                   │
├──────────────┴────────────────────────────────────────────┤
│  🟢 已连接  COM3 | 115200 8N1    ↑TX: 6  ↓RX: 512 | 3 个会话│
└──────────────────────────────────────────────────────────┘
```

Update the project structure section to include `session.py`:

```
├── session.py           # 会话管理（多标签 Session 封装）
```

- [ ] **Step 2: Commit**

```bash
cd F:\myTools\mySecureCRT
git add README.md
git commit -m "docs: update README with multi-tab feature documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Summary

| Task | Component | Tests | Files |
|------|-----------|-------|-------|
| 1 | ConfigManager V2 | 5 new | config.py, test_config.py |
| 2 | Session Module | 7 new | session.py, test_session.py |
| 3 | SettingsPanel methods | 5 new | settings_panel.py, test_settings_panel.py |
| 4 | MainWindow rewrite | 0 (smoke) | main.py |
| 5 | Smoke test + fixes | manual | main.py (if needed) |
| 6 | README update | 0 | README.md |

Dependency order: Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6
