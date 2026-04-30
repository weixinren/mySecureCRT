# terminal_widget.py
import re
from datetime import datetime

import pyte
from PyQt5.QtWidgets import (
    QPlainTextEdit, QTextEdit, QWidget, QHBoxLayout, QLineEdit,
    QPushButton, QLabel,
)
from PyQt5.QtGui import (
    QFont, QTextCharFormat, QColor, QKeyEvent, QWheelEvent, QTextCursor,
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer

_ANSI_CSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

# Display modes
MODE_TERMINAL = "terminal"  # VT100 emulation with cursor
MODE_MONITOR = "monitor"    # Timestamped lines (log view)
MODE_HEX = "hex"            # Hex dump

# Find bar highlight colors
_HIGHLIGHT_ALL = QColor(255, 255, 0, 80)       # yellow, semi-transparent
_HIGHLIGHT_CURRENT = QColor(255, 165, 0, 160)  # orange, more opaque


class FindBar(QWidget):
    """Floating search bar overlaid on terminal widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            "FindBar {"
            "  background-color: #2d2d30;"
            "  border: 1px solid #555555;"
            "  border-radius: 4px;"
            "}"
        )
        self._init_ui()
        self.hide()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("查找...")
        self.search_input.setMinimumWidth(180)
        self.search_input.setStyleSheet(
            "QLineEdit {"
            "  background-color: #3c3c3c;"
            "  color: #cccccc;"
            "  border: 1px solid #555555;"
            "  border-radius: 3px;"
            "  padding: 2px 6px;"
            "}"
        )
        layout.addWidget(self.search_input)

        self.match_label = QLabel("")
        self.match_label.setStyleSheet("color: #999999; font-size: 11px;")
        self.match_label.setMinimumWidth(50)
        layout.addWidget(self.match_label)

        btn_style = (
            "QPushButton {"
            "  background-color: transparent;"
            "  color: #cccccc;"
            "  border: 1px solid #555555;"
            "  border-radius: 3px;"
            "  padding: 2px 6px;"
            "  font-size: 12px;"
            "}"
            "QPushButton:hover { background-color: #3c3c3c; }"
            "QPushButton:checked { background-color: #094771; border-color: #094771; }"
        )

        self.case_btn = QPushButton("Aa")
        self.case_btn.setCheckable(True)
        self.case_btn.setToolTip("区分大小写")
        self.case_btn.setFixedSize(28, 24)
        self.case_btn.setStyleSheet(btn_style)
        layout.addWidget(self.case_btn)

        self.prev_btn = QPushButton("↑")
        self.prev_btn.setToolTip("上一个 (Shift+Enter)")
        self.prev_btn.setFixedSize(24, 24)
        self.prev_btn.setStyleSheet(btn_style)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("↓")
        self.next_btn.setToolTip("下一个 (Enter)")
        self.next_btn.setFixedSize(24, 24)
        self.next_btn.setStyleSheet(btn_style)
        layout.addWidget(self.next_btn)

        self.close_btn = QPushButton("×")
        self.close_btn.setToolTip("关闭 (Esc)")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet(btn_style)
        layout.addWidget(self.close_btn)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.hide()
            if self.parent():
                self.parent().setFocus()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                self.prev_btn.click()
            else:
                self.next_btn.click()
        else:
            super().keyPressEvent(event)


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
        "log_info": "#569cd6",     # <I> normal blue
        "log_warn": "#dcdcaa",     # <W> yellow
        "log_error": "#f44747",    # <E> red
        "default": "#cccccc",
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

        # Find bar
        self._find_bar = FindBar(self)
        self._find_matches = []  # list of QTextCursor for each match
        self._find_current = -1  # index into _find_matches
        self._find_bar.search_input.textChanged.connect(self._on_find_text_changed)
        self._find_bar.case_btn.toggled.connect(lambda: self._on_find_text_changed(self._find_bar.search_input.text()))
        self._find_bar.next_btn.clicked.connect(self._find_next)
        self._find_bar.prev_btn.clicked.connect(self._find_prev)
        self._find_bar.close_btn.clicked.connect(self._close_find_bar)

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

    def _log_level_color(self, text):
        if "<E>" in text:
            return self.COLORS["log_error"]
        if "<W>" in text:
            return self.COLORS["log_warn"]
        if "<I>" in text:
            return self.COLORS["log_info"]
        return self.COLORS["default"]

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
            # Only feed RX to VT screen; MCU echo handles TX display
            if direction == "RX":
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

        # Render with per-line log level colors
        self.setReadOnly(False)
        self.clear()
        cursor = self.textCursor()
        for i, line in enumerate(lines):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(self._log_level_color(line)))
            cursor.insertText(line, fmt)
            if i < len(lines) - 1:
                cursor.insertText("\n", fmt)
        self.setReadOnly(True)

        # Position cursor
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
            log_color = self._log_level_color(line)
            tag_fmt = QTextCharFormat()
            tag_fmt.setForeground(QColor(self.COLORS["rx_tag"]))
            data_fmt = QTextCharFormat()
            data_fmt.setForeground(QColor(log_color))

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
        # Ctrl+F opens find bar
        if key == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self._open_find_bar()
            return
        # Escape closes find bar if visible
        if key == Qt.Key_Escape and self._find_bar.isVisible():
            self._close_find_bar()
            return
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

    # ── Find Bar ──

    def _open_find_bar(self):
        self._find_bar.show()
        self._position_find_bar()
        self._find_bar.search_input.setFocus()
        self._find_bar.search_input.selectAll()

    def _close_find_bar(self):
        self._find_bar.hide()
        self._clear_find_highlights()
        self.setFocus()

    def _position_find_bar(self):
        bar_width = min(360, self.width() - 20)
        self._find_bar.setFixedWidth(bar_width)
        x = self.width() - bar_width - 10
        self._find_bar.move(x, 8)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._find_bar.isVisible():
            self._position_find_bar()

    def _on_find_text_changed(self, text):
        self._find_matches.clear()
        self._find_current = -1

        if not text:
            self._clear_find_highlights()
            self._find_bar.match_label.setText("")
            return

        from PyQt5.QtGui import QTextDocument
        case_sensitive = self._find_bar.case_btn.isChecked()
        flags = QTextDocument.FindCaseSensitively if case_sensitive else QTextDocument.FindFlags(0)

        doc = self.document()
        cursor = doc.find(text, 0, flags)
        while not cursor.isNull():
            self._find_matches.append(QTextCursor(cursor))
            cursor = doc.find(text, cursor, flags)

        if self._find_matches:
            self._find_current = 0
            self._apply_find_highlights()
            self._update_find_label()
        else:
            self._clear_find_highlights()
            self._find_bar.match_label.setText("无匹配")

    def _find_next(self):
        if not self._find_matches:
            return
        self._find_current = (self._find_current + 1) % len(self._find_matches)
        self._apply_find_highlights()
        self._update_find_label()

    def _find_prev(self):
        if not self._find_matches:
            return
        self._find_current = (self._find_current - 1) % len(self._find_matches)
        self._apply_find_highlights()
        self._update_find_label()

    def _apply_find_highlights(self):
        selections = []
        for i, cursor in enumerate(self._find_matches):
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            fmt = QTextCharFormat()
            if i == self._find_current:
                fmt.setBackground(_HIGHLIGHT_CURRENT)
            else:
                fmt.setBackground(_HIGHLIGHT_ALL)
            sel.format = fmt
            selections.append(sel)
        self.setExtraSelections(selections)
        # Scroll to current match
        if 0 <= self._find_current < len(self._find_matches):
            self.setTextCursor(self._find_matches[self._find_current])
            self.ensureCursorVisible()

    def _clear_find_highlights(self):
        self.setExtraSelections([])
        self._find_matches.clear()
        self._find_current = -1

    def _update_find_label(self):
        total = len(self._find_matches)
        current = self._find_current + 1
        self._find_bar.match_label.setText(f"{current}/{total}")
