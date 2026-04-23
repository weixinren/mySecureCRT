# Quick Send Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a right-side quick send panel with command buttons, command groups, HEX/text support, and loop sending for rapid embedded debugging.

**Architecture:** New `QuickSendPanel` widget on the right side of MainWindow, mirroring the left `SettingsPanel`. Commands are organized in named groups, persisted in config.json under `quick_send`. Each command button encodes data (text or HEX) and emits a signal that MainWindow routes to the active session's serial port. Loop sending uses per-button QTimers.

**Tech Stack:** Python 3.8+, PyQt5, pyserial, pytest

---

## File Structure

```
F:\myTools\mySecureCRT\
├── quick_send_panel.py      # NEW — QuickSendPanel + CommandButton + encode_command_data
├── quick_send_dialog.py     # NEW — CommandDialog + LoopDialog
├── config.py                # MODIFY — add quick_send to DEFAULT_CONFIG
├── main.py                  # MODIFY — add QuickSendPanel to layout, connect signals
└── tests\
    ├── test_quick_send_panel.py   # NEW — encode, button, panel tests
    ├── test_quick_send_dialog.py  # NEW — dialog tests
    └── test_config.py             # MODIFY — add quick_send config tests
```

---

### Task 1: Config — Add quick_send to DEFAULT_CONFIG

**Files:**
- Modify: `F:\myTools\mySecureCRT\config.py`
- Modify: `F:\myTools\mySecureCRT\tests\test_config.py`

- [ ] **Step 1: Write failing tests for quick_send config**

Add these two test methods to the existing `TestConfigManager` class in `tests/test_config.py`:

```python
    def test_default_config_has_quick_send(self):
        """Default config should include quick_send field."""
        qs = self.mgr.get("quick_send")
        assert qs is not None
        assert "groups" in qs
        assert "active_group" in qs
        assert len(qs["groups"]) == 1
        assert qs["groups"][0]["name"] == "默认命令组"

    def test_quick_send_save_and_load(self):
        """quick_send config should persist."""
        qs = {
            "collapsed": True,
            "groups": [
                {"id": "g1", "name": "Test", "commands": [
                    {"id": "c1", "name": "cmd", "data": "test", "type": "text",
                     "append_newline": True, "loop_interval_ms": 0}
                ]}
            ],
            "active_group": "g1",
        }
        self.mgr.set("quick_send", qs)
        self.mgr.save()

        mgr2 = ConfigManager(self.config_path)
        mgr2.load()
        loaded = mgr2.get("quick_send")
        assert loaded["collapsed"] is True
        assert len(loaded["groups"]) == 1
        assert loaded["groups"][0]["commands"][0]["name"] == "cmd"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_config.py::TestConfigManager::test_default_config_has_quick_send tests\test_config.py::TestConfigManager::test_quick_send_save_and_load -v`
Expected: FAIL — `qs` is `None` because `quick_send` not in DEFAULT_CONFIG.

- [ ] **Step 3: Add quick_send to DEFAULT_CONFIG**

In `config.py`, replace the `DEFAULT_CONFIG` dict (lines 7-16) with:

```python
DEFAULT_CONFIG = {
    "sessions": [],
    "active_session": "",
    "window": {
        "width": 900,
        "height": 600,
        "x": 100,
        "y": 100,
    },
    "quick_send": {
        "collapsed": False,
        "groups": [
            {
                "id": "default",
                "name": "默认命令组",
                "commands": [],
            }
        ],
        "active_group": "default",
    },
}
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_config.py -v`
Expected: All 12 tests pass.

- [ ] **Step 5: Run all tests to verify no regressions**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\ -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
cd F:\myTools\mySecureCRT
git add config.py tests\test_config.py
git commit -m "feat: add quick_send field to config schema

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 2: CommandDialog + LoopDialog

**Files:**
- Create: `F:\myTools\mySecureCRT\quick_send_dialog.py`
- Create: `F:\myTools\mySecureCRT\tests\test_quick_send_dialog.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_quick_send_dialog.py`:

```python
import sys
import pytest
from PyQt5.QtWidgets import QApplication, QDialogButtonBox

app = QApplication.instance() or QApplication(sys.argv)

from quick_send_dialog import CommandDialog, LoopDialog


class TestCommandDialog:
    def test_new_command_defaults(self):
        """New command dialog should have empty fields and default type."""
        dlg = CommandDialog()
        assert dlg.name_edit.text() == ""
        assert dlg.type_combo.currentText() == "文本"
        assert dlg.data_edit.text() == ""
        assert dlg.newline_check.isChecked()
        assert dlg.newline_check.isEnabled()

    def test_edit_command_prefills(self):
        """Edit mode should prefill controls from command dict."""
        cmd = {
            "id": "abc123",
            "name": "test cmd",
            "data": "AA BB CC",
            "type": "hex",
            "append_newline": False,
            "loop_interval_ms": 0,
        }
        dlg = CommandDialog(command=cmd)
        assert dlg.name_edit.text() == "test cmd"
        assert dlg.type_combo.currentText() == "HEX"
        assert dlg.data_edit.text() == "AA BB CC"
        assert not dlg.newline_check.isChecked()
        assert not dlg.newline_check.isEnabled()

    def test_hex_validation_valid(self):
        """Valid hex should not show error."""
        dlg = CommandDialog()
        dlg.name_edit.setText("test")
        dlg.type_combo.setCurrentText("HEX")
        dlg.data_edit.setText("AA 55 01 FF")
        assert dlg.hex_error_label.isHidden()
        ok_btn = dlg.buttons.button(QDialogButtonBox.Ok)
        assert ok_btn.isEnabled()

    def test_hex_validation_invalid(self):
        """Invalid hex should show error and disable OK."""
        dlg = CommandDialog()
        dlg.name_edit.setText("test")
        dlg.type_combo.setCurrentText("HEX")
        dlg.data_edit.setText("GG ZZ")
        assert dlg.hex_error_label.isVisible()
        ok_btn = dlg.buttons.button(QDialogButtonBox.Ok)
        assert not ok_btn.isEnabled()

    def test_newline_disabled_for_hex(self):
        """Switching to HEX should disable and uncheck newline."""
        dlg = CommandDialog()
        assert dlg.newline_check.isEnabled()
        assert dlg.newline_check.isChecked()
        dlg.type_combo.setCurrentText("HEX")
        assert not dlg.newline_check.isEnabled()
        assert not dlg.newline_check.isChecked()


class TestLoopDialog:
    def test_default_interval(self):
        """Default interval should be 1000ms."""
        dlg = LoopDialog()
        assert dlg.interval_spin.value() == 1000

    def test_custom_interval(self):
        """Custom interval should be set."""
        dlg = LoopDialog(current_interval=500)
        assert dlg.interval_spin.value() == 500

    def test_interval_range(self):
        """Interval should be clamped to 100-60000."""
        dlg = LoopDialog()
        assert dlg.interval_spin.minimum() == 100
        assert dlg.interval_spin.maximum() == 60000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_quick_send_dialog.py -v`
Expected: ImportError — `quick_send_dialog` module not found.

- [ ] **Step 3: Implement CommandDialog and LoopDialog**

Create `quick_send_dialog.py`:

```python
import uuid
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QSpinBox, QDialogButtonBox,
)


class CommandDialog(QDialog):
    """Dialog for creating or editing a quick send command."""

    def __init__(self, parent=None, command=None):
        super().__init__(parent)
        self.setWindowTitle("编辑命令" if command else "添加命令")
        self.setMinimumWidth(320)
        self._command = command
        self._init_ui()
        if command:
            self._load_command(command)
        self._validate()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("命令显示名称")
        self.name_edit.textChanged.connect(self._validate)
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["文本", "HEX"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        layout.addWidget(QLabel("数据:"))
        self.data_edit = QLineEdit()
        self.data_edit.setPlaceholderText("发送内容")
        self.data_edit.textChanged.connect(self._validate)
        layout.addWidget(self.data_edit)

        self.hex_error_label = QLabel("")
        self.hex_error_label.setStyleSheet("color: #f44747; font-size: 11px;")
        self.hex_error_label.hide()
        layout.addWidget(self.hex_error_label)

        self.newline_check = QCheckBox("追加换行 (\\r\\n)")
        self.newline_check.setChecked(True)
        layout.addWidget(self.newline_check)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def _load_command(self, cmd):
        self.name_edit.setText(cmd.get("name", ""))
        if cmd.get("type") == "hex":
            self.type_combo.setCurrentText("HEX")
        else:
            self.type_combo.setCurrentText("文本")
        self.data_edit.setText(cmd.get("data", ""))
        self.newline_check.setChecked(cmd.get("append_newline", True))

    def _on_type_changed(self, type_text):
        is_hex = (type_text == "HEX")
        self.newline_check.setEnabled(not is_hex)
        if is_hex:
            self.newline_check.setChecked(False)
        self._validate()

    def _validate(self):
        is_hex = (self.type_combo.currentText() == "HEX")
        name = self.name_edit.text().strip()
        data = self.data_edit.text().strip()
        ok_btn = self.buttons.button(QDialogButtonBox.Ok)

        if not name or not data:
            ok_btn.setEnabled(False)
            self.hex_error_label.hide()
            self.data_edit.setStyleSheet("")
            return

        if is_hex:
            hex_str = data.replace(" ", "")
            valid = (
                len(hex_str) > 0
                and len(hex_str) % 2 == 0
                and all(c in "0123456789abcdefABCDEF" for c in hex_str)
            )
            if not valid:
                self.hex_error_label.setText("HEX 格式错误（如: AA 55 01 FF）")
                self.hex_error_label.show()
                self.data_edit.setStyleSheet("border: 1px solid #f44747;")
                ok_btn.setEnabled(False)
                return

        self.hex_error_label.hide()
        self.data_edit.setStyleSheet("")
        ok_btn.setEnabled(True)

    def get_command(self):
        """Return command dict, or None if dialog was cancelled."""
        if self.result() != QDialog.Accepted:
            return None
        cmd_type = "hex" if self.type_combo.currentText() == "HEX" else "text"
        return {
            "id": self._command["id"] if self._command else uuid.uuid4().hex[:8],
            "name": self.name_edit.text().strip(),
            "data": self.data_edit.text().strip(),
            "type": cmd_type,
            "append_newline": self.newline_check.isChecked() and cmd_type == "text",
            "loop_interval_ms": self._command.get("loop_interval_ms", 0) if self._command else 0,
        }


class LoopDialog(QDialog):
    """Dialog for setting loop send interval."""

    def __init__(self, parent=None, current_interval=1000):
        super().__init__(parent)
        self.setWindowTitle("循环发送设置")
        self._init_ui(current_interval)

    def _init_ui(self, current_interval):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("发送间隔 (毫秒):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 60000)
        self.interval_spin.setValue(current_interval)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setSingleStep(100)
        layout.addWidget(self.interval_spin)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_interval(self):
        """Return interval in ms, or None if cancelled."""
        if self.result() != QDialog.Accepted:
            return None
        return self.interval_spin.value()
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_quick_send_dialog.py -v`
Expected: All 8 tests pass.

- [ ] **Step 5: Run all tests to verify no regressions**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\ -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
cd F:\myTools\mySecureCRT
git add quick_send_dialog.py tests\test_quick_send_dialog.py
git commit -m "feat: add CommandDialog and LoopDialog for quick send

- CommandDialog: create/edit commands with name, data, type (text/HEX), newline option
- LoopDialog: set loop interval (100-60000ms)
- HEX validation with real-time error feedback

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 3: QuickSendPanel + CommandButton

**Files:**
- Create: `F:\myTools\mySecureCRT\quick_send_panel.py`
- Create: `F:\myTools\mySecureCRT\tests\test_quick_send_panel.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_quick_send_panel.py`:

```python
import sys
import pytest
from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from quick_send_panel import QuickSendPanel, CommandButton, encode_command_data


class TestEncodeCommandData:
    def test_text_with_newline(self):
        result = encode_command_data("help", "text", append_newline=True)
        assert result == b"help\r\n"

    def test_text_without_newline(self):
        result = encode_command_data("help", "text", append_newline=False)
        assert result == b"help"

    def test_hex(self):
        result = encode_command_data("AA 55 01 FF", "hex")
        assert result == b"\xaa\x55\x01\xff"


class TestCommandButton:
    def _make_command(self, **overrides):
        cmd = {
            "id": "test1", "name": "test", "data": "hello",
            "type": "text", "append_newline": True, "loop_interval_ms": 0,
        }
        cmd.update(overrides)
        return cmd

    def test_encode_text(self):
        btn = CommandButton(self._make_command())
        assert btn.encode_data() == b"hello\r\n"

    def test_encode_hex(self):
        btn = CommandButton(self._make_command(data="AA BB", type="hex"))
        assert btn.encode_data() == b"\xaa\xbb"

    def test_loop_start_stop(self):
        btn = CommandButton(self._make_command())
        assert not btn.is_looping
        btn.start_loop(1000)
        assert btn.is_looping
        assert btn._timer.isActive()
        btn.stop_loop()
        assert not btn.is_looping
        assert not btn._timer.isActive()


class TestQuickSendPanel:
    def _sample_config(self):
        return {
            "collapsed": False,
            "groups": [
                {
                    "id": "g1", "name": "调试命令",
                    "commands": [
                        {"id": "c1", "name": "help", "data": "help", "type": "text",
                         "append_newline": True, "loop_interval_ms": 0},
                        {"id": "c2", "name": "心跳", "data": "AA 55", "type": "hex",
                         "append_newline": False, "loop_interval_ms": 1000},
                    ],
                },
                {
                    "id": "g2", "name": "协议测试",
                    "commands": [
                        {"id": "c3", "name": "ping", "data": "ping", "type": "text",
                         "append_newline": True, "loop_interval_ms": 0},
                    ],
                },
            ],
            "active_group": "g1",
        }

    def test_set_get_config(self):
        panel = QuickSendPanel()
        config = self._sample_config()
        panel.set_config(config)
        result = panel.get_config()
        assert len(result["groups"]) == 2
        assert result["active_group"] == "g1"
        assert result["groups"][0]["name"] == "调试命令"
        assert len(result["groups"][0]["commands"]) == 2

    def test_buttons_created_for_group(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        assert len(panel._buttons) == 2

    def test_switch_group_updates_buttons(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        assert len(panel._buttons) == 2
        panel._group_combo.setCurrentIndex(1)
        assert len(panel._buttons) == 1

    def test_send_text_signal(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        signals = []
        panel.send_requested.connect(lambda data: signals.append(data))
        panel._buttons[0]._on_clicked()
        assert len(signals) == 1
        assert signals[0] == b"help\r\n"

    def test_send_hex_signal(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        signals = []
        panel.send_requested.connect(lambda data: signals.append(data))
        panel._buttons[1]._on_clicked()
        assert len(signals) == 1
        assert signals[0] == b"\xaa\x55"

    def test_stop_all_loops(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        panel._buttons[0].start_loop(1000)
        panel._buttons[1].start_loop(500)
        assert panel._buttons[0].is_looping
        assert panel._buttons[1].is_looping
        panel.stop_all_loops()
        assert not panel._buttons[0].is_looping
        assert not panel._buttons[1].is_looping

    def test_collapse_expand(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        assert not panel.is_collapsed
        panel.set_collapsed(True)
        assert panel.is_collapsed
        assert panel.fixedWidth() == 32
        panel.set_collapsed(False)
        assert not panel.is_collapsed
        assert panel.fixedWidth() == 180

    def test_empty_group_shows_placeholder(self):
        panel = QuickSendPanel()
        panel.set_config({
            "collapsed": False,
            "groups": [{"id": "g1", "name": "空组", "commands": []}],
            "active_group": "g1",
        })
        assert len(panel._buttons) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_quick_send_panel.py -v`
Expected: ImportError — `quick_send_panel` module not found.

- [ ] **Step 3: Implement QuickSendPanel and CommandButton**

Create `quick_send_panel.py`:

```python
import uuid
import copy
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QMenu, QInputDialog, QMessageBox,
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer

from quick_send_dialog import CommandDialog, LoopDialog


def encode_command_data(data, cmd_type, append_newline=True):
    """Encode command data string to bytes."""
    if cmd_type == "hex":
        return bytes.fromhex(data.replace(" ", ""))
    encoded = data.encode("utf-8")
    if append_newline:
        encoded += b"\r\n"
    return encoded


class CommandButton(QPushButton):
    """A button representing a single quick-send command."""

    send_clicked = pyqtSignal(bytes)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    copy_requested = pyqtSignal(str)
    loop_requested = pyqtSignal(str)

    def __init__(self, command, parent=None):
        super().__init__(parent)
        self._command = command
        self._looping = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_loop_tick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.clicked.connect(self._on_clicked)
        self._update_display()

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, cmd):
        self._command = cmd
        self._update_display()

    @property
    def is_looping(self):
        return self._looping

    def encode_data(self):
        return encode_command_data(
            self._command["data"],
            self._command["type"],
            self._command.get("append_newline", True),
        )

    def start_loop(self, interval_ms):
        self._command["loop_interval_ms"] = interval_ms
        self._looping = True
        self._timer.start(interval_ms)
        self._update_display()

    def stop_loop(self):
        self._looping = False
        self._timer.stop()
        self._update_display()

    def _on_clicked(self):
        if self._looping:
            self.stop_loop()
            return
        try:
            data = self.encode_data()
            self.send_clicked.emit(data)
        except (ValueError, Exception):
            pass

    def _on_loop_tick(self):
        try:
            data = self.encode_data()
            self.send_clicked.emit(data)
        except (ValueError, Exception):
            self.stop_loop()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        edit_action = menu.addAction("✏️ 编辑命令...")
        copy_action = menu.addAction("📋 复制命令")
        menu.addSeparator()
        if self._looping:
            loop_action = menu.addAction("⏹ 停止循环发送")
        else:
            loop_action = menu.addAction("🔁 设置循环发送...")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 删除")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == edit_action:
            self.edit_requested.emit(self._command["id"])
        elif action == copy_action:
            self.copy_requested.emit(self._command["id"])
        elif action == loop_action:
            self.loop_requested.emit(self._command["id"])
        elif action == delete_action:
            self.delete_requested.emit(self._command["id"])

    def _update_display(self):
        cmd = self._command
        if self._looping:
            prefix = "🔁"
        elif cmd["type"] == "hex":
            prefix = "🔢"
        else:
            prefix = "📝"
        name = cmd["name"]
        if len(name) > 14:
            name = name[:12] + "…"
        self.setText(f"{prefix} {name}")

        if self._looping:
            self.setStyleSheet(
                "QPushButton { background-color: #0d4f3c; color: #4ec9b0; "
                "border: 1px solid #4ec9b0; border-radius: 4px; padding: 6px 8px; "
                "text-align: left; font-size: 12px; min-height: 20px; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background-color: #3c3c3c; color: #cccccc; "
                "border: 1px solid #555555; border-radius: 4px; padding: 6px 8px; "
                "text-align: left; font-size: 12px; min-height: 20px; }"
                "QPushButton:hover { background-color: #4c4c4c; }"
            )


class QuickSendPanel(QWidget):
    """Right-side panel for quick-send command buttons."""

    send_requested = pyqtSignal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = []
        self._active_group_id = ""
        self._collapsed = False
        self._buttons = []
        self._init_ui()

    def _init_ui(self):
        self.setFixedWidth(180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(32)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 4, 4)
        self._title_label = QLabel("⚡ 快捷发送")
        self._title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self._collapse_btn = QPushButton("◀")
        self._collapse_btn.setFixedSize(22, 22)
        self._collapse_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #888; font-size: 12px; }"
            "QPushButton:hover { color: #fff; }"
        )
        self._collapse_btn.clicked.connect(self._on_collapse_toggle)
        header_layout.addWidget(self._title_label, 1)
        header_layout.addWidget(self._collapse_btn)
        layout.addWidget(header)

        # Content (hidden when collapsed)
        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(6, 4, 6, 6)
        content_layout.setSpacing(4)

        # Group selector row
        group_row = QHBoxLayout()
        group_row.setSpacing(2)
        self._group_combo = QComboBox()
        self._group_combo.setStyleSheet("font-size: 11px;")
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        self._add_group_btn = QPushButton("＋")
        self._add_group_btn.setFixedSize(24, 24)
        self._add_group_btn.setToolTip("新建命令组")
        self._add_group_btn.clicked.connect(self._on_add_group)
        self._del_group_btn = QPushButton("🗑")
        self._del_group_btn.setFixedSize(24, 24)
        self._del_group_btn.setToolTip("删除当前命令组")
        self._del_group_btn.clicked.connect(self._on_delete_group)
        group_row.addWidget(self._group_combo, 1)
        group_row.addWidget(self._add_group_btn)
        group_row.addWidget(self._del_group_btn)
        content_layout.addLayout(group_row)

        # Scroll area for command buttons
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._btn_container = QWidget()
        self._btn_container.setStyleSheet("background: transparent;")
        self._btn_layout = QVBoxLayout(self._btn_container)
        self._btn_layout.setContentsMargins(0, 0, 0, 0)
        self._btn_layout.setSpacing(3)
        self._btn_layout.addStretch()
        self._scroll.setWidget(self._btn_container)
        content_layout.addWidget(self._scroll, 1)

        # Placeholder
        self._placeholder = QLabel("点击下方按钮\n添加命令")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #666; font-size: 11px; padding: 20px;")

        # Add command button
        self._add_cmd_btn = QPushButton("＋ 添加命令")
        self._add_cmd_btn.setStyleSheet(
            "QPushButton { background-color: #0e639c; color: #fff; border: none; "
            "border-radius: 3px; padding: 6px; font-size: 11px; }"
            "QPushButton:hover { background-color: #1177bb; }"
        )
        self._add_cmd_btn.clicked.connect(self._on_add_command)
        content_layout.addWidget(self._add_cmd_btn)

        layout.addWidget(self._content, 1)

    # ── Public API ──

    def set_config(self, config):
        """Load quick_send config dict."""
        self._groups = copy.deepcopy(config.get("groups", []))
        self._active_group_id = config.get("active_group", "")
        self._collapsed = config.get("collapsed", False)

        if not self._groups:
            self._groups = [{"id": "default", "name": "默认命令组", "commands": []}]
            self._active_group_id = "default"

        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        for g in self._groups:
            self._group_combo.addItem(g["name"], g["id"])
        idx = next((i for i, g in enumerate(self._groups)
                     if g["id"] == self._active_group_id), 0)
        self._group_combo.setCurrentIndex(idx)
        self._group_combo.blockSignals(False)

        self._rebuild_buttons()
        self.set_collapsed(self._collapsed)

    def get_config(self):
        """Export quick_send config dict."""
        return {
            "collapsed": self._collapsed,
            "groups": copy.deepcopy(self._groups),
            "active_group": self._active_group_id,
        }

    def stop_all_loops(self):
        """Stop all active loop timers."""
        for btn in self._buttons:
            if btn.is_looping:
                btn.stop_loop()

    @property
    def is_collapsed(self):
        return self._collapsed

    def set_collapsed(self, collapsed):
        self._collapsed = collapsed
        if collapsed:
            self._content.hide()
            self._title_label.hide()
            self._collapse_btn.setText("▶")
            self.setFixedWidth(32)
        else:
            self._content.show()
            self._title_label.show()
            self._collapse_btn.setText("◀")
            self.setFixedWidth(180)

    # ── Internal ──

    def _current_group(self):
        for g in self._groups:
            if g["id"] == self._active_group_id:
                return g
        return self._groups[0] if self._groups else None

    def _rebuild_buttons(self):
        for btn in self._buttons:
            btn.stop_loop()
            btn.deleteLater()
        self._buttons.clear()

        # Clear layout
        while self._btn_layout.count() > 0:
            item = self._btn_layout.takeAt(0)
            w = item.widget()
            if w and w is not self._placeholder:
                w.deleteLater()

        if self._placeholder.parent():
            self._placeholder.setParent(None)

        group = self._current_group()
        if group is None or not group["commands"]:
            self._btn_layout.addWidget(self._placeholder)
            self._btn_layout.addStretch()
            return

        for cmd in group["commands"]:
            btn = CommandButton(cmd)
            btn.send_clicked.connect(self.send_requested.emit)
            btn.edit_requested.connect(self._on_edit_command)
            btn.delete_requested.connect(self._on_delete_command)
            btn.copy_requested.connect(self._on_copy_command)
            btn.loop_requested.connect(self._on_loop_command)
            self._btn_layout.addWidget(btn)
            self._buttons.append(btn)
        self._btn_layout.addStretch()

    def _on_collapse_toggle(self):
        self.set_collapsed(not self._collapsed)

    def _on_group_changed(self, index):
        if 0 <= index < len(self._groups):
            self._active_group_id = self._groups[index]["id"]
            self._rebuild_buttons()

    def _on_add_group(self):
        name, ok = QInputDialog.getText(self, "新建命令组", "命令组名称:")
        if ok and name.strip():
            group = {"id": uuid.uuid4().hex[:8], "name": name.strip(), "commands": []}
            self._groups.append(group)
            self._group_combo.blockSignals(True)
            self._group_combo.addItem(group["name"], group["id"])
            self._group_combo.setCurrentIndex(self._group_combo.count() - 1)
            self._group_combo.blockSignals(False)
            self._active_group_id = group["id"]
            self._rebuild_buttons()

    def _on_delete_group(self):
        if len(self._groups) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个命令组")
            return
        group = self._current_group()
        if group is None:
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除命令组「{group['name']}」及其所有命令？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._groups.remove(group)
        self._group_combo.blockSignals(True)
        self._group_combo.removeItem(self._group_combo.currentIndex())
        self._group_combo.blockSignals(False)
        self._active_group_id = self._groups[0]["id"]
        self._group_combo.setCurrentIndex(0)
        self._rebuild_buttons()

    def _on_add_command(self):
        dlg = CommandDialog(self)
        if dlg.exec_():
            cmd = dlg.get_command()
            if cmd:
                group = self._current_group()
                if group is not None:
                    group["commands"].append(cmd)
                    self._rebuild_buttons()

    def _on_edit_command(self, cmd_id):
        group = self._current_group()
        if group is None:
            return
        for i, cmd in enumerate(group["commands"]):
            if cmd["id"] == cmd_id:
                dlg = CommandDialog(self, command=cmd)
                if dlg.exec_():
                    updated = dlg.get_command()
                    if updated:
                        group["commands"][i] = updated
                        self._rebuild_buttons()
                return

    def _on_delete_command(self, cmd_id):
        group = self._current_group()
        if group is None:
            return
        for btn in self._buttons:
            if btn.command["id"] == cmd_id and btn.is_looping:
                btn.stop_loop()
        group["commands"] = [c for c in group["commands"] if c["id"] != cmd_id]
        self._rebuild_buttons()

    def _on_copy_command(self, cmd_id):
        group = self._current_group()
        if group is None:
            return
        for cmd in group["commands"]:
            if cmd["id"] == cmd_id:
                new_cmd = copy.deepcopy(cmd)
                new_cmd["id"] = uuid.uuid4().hex[:8]
                new_cmd["name"] = cmd["name"] + " (副本)"
                group["commands"].append(new_cmd)
                self._rebuild_buttons()
                return

    def _on_loop_command(self, cmd_id):
        for btn in self._buttons:
            if btn.command["id"] == cmd_id:
                if btn.is_looping:
                    btn.stop_loop()
                else:
                    current = btn.command.get("loop_interval_ms", 1000) or 1000
                    dlg = LoopDialog(self, current_interval=current)
                    if dlg.exec_():
                        interval = dlg.get_interval()
                        if interval:
                            btn.start_loop(interval)
                return
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\test_quick_send_panel.py -v`
Expected: All 11 tests pass (3 encode + 3 button + 5 panel).

- [ ] **Step 5: Run all tests to verify no regressions**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\ -v`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
cd F:\myTools\mySecureCRT
git add quick_send_panel.py tests\test_quick_send_panel.py
git commit -m "feat: add QuickSendPanel with command buttons and loop sending

- encode_command_data: text/HEX encoding with optional newline
- CommandButton: left-click send, right-click menu, QTimer loop
- QuickSendPanel: command groups, collapse/expand, CRUD operations

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 4: MainWindow Integration

**Files:**
- Modify: `F:\myTools\mySecureCRT\main.py`

- [ ] **Step 1: Add QuickSendPanel import**

In `main.py`, after line 15 (`from session import Session`), add:

```python
from quick_send_panel import QuickSendPanel
```

- [ ] **Step 2: Add QuickSendPanel to layout**

In `main.py`, after the line `main_layout.addLayout(right_layout, 1)` (line 188), add:

```python
        # Right-side quick send panel
        self.quick_send_panel = QuickSendPanel()
        self.quick_send_panel.setStyleSheet(
            "QuickSendPanel { background-color: #252526; border-left: 1px solid #333333; }"
        )
        self.quick_send_panel.send_requested.connect(self._on_quick_send)
        main_layout.addWidget(self.quick_send_panel)
```

- [ ] **Step 3: Add quick send restore to __init__**

In `main.py`, after the line `self._refresh_ports()` in `__init__`, add:

```python
        self._restore_quick_send()
```

- [ ] **Step 4: Add _restore_quick_send and _on_quick_send methods**

In `main.py`, add these methods in the "Settings Panel Actions" section (after `_refresh_ports`):

```python
    # ── Quick Send ──

    def _on_quick_send(self, data):
        """Route quick send data to active session's serial port."""
        session = self._active_session
        if session and session.serial_manager.is_connected:
            session.serial_manager.write(data)

    def _restore_quick_send(self):
        """Load quick send config into panel."""
        qs_config = self.config.get("quick_send")
        if qs_config:
            self.quick_send_panel.set_config(qs_config)
```

- [ ] **Step 5: Save quick_send config in _save_config**

In `main.py`, in the `_save_config` method, add this line before `self.config.save()`:

```python
        self.config.set("quick_send", self.quick_send_panel.get_config())
```

- [ ] **Step 6: Stop loops in closeEvent**

In `main.py`, in the `closeEvent` method, add this line as the first line of the method body (before `self._save_config()`):

```python
        self.quick_send_panel.stop_all_loops()
```

- [ ] **Step 7: Run all tests to verify no regressions**

Run: `cd F:\myTools\mySecureCRT && python -m pytest tests\ -v`
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
cd F:\myTools\mySecureCRT
git add main.py
git commit -m "feat: integrate QuickSendPanel into MainWindow

- Add right-side quick send panel to main layout
- Route send_requested signal to active session serial port
- Save/restore quick send config on exit/startup
- Stop all loops on application close

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 5: Smoke Test + Fixes

**Files:**
- Possibly modify: `F:\myTools\mySecureCRT\main.py`, `F:\myTools\mySecureCRT\quick_send_panel.py`

- [ ] **Step 1: Run the application**

Run: `cd F:\myTools\mySecureCRT && python main.py`

Verify manually:
1. Application launches with three-column layout (settings | terminal+tabs | quick send)
2. Quick send panel shows "默认命令组" with empty command list and placeholder text
3. Click "＋ 添加命令" — dialog appears, add a text command "help"
4. Command button appears in the list with 📝 icon
5. Click the button — no crash (won't send without serial connection)
6. Right-click button — context menu appears with edit/copy/loop/delete
7. Click ◀ button — panel collapses to narrow strip
8. Click ▶ — panel expands back
9. Close and reopen — command persists
10. Add a HEX command with data "AA 55 01" — appears with 🔢 icon

- [ ] **Step 2: Run headless smoke test**

Run:
```python
cd F:\myTools\mySecureCRT && python -c "
import sys
from PyQt5.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
from main import MainWindow, DARK_THEME
app.setStyleSheet(DARK_THEME)
w = MainWindow()
assert hasattr(w, 'quick_send_panel'), 'Missing quick_send_panel'
assert w.quick_send_panel.fixedWidth() == 180, 'Wrong panel width'
print('Quick send panel integrated OK')
print('Smoke test PASSED')
"
```

- [ ] **Step 3: Fix any issues found during smoke test**

If visual issues are found, fix them and commit.

- [ ] **Step 4: Commit any fixes**

```bash
cd F:\myTools\mySecureCRT
git add -A
git commit -m "fix: polish quick send panel after smoke test

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

### Task 6: Update README

**Files:**
- Modify: `F:\myTools\mySecureCRT\README.md`

- [ ] **Step 1: Add quick send feature to README**

In `README.md`, under `## ✨ 功能特性`, after the multi-tab section, add:

```markdown
- **快捷发送面板**
  - ⚡ 预设常用命令，一键发送到活动串口
  - 🔢 支持文本和 HEX 两种命令类型
  - 🔁 循环定时发送（如心跳包，间隔 100ms~60s）
  - 📂 命令分组管理，不同项目不同命令集
  - 右键菜单：编辑 / 复制 / 删除 / 循环设置
```

Update the ASCII diagram under `## 📸 界面预览` to show three-column layout:

```
┌──────────┬──────────────────────────────┬──────────┐
│ 串口设置  │ [🟢 COM3] [🟢 COM5] [＋新建]  │⚡快捷发送 │
│ 端口 COM3 │                              │ 调试命令 ▾│
│ 波特率... │ [0.270] <I> Entering Startup │ 📝 help  │
│ 数据位 8  │ [0.471] <W> chip not locked  │ 📝 reboot│
│ 显示设置  │ #DK> help                    │ 🔁 心跳包│
│ [终端]... │ misc  - misc test            │ 🔢 AA 55 │
│ [清屏]    │ #DK> _                       │[＋添加命令]│
├──────────┴──────────────────────────────┴──────────┤
│ 🟢 已连接  COM3 | 115200 8N1  ↑TX:6 ↓RX:512 3个会话│
└───────────────────────────────────────────────────┘
```

Add `quick_send_panel.py` and `quick_send_dialog.py` to the project structure section:

```
├── quick_send_panel.py  # 快捷发送面板（命令按钮 + 循环发送）
├── quick_send_dialog.py # 命令编辑 / 循环设置对话框
```

And add the corresponding test files:

```
    ├── test_quick_send_panel.py
    ├── test_quick_send_dialog.py
```

Update the config section to mention quick send:

```markdown
- 快捷发送命令组（命令名称、数据、类型、循环间隔）
```

- [ ] **Step 2: Commit**

```bash
cd F:\myTools\mySecureCRT
git add README.md
git commit -m "docs: update README with quick send panel feature

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Summary

| Task | Component | Tests | Files |
|------|-----------|-------|-------|
| 1 | Config quick_send | 2 new | config.py, test_config.py |
| 2 | CommandDialog + LoopDialog | 8 new | quick_send_dialog.py, test_quick_send_dialog.py |
| 3 | QuickSendPanel + CommandButton | 11 new | quick_send_panel.py, test_quick_send_panel.py |
| 4 | MainWindow integration | 0 (smoke) | main.py |
| 5 | Smoke test + fixes | manual | main.py, quick_send_panel.py (if needed) |
| 6 | README update | 0 | README.md |

Dependency order: Task 1 (independent), Task 2 (independent) → Task 3 (needs Task 2) → Task 4 (needs Tasks 1, 3) → Task 5 → Task 6
