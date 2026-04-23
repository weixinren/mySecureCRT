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
