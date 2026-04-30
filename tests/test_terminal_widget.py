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
        line = self.widget._format_monitor_line("RX", b"Hello")
        assert "RX" in line
        assert "Hello" in line
        assert line.startswith("[")

    def test_format_text_tx(self):
        line = self.widget._format_monitor_line("TX", b"AT\r")
        assert "TX" in line
        assert "AT" in line

    def test_format_hex_rx(self):
        line = self.widget._format_hex_line("RX", b"\x48\x65\x6c")
        assert "RX" in line
        assert "48 65 6C" in line.upper()
        assert "Hel" in line

    def test_clear_terminal(self):
        self.widget.set_display_mode("monitor")
        self.widget.append_data("RX", b"data\n")
        self.widget.clear_terminal()
        assert self.widget.toPlainText() == ""

    def test_display_mode_switch(self):
        self.widget.set_display_mode("hex")
        assert self.widget.display_mode == "hex"
        self.widget.set_display_mode("terminal")
        assert self.widget.display_mode == "terminal"


class TestFindBar:
    def setup_method(self):
        self.widget = TerminalWidget()
        self.widget.set_display_mode("monitor")
        self.widget.append_data("RX", b"Hello World\n")
        self.widget.append_data("RX", b"hello test\n")
        self.widget.append_data("RX", b"nothing here\n")

    def test_find_bar_initially_hidden(self):
        assert self.widget._find_bar.isHidden()

    def test_open_close_find_bar(self):
        self.widget._open_find_bar()
        assert not self.widget._find_bar.isHidden()
        self.widget._close_find_bar()
        assert self.widget._find_bar.isHidden()

    def test_find_case_insensitive(self):
        self.widget._open_find_bar()
        self.widget._find_bar.search_input.setText("hello")
        assert len(self.widget._find_matches) == 2
        assert self.widget._find_current == 0

    def test_find_case_sensitive(self):
        self.widget._open_find_bar()
        self.widget._find_bar.case_btn.setChecked(True)
        self.widget._find_bar.search_input.setText("hello")
        assert len(self.widget._find_matches) == 1

    def test_find_next_prev_wraps(self):
        self.widget._open_find_bar()
        self.widget._find_bar.search_input.setText("hello")
        assert self.widget._find_current == 0
        self.widget._find_next()
        assert self.widget._find_current == 1
        self.widget._find_next()
        assert self.widget._find_current == 0  # wraps
        self.widget._find_prev()
        assert self.widget._find_current == 1  # wraps back

    def test_find_no_matches(self):
        self.widget._open_find_bar()
        self.widget._find_bar.search_input.setText("nonexistent")
        assert len(self.widget._find_matches) == 0
        assert self.widget._find_current == -1

    def test_close_clears_highlights(self):
        self.widget._open_find_bar()
        self.widget._find_bar.search_input.setText("hello")
        assert len(self.widget._find_matches) == 2
        self.widget._close_find_bar()
        assert len(self.widget._find_matches) == 0
        assert self.widget.extraSelections() == []
