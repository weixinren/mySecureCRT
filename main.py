import sys
import os
import copy
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStatusBar, QLabel, QMessageBox, QFileDialog, QTabWidget,
    QTabBar, QPushButton, QInputDialog, QShortcut,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence

from serial_manager import SerialManager
from settings_panel import SettingsPanel
from config import ConfigManager, new_session_config
from session import Session


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
QTabWidget::pane {
    border: none;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #888888;
    padding: 6px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #ffffff;
    border-bottom: 2px solid #007acc;
}
QTabBar::tab:hover:!selected {
    background-color: #353535;
    color: #cccccc;
}
QTabBar::close-button {
    image: none;
    subcontrol-position: right;
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

        self._sessions = {}          # id → Session
        self._active_session = None  # current Session or None
        self._active_connections = []

        self._init_ui()
        self._setup_shortcuts()
        self._restore_sessions()
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

        # Right area: tab widget
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)

        # "+" button in tab bar corner
        add_btn = QPushButton("＋")
        add_btn.setFixedSize(28, 28)
        add_btn.setToolTip("新建会话 (Ctrl+T)")
        add_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #cccccc; border: none; font-size: 16px; }"
            "QPushButton:hover { color: #ffffff; background-color: #3c3c3c; border-radius: 4px; }"
        )
        add_btn.clicked.connect(self._on_new_tab)
        self.tab_widget.setCornerWidget(add_btn, Qt.TopRightCorner)

        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close)
        self.tab_widget.tabBarDoubleClicked.connect(self._on_tab_double_clicked)

        right_layout.addWidget(self.tab_widget)
        main_layout.addLayout(right_layout, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("🔴 未连接")
        self.params_label = QLabel("")
        self.stats_label = QLabel("↑TX: 0  ↓RX: 0")
        self.log_label = QLabel("")
        self.session_count_label = QLabel("")
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addWidget(self.params_label)
        self.status_bar.addPermanentWidget(self.log_label)
        self.status_bar.addPermanentWidget(self.stats_label)
        self.status_bar.addPermanentWidget(self.session_count_label)

        # Connect settings panel signals (these route to active session)
        self.settings_panel.connect_clicked.connect(self._on_connect)
        self.settings_panel.disconnect_clicked.connect(self._on_disconnect)
        self.settings_panel.refresh_clicked.connect(self._refresh_ports)
        self.settings_panel.display_mode_changed.connect(self._on_display_mode_changed)
        self.settings_panel.font_size_changed.connect(self._on_font_size_changed)
        self.settings_panel.clear_clicked.connect(self._on_clear)
        self.settings_panel.save_log_clicked.connect(self._on_save_log)

        # Restore window geometry
        w = self.config.get("window.width") or 900
        h = self.config.get("window.height") or 600
        x = self.config.get("window.x")
        y = self.config.get("window.y")
        self.resize(w, h)
        if x is not None and y is not None:
            self.move(x, y)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, self._on_new_tab)
        QShortcut(QKeySequence("Ctrl+W"), self, self._on_close_current_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self, self._on_next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._on_prev_tab)

    # ── Session Lifecycle ──

    def _create_session(self, config=None):
        """Create a new Session and add it as a tab. Returns the Session."""
        if config is None:
            config = new_session_config()
        session = Session(config)
        self._sessions[session.id] = session

        # Connect session signals
        session.connection_changed.connect(self._on_session_connection_changed)
        session.error_occurred.connect(self._on_session_error)
        session.name_changed.connect(self._on_session_name_changed)
        session.data_activity.connect(self._on_session_data_activity)
        session.terminal.font_size_changed.connect(self._on_terminal_font_size_changed)

        tab_index = self.tab_widget.addTab(session.terminal, self._tab_label(session))
        self.tab_widget.setCurrentIndex(tab_index)
        self._update_session_count()
        return session

    def _close_session(self, tab_index):
        """Close session at the given tab index."""
        terminal = self.tab_widget.widget(tab_index)
        session = self._session_for_terminal(terminal)
        if session is None:
            return

        session.destroy()
        del self._sessions[session.id]
        self.tab_widget.removeTab(tab_index)

        # Ensure at least one tab exists
        if self.tab_widget.count() == 0:
            self._create_session()

        self._update_session_count()

    def _session_for_terminal(self, terminal):
        """Find the Session that owns a given TerminalWidget."""
        for session in self._sessions.values():
            if session.terminal is terminal:
                return session
        return None

    def _active_session_obj(self):
        """Get the Session for the currently active tab."""
        terminal = self.tab_widget.currentWidget()
        if terminal is None:
            return None
        return self._session_for_terminal(terminal)

    # ── Tab Events ──

    def _on_new_tab(self):
        session = self._create_session()
        session.terminal.setFocus()

    def _on_close_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx >= 0:
            self._on_tab_close(idx)

    def _on_next_tab(self):
        count = self.tab_widget.count()
        if count > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % count)

    def _on_prev_tab(self):
        count = self.tab_widget.count()
        if count > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1) % count)

    def _on_tab_close(self, index):
        self._close_session(index)

    def _on_tab_changed(self, index):
        """Switch sidebar and status bar to the newly active tab."""
        session = self._active_session_obj()
        if session is None:
            return

        self._active_session = session

        # Sync sidebar controls to this session's config
        self.settings_panel.apply_session_config(session.config)
        self.settings_panel.set_connected(session.serial_manager.is_connected)

        # Sync status bar
        self._update_status_bar(session)
        self._update_stats(session)

        session.terminal.setFocus()

    def _on_tab_double_clicked(self, index):
        """Rename a tab via dialog."""
        terminal = self.tab_widget.widget(index)
        session = self._session_for_terminal(terminal)
        if session is None:
            return

        new_name, ok = QInputDialog.getText(
            self, "重命名会话", "会话名称:", text=session.name
        )
        if ok and new_name.strip():
            session.name = new_name.strip()
            session.renamed = True
            self.tab_widget.setTabText(index, self._tab_label(session))

    # ── Session Signal Handlers ──

    def _on_session_connection_changed(self, session, connected):
        # Update tab label
        idx = self.tab_widget.indexOf(session.terminal)
        if idx >= 0:
            self.tab_widget.setTabText(idx, self._tab_label(session))

        # Update sidebar and status bar only if this is the active session
        if session is self._active_session:
            self.settings_panel.set_connected(connected)
            self._update_status_bar(session)

    def _on_session_error(self, session, msg):
        QMessageBox.critical(self, "串口错误", f"[{session.name}] {msg}")

    def _on_session_name_changed(self, session):
        idx = self.tab_widget.indexOf(session.terminal)
        if idx >= 0:
            self.tab_widget.setTabText(idx, self._tab_label(session))

    def _on_session_data_activity(self, session):
        if session is self._active_session:
            self._update_stats(session)

    def _on_terminal_font_size_changed(self, size):
        """Sync font size spinner when terminal font changes (Ctrl+scroll)."""
        session = self._active_session_obj()
        if session and session.terminal.font_size == size:
            self.settings_panel.set_font_size(size)
            session.config["display"]["font_size"] = size

    # ── Settings Panel Actions (route to active session) ──

    def _on_connect(self):
        session = self._active_session
        if session is None:
            return
        settings = self.settings_panel.get_settings()
        if not settings["port"]:
            QMessageBox.warning(self, "提示", "请先选择串口端口")
            return
        # Save settings to session config before connecting
        session.update_config_from_settings(self.settings_panel.get_session_config())
        session.serial_manager.open(
            settings["port"], settings["baudrate"], settings["databits"],
            settings["stopbits"], settings["parity"], settings["flowcontrol"],
        )

    def _on_disconnect(self):
        session = self._active_session
        if session is None:
            return
        session.serial_manager.close()

    def _on_display_mode_changed(self, mode):
        session = self._active_session
        if session is None:
            return
        session.terminal.set_display_mode(mode)
        session.config["display"]["mode"] = mode

    def _on_font_size_changed(self, size):
        session = self._active_session
        if session is None:
            return
        session.terminal.set_font_size(size)
        session.config["display"]["font_size"] = size

    def _on_clear(self):
        session = self._active_session
        if session is None:
            return
        session.terminal.clear_terminal()
        self._update_stats(session)

    def _on_save_log(self):
        session = self._active_session
        if session is None:
            return
        if session.logger.is_active:
            session.logger.stop()
            self.log_label.setText("")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "", "日志文件 (*.log *.txt);;所有文件 (*)"
        )
        if path:
            session.logger.start(path)
            self.log_label.setText("📝 日志记录中")

    def _refresh_ports(self):
        mgr = SerialManager()
        ports = mgr.list_ports()
        self.settings_panel.set_ports(ports)

    # ── UI Helpers ──

    def _tab_label(self, session):
        icon = "🟢" if session.serial_manager.is_connected else "🔴"
        return f"{icon} {session.name}"

    def _update_status_bar(self, session):
        if session.serial_manager.is_connected:
            cfg = session.config["serial"]
            parity_short = "N" if cfg["parity"] == "None" else cfg["parity"][0]
            self.status_label.setText("🟢 已连接")
            self.params_label.setText(
                f"{cfg['port']} | {cfg['baudrate']} {cfg['databits']}{parity_short}{cfg['stopbits']}"
            )
        else:
            self.status_label.setText("🔴 未连接")
            self.params_label.setText("")

    def _update_stats(self, session):
        tx = session.terminal.tx_bytes
        rx = session.terminal.rx_bytes
        self.stats_label.setText(f"↑TX: {tx}  ↓RX: {rx}")

    def _update_session_count(self):
        count = len(self._sessions)
        self.session_count_label.setText(f"{count} 个会话")

    # ── Config Persistence ──

    def _restore_sessions(self):
        """Restore tabs from saved config, or create one default tab."""
        sessions_config = self.config.get("sessions") or []
        active_id = self.config.get("active_session", "")

        if not sessions_config:
            self._create_session()
            return

        active_index = 0
        for i, cfg in enumerate(sessions_config):
            self._create_session(cfg)
            if cfg.get("id") == active_id:
                active_index = i

        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(active_index)

    def _save_config(self):
        """Save all session configs and window geometry."""
        sessions_list = []
        for i in range(self.tab_widget.count()):
            terminal = self.tab_widget.widget(i)
            session = self._session_for_terminal(terminal)
            if session is None:
                continue
            # Sync current sidebar settings to active session
            if session is self._active_session:
                session.update_config_from_settings(
                    self.settings_panel.get_session_config()
                )
            # Sync terminal display state
            session.config["display"]["mode"] = session.terminal.display_mode
            session.config["display"]["font_size"] = session.terminal.font_size
            sessions_list.append(copy.deepcopy(session.config))

        self.config.set("sessions", sessions_list)
        active = self._active_session
        self.config.set("active_session", active.id if active else "")

        geo = self.geometry()
        self.config.set("window.width", geo.width())
        self.config.set("window.height", geo.height())
        self.config.set("window.x", geo.x())
        self.config.set("window.y", geo.y())
        self.config.save()

    def closeEvent(self, event):
        self._save_config()
        for session in list(self._sessions.values()):
            session.destroy()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    window = MainWindow()
    window.show()
    # Focus the active terminal
    active = window._active_session
    if active:
        active.terminal.setFocus()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
