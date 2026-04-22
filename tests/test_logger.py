import os
import tempfile
import pytest
from logger import DataLogger


class TestDataLogger:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False
        )
        self.tmp.close()
        self.log_path = self.tmp.name

    def teardown_method(self):
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def test_start_creates_file(self):
        logger = DataLogger()
        logger.start(self.log_path)
        assert logger.is_active
        logger.stop()

    def test_log_entry_written(self):
        logger = DataLogger()
        logger.start(self.log_path)
        logger.log("RX", b"Hello")
        logger.stop()
        content = open(self.log_path, "r", encoding="utf-8").read()
        assert "RX" in content
        assert "Hello" in content

    def test_log_hex_entry(self):
        logger = DataLogger()
        logger.start(self.log_path)
        logger.log("TX", b"\x41\x42\x43")
        logger.stop()
        content = open(self.log_path, "r", encoding="utf-8").read()
        assert "TX" in content

    def test_stop_closes_file(self):
        logger = DataLogger()
        logger.start(self.log_path)
        logger.stop()
        assert not logger.is_active

    def test_log_when_inactive_does_nothing(self):
        logger = DataLogger()
        logger.log("RX", b"data")  # should not raise
