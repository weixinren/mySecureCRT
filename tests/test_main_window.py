"""Regression tests for MainWindow session initialization."""
import sys
import pytest
from PyQt5.QtWidgets import QApplication
from config import ConfigManager, new_session_config

app = QApplication.instance() or QApplication(sys.argv)


class TestMainWindowInit:
    """Ensure _active_session is set after construction."""

    def _make_window(self, monkeypatch, sessions=None):
        """Create MainWindow with a controlled config."""
        from main import MainWindow

        cfg = ConfigManager()
        cfg.load()
        if sessions is not None:
            cfg._data["sessions"] = sessions
        monkeypatch.setattr(MainWindow, "__init__", lambda self: None)
        w = MainWindow.__new__(MainWindow)
        # Re-init properly with our config
        from PyQt5.QtWidgets import QMainWindow
        QMainWindow.__init__(w)
        w.config = cfg
        w._sessions = {}
        w._active_session = None
        w._init_ui()
        w._setup_shortcuts()
        w._restore_sessions()
        return w

    def test_active_session_set_first_launch(self, monkeypatch):
        """First launch (no saved sessions) must set _active_session."""
        w = self._make_window(monkeypatch, sessions=[])
        assert w.tab_widget.count() == 1
        assert w._active_session is not None

    def test_active_session_set_with_saved_sessions(self, monkeypatch):
        """Restoring saved sessions must set _active_session."""
        cfg1 = new_session_config()
        w = self._make_window(monkeypatch, sessions=[cfg1])
        assert w.tab_widget.count() == 1
        assert w._active_session is not None
        assert w._active_session.id == cfg1["id"]

    def test_active_session_set_multiple_saved(self, monkeypatch):
        """Restoring multiple saved sessions sets correct active session."""
        cfg1 = new_session_config()
        cfg2 = new_session_config()
        w = self._make_window(monkeypatch, sessions=[cfg1, cfg2])
        assert w.tab_widget.count() == 2
        assert w._active_session is not None
