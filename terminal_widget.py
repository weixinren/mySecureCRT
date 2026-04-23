# terminal_widget.py
import re
from datetime import datetime

import pyte
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QKeyEvent, QWheelEvent
from PyQt5.QtCore import pyqtSignal, Qt, QTimer

_ANSI_CSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

# Display modes
MODE_TERMINAL = "terminal"  # VT100 emulation with cursor
MODE_MONITOR = "monitor"    # Timestamped lines (log view)
MODE_HEX = "hex"            # Hex dump


class TerminalWidget(QPlainTextEdit):
    key_pressed = pyqtSignal(bytes)
    font_size_changed = pyqtSignal(int)

    MIN_FONT_SIZE = 8
    MAX_FONT_SIZE = 48

    COLORS = {
        "timestamp": "#666666",
        "rx_tag": "#6a9955",
        "rx_data": "#569cd6",
        "tx_tag": "#ce9178",
        "tx_data": "#ce9178",
    }

    VT_COLS = 120
    VT_ROWS = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = MODE_TERMINAL
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._font_size = 14

        # Monitor mode: line buffer
        self._rx_buffer = b""
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self._flush_rx_buffer)

        # Terminal mode: pyte VT100 screen
        self._vt_screen = pyte.Screen(self.VT_COLS, self.VT_ROWS)
        # LNM: Line Feed also does Carriage Return (MCU sends \n only)
        self._vt_screen.set_mode(pyte.modes.LNM)
        self._vt_stream = pyte.Stream(self._vt_screen)
        self._vt_refresh_timer = QTimer(self)
        self._vt_refresh_timer.setSingleShot(True)
        self._vt_refresh_timer.setInterval(30)
        self._vt_refresh_timer.timeout.connect(self._render_vt_screen)

        self.setReadOnly(True)
        self._apply_font_style()
        self.setMaximumBlockCount(10000)

    def _apply_font_style(self):
        self.setStyleSheet(
            "QPlainTextEdit {"
            f"  font-family: Consolas, 'Courier New', monospace;"
            f"  font-size: {self._font_size}pt;"
            "  background-color: #1e1e1e;"
            "  color: #cccccc;"
            "  border: none;"
            "  selection-background-color: #264f78;"
            "}"
        )

    @property
    def display_mode(self):
        return self._display_mode

    @property
    def tx_bytes(self):
        return self._tx_bytes

    @property
    def rx_bytes(self):
        return self._rx_bytes

    def set_display_mode(self, mode):
        if mode == self._display_mode:
            return
        self._flush_rx_buffer()
        self._display_mode = mode
        if mode == MODE_TERMINAL:
            self._reset_vt()
            self.clear()

    # ── Monitor / HEX helpers ──

    def _format_monitor_line(self, direction, data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = data.decode("latin-1")
        text = _ANSI_CSI.sub('', text)
        text = ''.join(
            c for c in text
            if c == '\t' or (c >= ' ' and c != '\x7f')
        )
        return f"[{timestamp}] {direction}: {text}"

    def _format_hex_line(self, direction, data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        hex_part = " ".join(f"{b:02X}" for b in data)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
        return f"[{timestamp}] {direction}: {hex_part} | {ascii_part}"

    # ── Data entry point ──

    def append_data(self, direction, data):
        if direction == "RX":
            self._rx_bytes += len(data)
        else:
            self._tx_bytes += len(data)

        if self._display_mode == MODE_TERMINAL:
            self._feed_vt(data)
        elif self._display_mode == MODE_HEX:
            line = self._format_hex_line(direction, data)
            self._append_colored_line(direction, line)
        else:
            # Monitor mode: buffer RX, show TX immediately
            if direction == "RX":
                self._rx_buffer += data
                self._process_rx_buffer()
            else:
                line = self._format_monitor_line("TX", data)
                self._append_colored_line("TX", line)

    # ── Terminal (VT100) mode ──

    def _feed_vt(self, data):
        text = data.decode("latin-1")
        self._vt_stream.feed(text)
        self._vt_refresh_timer.start()

    def _render_vt_screen(self):
        lines = []
        for row in range(self._vt_screen.lines):
            line_chars = []
            for col in range(self._vt_screen.columns):
                char = self._vt_screen.buffer[row][col]
                line_chars.append(char.data if char.data else " ")
            lines.append("".join(line_chars).rstrip())

        # Trim trailing empty lines
        while lines and not lines[-1]:
            lines.pop()

        cursor_row = self._vt_screen.cursor.y
        cursor_col = self._vt_screen.cursor.x

        self.setReadOnly(False)
        self.setPlainText("\n".join(lines))
        self.setReadOnly(True)

        # Position cursor
        cursor = self.textCursor()
        cursor.movePosition(cursor.Start)
        for _ in range(cursor_row):
            cursor.movePosition(cursor.Down)
        for _ in range(cursor_col):
            cursor.movePosition(cursor.Right)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    # ── Monitor mode line buffering ──

    def _process_rx_buffer(self):
        while b"\n" in self._rx_buffer:
            idx = self._rx_buffer.index(b"\n")
            chunk = self._rx_buffer[: idx + 1]
            self._rx_buffer = self._rx_buffer[idx + 1 :]
            line = self._format_monitor_line("RX", chunk)
            self._append_colored_line("RX", line)
        if self._rx_buffer:
            self._flush_timer.start()

    def _flush_rx_buffer(self):
        if self._rx_buffer:
            line = self._format_monitor_line("RX", self._rx_buffer)
            self._append_colored_line("RX", line)
            self._rx_buffer = b""

    def _append_colored_line(self, direction, line):
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)

        bracket_end = line.index("]") + 1
        timestamp_part = line[:bracket_end]
        rest = line[bracket_end:]

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS["timestamp"]))
        cursor.insertText(timestamp_part, fmt)

        if direction == "TX":
            tag_fmt = QTextCharFormat()
            tag_fmt.setForeground(QColor(self.COLORS["tx_tag"]))
            data_fmt = QTextCharFormat()
            data_fmt.setForeground(QColor(self.COLORS["tx_data"]))
        else:
            tag_fmt = QTextCharFormat()
            tag_fmt.setForeground(QColor(self.COLORS["rx_tag"]))
            data_fmt = QTextCharFormat()
            data_fmt.setForeground(QColor(self.COLORS["rx_data"]))

        colon_pos = rest.index(":")
        tag_part = rest[: colon_pos + 1]
        data_part = rest[colon_pos + 1 :]

        cursor.insertText(tag_part, tag_fmt)
        cursor.insertText(data_part + "\n", data_fmt)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    # ── Common ──

    def _reset_vt(self):
        self._vt_screen.reset()
        self._vt_screen.set_mode(pyte.modes.LNM)

    def clear_terminal(self):
        self.clear()
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._rx_buffer = b""
        self._reset_vt()

    def set_font_size(self, size):
        size = max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, size))
        if size != self._font_size:
            self._font_size = size
            self._apply_font_style()
            self.font_size_changed.emit(self._font_size)

    @property
    def font_size(self):
        return self._font_size

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_font_size(self._font_size + 1)
            elif delta < 0:
                self.set_font_size(self._font_size - 1)
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.key_pressed.emit(b"\r\n")
        elif key == Qt.Key_Backspace:
            self.key_pressed.emit(b"\x08")
        elif key == Qt.Key_Tab:
            self.key_pressed.emit(b"\t")
        elif key == Qt.Key_Escape:
            self.key_pressed.emit(b"\x1b")
        elif key == Qt.Key_Up:
            self.key_pressed.emit(b"\x1b[A")
        elif key == Qt.Key_Down:
            self.key_pressed.emit(b"\x1b[B")
        elif key == Qt.Key_Right:
            self.key_pressed.emit(b"\x1b[C")
        elif key == Qt.Key_Left:
            self.key_pressed.emit(b"\x1b[D")
        elif key == Qt.Key_Home:
            self.key_pressed.emit(b"\x1b[H")
        elif key == Qt.Key_End:
            self.key_pressed.emit(b"\x1b[F")
        elif key == Qt.Key_Delete:
            self.key_pressed.emit(b"\x1b[3~")
        elif text:
            self.key_pressed.emit(text.encode("utf-8"))
