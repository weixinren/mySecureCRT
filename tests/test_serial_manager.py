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
        mgr.close()

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
        mgr.close()

    def test_write_when_disconnected_does_nothing(self):
        mgr = SerialManager()
        mgr.write(b"data")  # should not raise
