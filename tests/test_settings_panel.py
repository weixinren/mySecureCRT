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
