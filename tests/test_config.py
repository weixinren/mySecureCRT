import os
import json
import tempfile
import pytest
from config import ConfigManager


class TestConfigManager:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmp_dir, "config.json")
        self.mgr = ConfigManager(self.config_path)

    def teardown_method(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.tmp_dir)

    def test_default_values(self):
        """Config should have sensible defaults when no file exists (V2 schema)."""
        assert self.mgr.get("sessions") == []
        assert self.mgr.get("active_session") == ""
        assert self.mgr.get("window.width") == 900
        assert self.mgr.get("window.height") == 600
        assert self.mgr.get("window.x") == 100
        assert self.mgr.get("window.y") == 100

    def test_set_and_get(self):
        """Setting a value should be retrievable."""
        self.mgr.set("window.width", 1200)
        assert self.mgr.get("window.width") == 1200

    def test_save_and_load(self):
        """Config should persist to disk and reload."""
        self.mgr.set("window.width", 1100)
        self.mgr.save()
        assert os.path.exists(self.config_path)

        mgr2 = ConfigManager(self.config_path)
        mgr2.load()
        assert mgr2.get("window.width") == 1100

    def test_load_missing_file_uses_defaults(self):
        """Loading when file doesn't exist should keep defaults."""
        self.mgr.load()
        assert self.mgr.get("sessions") == []
        assert self.mgr.get("window.width") == 900

    def test_get_all(self):
        """get_all should return entire config dict."""
        data = self.mgr.get_all()
        assert "sessions" in data
        assert "active_session" in data
        assert "window" in data

    def test_v2_sessions_save_and_load(self):
        """V2 config should save and load multiple sessions."""
        sessions = [
            {
                "id": "abc123",
                "name": "COM3",
                "renamed": False,
                "serial": {
                    "port": "COM3",
                    "baudrate": 115200,
                    "databits": 8,
                    "stopbits": 1,
                    "parity": "None",
                    "flowcontrol": "None",
                },
                "display": {"mode": "terminal", "font_size": 14},
            },
            {
                "id": "def456",
                "name": "传感器",
                "renamed": True,
                "serial": {
                    "port": "COM5",
                    "baudrate": 9600,
                    "databits": 8,
                    "stopbits": 1,
                    "parity": "None",
                    "flowcontrol": "None",
                },
                "display": {"mode": "monitor", "font_size": 12},
            },
        ]
        self.mgr.set("sessions", sessions)
        self.mgr.set("active_session", "abc123")
        self.mgr.save()

        mgr2 = ConfigManager(self.config_path)
        mgr2.load()
        loaded = mgr2.get("sessions")
        assert len(loaded) == 2
        assert loaded[0]["id"] == "abc123"
        assert loaded[1]["name"] == "传感器"
        assert mgr2.get("active_session") == "abc123"

    def test_v1_to_v2_migration(self):
        """Loading a V1 config (no 'sessions' key) should auto-migrate to V2."""
        v1_config = {
            "serial": {
                "port": "COM3",
                "baudrate": 115200,
                "databits": 8,
                "stopbits": 1,
                "parity": "None",
                "flowcontrol": "None",
            },
            "display": {"mode": "text"},
            "window": {"width": 900, "height": 600, "x": 100, "y": 100},
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(v1_config, f)

        mgr = ConfigManager(self.config_path)
        mgr.load()

        sessions = mgr.get("sessions")
        assert isinstance(sessions, list)
        assert len(sessions) == 1
        s = sessions[0]
        assert "id" in s
        assert s["serial"]["port"] == "COM3"
        assert s["serial"]["baudrate"] == 115200
        assert s["display"]["mode"] == "text"
        assert s["renamed"] is False
        assert mgr.get("active_session") == s["id"]
        assert mgr.get("window.width") == 900

    def test_v1_migration_empty_serial(self):
        """V1 migration with no port should still produce a valid session."""
        v1_config = {
            "serial": {"port": "", "baudrate": 115200, "databits": 8, "stopbits": 1, "parity": "None", "flowcontrol": "None"},
            "display": {"mode": "terminal"},
            "window": {"width": 900, "height": 600, "x": 100, "y": 100},
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(v1_config, f)

        mgr = ConfigManager(self.config_path)
        mgr.load()

        sessions = mgr.get("sessions")
        assert len(sessions) == 1
        assert sessions[0]["name"] == "新会话"

    def test_v2_default_config_has_sessions(self):
        """Fresh V2 ConfigManager should have an empty sessions list."""
        mgr = ConfigManager(self.config_path)
        sessions = mgr.get("sessions")
        assert isinstance(sessions, list)
        assert len(sessions) == 0

    def test_existing_v1_tests_still_pass_via_get_set(self):
        """V2 ConfigManager must still support dotted get/set for window config."""
        self.mgr.set("window.width", 1200)
        assert self.mgr.get("window.width") == 1200
