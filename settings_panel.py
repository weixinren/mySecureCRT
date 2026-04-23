# settings_panel.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout,
    QSpinBox,
)
from PyQt5.QtCore import pyqtSignal, Qt


class SettingsPanel(QWidget):
    connect_clicked = pyqtSignal()
    disconnect_clicked = pyqtSignal()
    refresh_clicked = pyqtSignal()
    display_mode_changed = pyqtSignal(str)
    font_size_changed = pyqtSignal(int)
    clear_clicked = pyqtSignal()
    save_log_clicked = pyqtSignal()

    BAUDRATES = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]
    DATABITS = ["5", "6", "7", "8"]
    STOPBITS = ["1", "1.5", "2"]
    PARITIES = ["None", "Even", "Odd", "Mark", "Space"]
    FLOWCONTROLS = ["None", "RTS/CTS", "XON/XOFF"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self._connected = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Section: Serial Settings
        layout.addWidget(self._make_section_label("串口设置"))

        self.port_combo = self._add_combo(layout, "端口 Port", [])
        self.baud_combo = self._add_combo(layout, "波特率 Baud Rate", self.BAUDRATES)
        self.baud_combo.setCurrentText("115200")
        self.databits_combo = self._add_combo(layout, "数据位 Data Bits", self.DATABITS)
        self.databits_combo.setCurrentText("8")
        self.stopbits_combo = self._add_combo(layout, "停止位 Stop Bits", self.STOPBITS)
        self.stopbits_combo.setCurrentText("1")
        self.parity_combo = self._add_combo(layout, "校验位 Parity", self.PARITIES)
        self.flow_combo = self._add_combo(layout, "流控 Flow Control", self.FLOWCONTROLS)

        # Connect button
        self.connect_btn = QPushButton("🔗 连接")
        self.connect_btn.setObjectName("connectBtn")
        self.connect_btn.setMinimumHeight(32)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)

        # Separator
        layout.addWidget(self._make_separator())

        # Section: Display Settings
        layout.addWidget(self._make_section_label("显示设置"))

        mode_row = QHBoxLayout()
        self.terminal_btn = QPushButton("终端")
        self.terminal_btn.setCheckable(True)
        self.terminal_btn.setChecked(True)
        self.terminal_btn.clicked.connect(lambda: self._set_mode("terminal"))
        self.monitor_btn = QPushButton("监控")
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.clicked.connect(lambda: self._set_mode("monitor"))
        self.hex_btn = QPushButton("HEX")
        self.hex_btn.setCheckable(True)
        self.hex_btn.clicked.connect(lambda: self._set_mode("hex"))
        mode_row.addWidget(self.terminal_btn)
        mode_row.addWidget(self.monitor_btn)
        mode_row.addWidget(self.hex_btn)
        layout.addLayout(mode_row)

        # Font size control
        font_row = QHBoxLayout()
        font_lbl = QLabel("字号")
        font_lbl.setStyleSheet("color: #888888; font-size: 13px;")
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 48)
        self.font_spin.setValue(14)
        self.font_spin.setSuffix(" pt")
        self.font_spin.valueChanged.connect(self.font_size_changed.emit)
        font_row.addWidget(font_lbl)
        font_row.addWidget(self.font_spin)
        layout.addLayout(font_row)

        action_row = QHBoxLayout()
        self.clear_btn = QPushButton("清屏")
        self.clear_btn.clicked.connect(self.clear_clicked.emit)
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_log_clicked.emit)
        action_row.addWidget(self.clear_btn)
        action_row.addWidget(self.save_btn)
        layout.addLayout(action_row)

        # Separator
        layout.addWidget(self._make_separator())

        # Refresh
        self.refresh_btn = QPushButton("🔄 刷新端口")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()

    def _make_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #4ec9b0; font-size: 14px; font-weight: bold;"
            "text-transform: uppercase; letter-spacing: 1px;"
        )
        return lbl

    def _make_separator(self):
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #444444;")
        return sep

    def _add_combo(self, layout, label_text, items):
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(lbl)
        combo = QComboBox()
        combo.addItems(items)
        layout.addWidget(combo)
        return combo

    def _on_connect_clicked(self):
        if self._connected:
            self.disconnect_clicked.emit()
        else:
            self.connect_clicked.emit()

    def _set_mode(self, mode):
        self.terminal_btn.setChecked(mode == "terminal")
        self.monitor_btn.setChecked(mode == "monitor")
        self.hex_btn.setChecked(mode == "hex")
        self.display_mode_changed.emit(mode)

    def set_font_size(self, size):
        self.font_spin.blockSignals(True)
        self.font_spin.setValue(size)
        self.font_spin.blockSignals(False)

    def set_connected(self, connected):
        self._connected = connected
        if connected:
            self.connect_btn.setText("🔌 断开")
            self.connect_btn.setStyleSheet(
                "background-color: #a1260d; color: white; font-weight: bold;"
                "border: none; border-radius: 4px;"
            )
        else:
            self.connect_btn.setText("🔗 连接")
            self.connect_btn.setStyleSheet(
                "background-color: #0e639c; color: white; font-weight: bold;"
                "border: none; border-radius: 4px;"
            )

    def set_ports(self, ports):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)

    def get_settings(self):
        stopbits = self.stopbits_combo.currentText()
        try:
            stopbits = float(stopbits)
            if stopbits == int(stopbits):
                stopbits = int(stopbits)
        except ValueError:
            stopbits = 1
        return {
            "port": self.port_combo.currentText(),
            "baudrate": int(self.baud_combo.currentText()),
            "databits": int(self.databits_combo.currentText()),
            "stopbits": stopbits,
            "parity": self.parity_combo.currentText(),
            "flowcontrol": self.flow_combo.currentText(),
        }

    def apply_config(self, config):
        if config.get("serial.port"):
            idx = self.port_combo.findText(config.get("serial.port"))
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        self.baud_combo.setCurrentText(str(config.get("serial.baudrate", 115200)))
        self.databits_combo.setCurrentText(str(config.get("serial.databits", 8)))
        stopbits = config.get("serial.stopbits", 1)
        self.stopbits_combo.setCurrentText(str(stopbits))
        self.parity_combo.setCurrentText(config.get("serial.parity", "None"))
        self.flow_combo.setCurrentText(config.get("serial.flowcontrol", "None"))

        mode = config.get("display.mode", "terminal")
        if mode == "text":
            mode = "terminal"
        self._set_mode(mode)

        font_size = config.get("display.font_size", 14)
        self.font_spin.setValue(int(font_size))

    def apply_session_config(self, config):
        """Load a Session's config dict into all sidebar controls.

        Args:
            config: dict with 'serial' and 'display' sub-dicts.
        """
        serial = config.get("serial", {})
        display = config.get("display", {})

        # Block signals to avoid triggering side effects during bulk update
        self.blockSignals(True)

        idx = self.port_combo.findText(serial.get("port", ""))
        if idx >= 0:
            self.port_combo.setCurrentIndex(idx)
        self.baud_combo.setCurrentText(str(serial.get("baudrate", 115200)))
        self.databits_combo.setCurrentText(str(serial.get("databits", 8)))
        self.stopbits_combo.setCurrentText(str(serial.get("stopbits", 1)))
        self.parity_combo.setCurrentText(serial.get("parity", "None"))
        self.flow_combo.setCurrentText(serial.get("flowcontrol", "None"))

        mode = display.get("mode", "terminal")
        if mode == "text":
            mode = "terminal"
        self._set_mode(mode)

        self.font_spin.blockSignals(True)
        self.font_spin.setValue(int(display.get("font_size", 14)))
        self.font_spin.blockSignals(False)

        self.blockSignals(False)

    def get_session_config(self):
        """Export current sidebar controls as a session config snippet.

        Returns:
            dict with keys: port, baudrate, databits, stopbits, parity,
            flowcontrol, display_mode, font_size.
        """
        settings = self.get_settings()
        if self.terminal_btn.isChecked():
            settings["display_mode"] = "terminal"
        elif self.monitor_btn.isChecked():
            settings["display_mode"] = "monitor"
        else:
            settings["display_mode"] = "hex"
        settings["font_size"] = self.font_spin.value()
        return settings
