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
