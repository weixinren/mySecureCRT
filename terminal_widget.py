# terminal_widget.py
from datetime import datetime
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QKeyEvent, QWheelEvent
from PyQt5.QtCore import pyqtSignal, Qt


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_mode = "text"
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._font_size = 14
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
        self._display_mode = mode

    def format_line(self, direction, data, mode=None):
        if mode is None:
            mode = self._display_mode
        timestamp = datetime.now().strftime("%H:%M:%S")
        if mode == "hex":
            hex_part = " ".join(f"{b:02X}" for b in data)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
            return f"[{timestamp}] {direction}: {hex_part} | {ascii_part}"
        else:
            text = data.decode("utf-8", errors="replace")
            return f"[{timestamp}] {direction}: {text}"

    def append_data(self, direction, data):
        if direction == "TX":
            self._tx_bytes += len(data)
        else:
            self._rx_bytes += len(data)
        line = self.format_line(direction, data)
        self._append_colored_line(direction, line)

    def _append_colored_line(self, direction, line):
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)

        # Parse the line: [timestamp] DIRECTION: content
        bracket_end = line.index("]") + 1
        timestamp_part = line[:bracket_end]
        rest = line[bracket_end:]

        # Timestamp in gray
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS["timestamp"]))
        cursor.insertText(timestamp_part, fmt)

        # Direction tag + data
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

        # Find the colon after direction
        colon_pos = rest.index(":")
        tag_part = rest[: colon_pos + 1]
        data_part = rest[colon_pos + 1 :]

        cursor.insertText(tag_part, tag_fmt)
        cursor.insertText(data_part + "\n", data_fmt)

        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def clear_terminal(self):
        self.clear()
        self._tx_bytes = 0
        self._rx_bytes = 0

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
        elif text:
            self.key_pressed.emit(text.encode("utf-8"))
