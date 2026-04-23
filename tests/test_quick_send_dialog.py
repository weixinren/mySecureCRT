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
        assert not dlg.hex_error_label.isHidden()
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
