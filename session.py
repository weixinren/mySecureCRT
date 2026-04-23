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
        self.terminal.setParent(None)
        self.terminal.deleteLater()
        self.serial_manager.deleteLater()
        self.deleteLater()
