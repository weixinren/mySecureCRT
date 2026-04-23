import sys
import pytest
from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from quick_send_panel import QuickSendPanel, CommandButton, encode_command_data


class TestEncodeCommandData:
    def test_text_with_newline(self):
        result = encode_command_data("help", "text", append_newline=True)
        assert result == b"help\r\n"

    def test_text_without_newline(self):
        result = encode_command_data("help", "text", append_newline=False)
        assert result == b"help"

    def test_hex(self):
        result = encode_command_data("AA 55 01 FF", "hex")
        assert result == b"\xaa\x55\x01\xff"


class TestCommandButton:
    def _make_command(self, **overrides):
        cmd = {
            "id": "test1", "name": "test", "data": "hello",
            "type": "text", "append_newline": True, "loop_interval_ms": 0,
        }
        cmd.update(overrides)
        return cmd

    def test_encode_text(self):
        btn = CommandButton(self._make_command())
        assert btn.encode_data() == b"hello\r\n"

    def test_encode_hex(self):
        btn = CommandButton(self._make_command(data="AA BB", type="hex"))
        assert btn.encode_data() == b"\xaa\xbb"

    def test_loop_start_stop(self):
        btn = CommandButton(self._make_command())
        assert not btn.is_looping
        btn.start_loop(1000)
        assert btn.is_looping
        assert btn._timer.isActive()
        btn.stop_loop()
        assert not btn.is_looping
        assert not btn._timer.isActive()


class TestQuickSendPanel:
    def _sample_config(self):
        return {
            "collapsed": False,
            "groups": [
                {
                    "id": "g1", "name": "调试命令",
                    "commands": [
                        {"id": "c1", "name": "help", "data": "help", "type": "text",
                         "append_newline": True, "loop_interval_ms": 0},
                        {"id": "c2", "name": "心跳", "data": "AA 55", "type": "hex",
                         "append_newline": False, "loop_interval_ms": 1000},
                    ],
                },
                {
                    "id": "g2", "name": "协议测试",
                    "commands": [
                        {"id": "c3", "name": "ping", "data": "ping", "type": "text",
                         "append_newline": True, "loop_interval_ms": 0},
                    ],
                },
            ],
            "active_group": "g1",
        }

    def test_set_get_config(self):
        panel = QuickSendPanel()
        config = self._sample_config()
        panel.set_config(config)
        result = panel.get_config()
        assert len(result["groups"]) == 2
        assert result["active_group"] == "g1"
        assert result["groups"][0]["name"] == "调试命令"
        assert len(result["groups"][0]["commands"]) == 2

    def test_buttons_created_for_group(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        assert len(panel._buttons) == 2

    def test_switch_group_updates_buttons(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        assert len(panel._buttons) == 2
        panel._group_combo.setCurrentIndex(1)
        assert len(panel._buttons) == 1

    def test_send_text_signal(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        signals = []
        panel.send_requested.connect(lambda data: signals.append(data))
        panel._buttons[0]._on_clicked()
        assert len(signals) == 1
        assert signals[0] == b"help\r\n"

    def test_send_hex_signal(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        signals = []
        panel.send_requested.connect(lambda data: signals.append(data))
        panel._buttons[1]._on_clicked()
        assert len(signals) == 1
        assert signals[0] == b"\xaa\x55"

    def test_stop_all_loops(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        panel._buttons[0].start_loop(1000)
        panel._buttons[1].start_loop(500)
        assert panel._buttons[0].is_looping
        assert panel._buttons[1].is_looping
        panel.stop_all_loops()
        assert not panel._buttons[0].is_looping
        assert not panel._buttons[1].is_looping

    def test_collapse_expand(self):
        panel = QuickSendPanel()
        panel.set_config(self._sample_config())
        assert not panel.is_collapsed
        panel.set_collapsed(True)
        assert panel.is_collapsed
        assert panel.width() == 32
        panel.set_collapsed(False)
        assert not panel.is_collapsed
        assert panel.width() == 180

    def test_empty_group_shows_placeholder(self):
        panel = QuickSendPanel()
        panel.set_config({
            "collapsed": False,
            "groups": [{"id": "g1", "name": "空组", "commands": []}],
            "active_group": "g1",
        })
        assert len(panel._buttons) == 0
