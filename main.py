# main.py
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QLabel, QMessageBox, QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from serial_manager import SerialManager
from terminal_widget import TerminalWidget
from settings_panel import SettingsPanel
from config import ConfigManager
from logger import DataLogger


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
        self.serial_mgr = SerialManager()
        self.data_logger = DataLogger()

        self._init_ui()
        self._connect_signals()
        self._apply_saved_config()
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

        # Right terminal area
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        self.terminal = TerminalWidget()
        right_layout.addWidget(self.terminal)
        main_layout.addLayout(right_layout, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("🔴 未连接")
        self.params_label = QLabel("")
        self.stats_label = QLabel("↑TX: 0  ↓RX: 0")
        self.log_label = QLabel("")
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addWidget(self.params_label)
        self.status_bar.addPermanentWidget(self.log_label)
        self.status_bar.addPermanentWidget(self.stats_label)

        # Restore window geometry
        w = self.config.get("window.width") or 900
        h = self.config.get("window.height") or 600
        x = self.config.get("window.x")
        y = self.config.get("window.y")
        self.resize(w, h)
        if x is not None and y is not None:
            self.move(x, y)

    def _connect_signals(self):
        # Settings panel signals
        self.settings_panel.connect_clicked.connect(self._on_connect)
        self.settings_panel.disconnect_clicked.connect(self._on_disconnect)
        self.settings_panel.refresh_clicked.connect(self._refresh_ports)
        # Display mode and font size
        self.settings_panel.display_mode_changed.connect(self.terminal.set_display_mode)
        self.settings_panel.font_size_changed.connect(self.terminal.set_font_size)
        self.terminal.font_size_changed.connect(self.settings_panel.set_font_size)
        self.settings_panel.clear_clicked.connect(self._on_clear)
        self.settings_panel.save_log_clicked.connect(self._on_save_log)

        # Serial manager signals
        self.serial_mgr.data_received.connect(self._on_data_received)
        self.serial_mgr.connection_changed.connect(self._on_connection_changed)
        self.serial_mgr.error_occurred.connect(self._on_error)

        # Terminal keyboard input
        self.terminal.key_pressed.connect(self._on_key_pressed)

    def _apply_saved_config(self):
        self.settings_panel.apply_config(self.config)
        mode = self.config.get("display.mode") or "terminal"
        if mode == "text":
            mode = "terminal"
        self.terminal.set_display_mode(mode)
        font_size = self.config.get("display.font_size", 14)
        self.terminal.set_font_size(int(font_size))

    def _refresh_ports(self):
        ports = self.serial_mgr.list_ports()
        self.settings_panel.set_ports(ports)

    def _on_connect(self):
        settings = self.settings_panel.get_settings()
        if not settings["port"]:
            QMessageBox.warning(self, "提示", "请先选择串口端口")
            return
        self.serial_mgr.open(
            settings["port"], settings["baudrate"], settings["databits"],
            settings["stopbits"], settings["parity"], settings["flowcontrol"],
        )

    def _on_disconnect(self):
        self.serial_mgr.close()

    def _on_connection_changed(self, connected):
        self.settings_panel.set_connected(connected)
        if connected:
            settings = self.settings_panel.get_settings()
            self.status_label.setText("🟢 已连接")
            p = settings
            self.params_label.setText(
                f"{p['port']} | {p['baudrate']} {p['databits']}"
                f"{'N' if p['parity'] == 'None' else p['parity'][0]}"
                f"{p['stopbits']}"
            )
        else:
            self.status_label.setText("🔴 未连接")
            self.params_label.setText("")

    def _on_data_received(self, data):
        self.terminal.append_data("RX", data)
        if self.data_logger.is_active:
            self.data_logger.log("RX", data)
        self._update_stats()

    def _on_key_pressed(self, data):
        self.serial_mgr.write(data)
        self.terminal.append_data("TX", data)
        if self.data_logger.is_active:
            self.data_logger.log("TX", data)
        self._update_stats()

    def _on_error(self, msg):
        QMessageBox.critical(self, "串口错误", msg)

    def _on_clear(self):
        self.terminal.clear_terminal()
        self._update_stats()

    def _on_save_log(self):
        if self.data_logger.is_active:
            self.data_logger.stop()
            self.log_label.setText("")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "日志文件 (*.log *.txt);;所有文件 (*)"
        )
        if path:
            self.data_logger.start(path)
            self.log_label.setText("📝 日志记录中")

    def _update_stats(self):
        tx = self.terminal.tx_bytes
        rx = self.terminal.rx_bytes
        self.stats_label.setText(f"↑TX: {tx}  ↓RX: {rx}")

    def _save_config(self):
        settings = self.settings_panel.get_settings()
        self.config.set("serial.port", settings["port"])
        self.config.set("serial.baudrate", settings["baudrate"])
        self.config.set("serial.databits", settings["databits"])
        self.config.set("serial.stopbits", settings["stopbits"])
        self.config.set("serial.parity", settings["parity"])
        self.config.set("serial.flowcontrol", settings["flowcontrol"])
        self.config.set("display.mode", self.terminal.display_mode)
        self.config.set("display.font_size", self.terminal.font_size)
        geo = self.geometry()
        self.config.set("window.width", geo.width())
        self.config.set("window.height", geo.height())
        self.config.set("window.x", geo.x())
        self.config.set("window.y", geo.y())
        self.config.save()

    def closeEvent(self, event):
        self._save_config()
        if self.data_logger.is_active:
            self.data_logger.stop()
        self.serial_mgr.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    window = MainWindow()
    window.show()
    # Focus the terminal for keyboard input
    window.terminal.setFocus()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
