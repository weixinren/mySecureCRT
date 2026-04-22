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
