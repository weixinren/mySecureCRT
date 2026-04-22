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
        """Config should have sensible defaults when no file exists."""
        assert self.mgr.get("serial.port") == ""
        assert self.mgr.get("serial.baudrate") == 115200
        assert self.mgr.get("serial.databits") == 8
        assert self.mgr.get("serial.stopbits") == 1
        assert self.mgr.get("serial.parity") == "None"
        assert self.mgr.get("serial.flowcontrol") == "None"
        assert self.mgr.get("display.mode") == "text"
        assert self.mgr.get("window.width") == 900
        assert self.mgr.get("window.height") == 600

    def test_set_and_get(self):
        """Setting a value should be retrievable."""
        self.mgr.set("serial.port", "COM5")
        assert self.mgr.get("serial.port") == "COM5"

    def test_save_and_load(self):
        """Config should persist to disk and reload."""
        self.mgr.set("serial.baudrate", 9600)
        self.mgr.save()
        assert os.path.exists(self.config_path)

        mgr2 = ConfigManager(self.config_path)
        mgr2.load()
        assert mgr2.get("serial.baudrate") == 9600

    def test_load_missing_file_uses_defaults(self):
        """Loading when file doesn't exist should keep defaults."""
        self.mgr.load()
        assert self.mgr.get("serial.baudrate") == 115200

    def test_get_all(self):
        """get_all should return entire config dict."""
        data = self.mgr.get_all()
        assert "serial" in data
        assert "display" in data
        assert "window" in data
