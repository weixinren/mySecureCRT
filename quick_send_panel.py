import uuid
import copy
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QMenu, QInputDialog, QMessageBox,
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer

from quick_send_dialog import CommandDialog, LoopDialog


def encode_command_data(data, cmd_type, append_newline=True):
    """Encode command data string to bytes."""
    if cmd_type == "hex":
        return bytes.fromhex(data.replace(" ", ""))
    encoded = data.encode("utf-8")
    if append_newline:
        encoded += b"\r\n"
    return encoded


class CommandButton(QPushButton):
    """A button representing a single quick-send command."""

    send_clicked = pyqtSignal(bytes)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    copy_requested = pyqtSignal(str)
    loop_requested = pyqtSignal(str)

    def __init__(self, command, parent=None):
        super().__init__(parent)
        self._command = command
        self._looping = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_loop_tick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.clicked.connect(self._on_clicked)
        self._update_display()

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, cmd):
        self._command = cmd
        self._update_display()

    @property
    def is_looping(self):
        return self._looping

    def encode_data(self):
        return encode_command_data(
            self._command["data"],
            self._command["type"],
            self._command.get("append_newline", True),
        )

    def start_loop(self, interval_ms):
        self._command["loop_interval_ms"] = interval_ms
        self._looping = True
        self._timer.start(interval_ms)
        self._update_display()

    def stop_loop(self):
        self._looping = False
        self._timer.stop()
        self._update_display()

    def _on_clicked(self):
        if self._looping:
            self.stop_loop()
            return
        try:
            data = self.encode_data()
            self.send_clicked.emit(data)
        except (ValueError, Exception):
            pass

    def _on_loop_tick(self):
        try:
            data = self.encode_data()
            self.send_clicked.emit(data)
        except (ValueError, Exception):
            self.stop_loop()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        edit_action = menu.addAction("✏️ 编辑命令...")
        copy_action = menu.addAction("📋 复制命令")
        menu.addSeparator()
        if self._looping:
            loop_action = menu.addAction("⏹ 停止循环发送")
        else:
            loop_action = menu.addAction("🔁 设置循环发送...")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 删除")

        action = menu.exec_(self.mapToGlobal(pos))
        if action == edit_action:
            self.edit_requested.emit(self._command["id"])
        elif action == copy_action:
            self.copy_requested.emit(self._command["id"])
        elif action == loop_action:
            self.loop_requested.emit(self._command["id"])
        elif action == delete_action:
            self.delete_requested.emit(self._command["id"])

    def _update_display(self):
        cmd = self._command
        if self._looping:
            prefix = "🔁"
        elif cmd["type"] == "hex":
            prefix = "🔢"
        else:
            prefix = "📝"
        name = cmd["name"]
        if len(name) > 14:
            name = name[:12] + "…"
        self.setText(f"{prefix} {name}")

        if self._looping:
            self.setStyleSheet(
                "QPushButton { background-color: #0d4f3c; color: #4ec9b0; "
                "border: 1px solid #4ec9b0; border-radius: 4px; padding: 6px 8px; "
                "text-align: left; font-size: 12px; min-height: 20px; }"
            )
        else:
            self.setStyleSheet(
                "QPushButton { background-color: #3c3c3c; color: #cccccc; "
                "border: 1px solid #555555; border-radius: 4px; padding: 6px 8px; "
                "text-align: left; font-size: 12px; min-height: 20px; }"
                "QPushButton:hover { background-color: #4c4c4c; }"
            )


class QuickSendPanel(QWidget):
    """Right-side panel for quick-send command buttons."""

    send_requested = pyqtSignal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups = []
        self._active_group_id = ""
        self._collapsed = False
        self._buttons = []
        self._init_ui()

    def _init_ui(self):
        self.setFixedWidth(180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(32)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 4, 4)
        self._title_label = QLabel("⚡ 快捷发送")
        self._title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self._collapse_btn = QPushButton("◀")
        self._collapse_btn.setFixedSize(22, 22)
        self._collapse_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #888; font-size: 12px; }"
            "QPushButton:hover { color: #fff; }"
        )
        self._collapse_btn.clicked.connect(self._on_collapse_toggle)
        header_layout.addWidget(self._title_label, 1)
        header_layout.addWidget(self._collapse_btn)
        layout.addWidget(header)

        # Content (hidden when collapsed)
        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(6, 4, 6, 6)
        content_layout.setSpacing(4)

        # Group selector row
        group_row = QHBoxLayout()
        group_row.setSpacing(2)
        self._group_combo = QComboBox()
        self._group_combo.setStyleSheet("font-size: 11px;")
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        self._add_group_btn = QPushButton("＋")
        self._add_group_btn.setFixedSize(24, 24)
        self._add_group_btn.setToolTip("新建命令组")
        self._add_group_btn.clicked.connect(self._on_add_group)
        self._del_group_btn = QPushButton("🗑")
        self._del_group_btn.setFixedSize(24, 24)
        self._del_group_btn.setToolTip("删除当前命令组")
        self._del_group_btn.clicked.connect(self._on_delete_group)
        group_row.addWidget(self._group_combo, 1)
        group_row.addWidget(self._add_group_btn)
        group_row.addWidget(self._del_group_btn)
        content_layout.addLayout(group_row)

        # Scroll area for command buttons
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._btn_container = QWidget()
        self._btn_container.setStyleSheet("background: transparent;")
        self._btn_layout = QVBoxLayout(self._btn_container)
        self._btn_layout.setContentsMargins(0, 0, 0, 0)
        self._btn_layout.setSpacing(3)
        self._btn_layout.addStretch()
        self._scroll.setWidget(self._btn_container)
        content_layout.addWidget(self._scroll, 1)

        # Placeholder
        self._placeholder = QLabel("点击下方按钮\n添加命令")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #666; font-size: 11px; padding: 20px;")

        # Add command button
        self._add_cmd_btn = QPushButton("＋ 添加命令")
        self._add_cmd_btn.setStyleSheet(
            "QPushButton { background-color: #0e639c; color: #fff; border: none; "
            "border-radius: 3px; padding: 6px; font-size: 11px; }"
            "QPushButton:hover { background-color: #1177bb; }"
        )
        self._add_cmd_btn.clicked.connect(self._on_add_command)
        content_layout.addWidget(self._add_cmd_btn)

        layout.addWidget(self._content, 1)

    # ── Public API ──

    def set_config(self, config):
        """Load quick_send config dict."""
        self._groups = copy.deepcopy(config.get("groups", []))
        self._active_group_id = config.get("active_group", "")
        self._collapsed = config.get("collapsed", False)

        if not self._groups:
            self._groups = [{"id": "default", "name": "默认命令组", "commands": []}]
            self._active_group_id = "default"

        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        for g in self._groups:
            self._group_combo.addItem(g["name"], g["id"])
        idx = next((i for i, g in enumerate(self._groups)
                     if g["id"] == self._active_group_id), 0)
        self._group_combo.setCurrentIndex(idx)
        self._group_combo.blockSignals(False)

        self._rebuild_buttons()
        self.set_collapsed(self._collapsed)

    def get_config(self):
        """Export quick_send config dict."""
        return {
            "collapsed": self._collapsed,
            "groups": copy.deepcopy(self._groups),
            "active_group": self._active_group_id,
        }

    def stop_all_loops(self):
        """Stop all active loop timers."""
        for btn in self._buttons:
            if btn.is_looping:
                btn.stop_loop()

    @property
    def is_collapsed(self):
        return self._collapsed

    def set_collapsed(self, collapsed):
        self._collapsed = collapsed
        if collapsed:
            self._content.hide()
            self._title_label.hide()
            self._collapse_btn.setText("▶")
            self.setFixedWidth(32)
        else:
            self._content.show()
            self._title_label.show()
            self._collapse_btn.setText("◀")
            self.setFixedWidth(180)

    # ── Internal ──

    def _current_group(self):
        for g in self._groups:
            if g["id"] == self._active_group_id:
                return g
        return self._groups[0] if self._groups else None

    def _rebuild_buttons(self):
        for btn in self._buttons:
            btn.stop_loop()
            btn.deleteLater()
        self._buttons.clear()

        # Clear layout
        while self._btn_layout.count() > 0:
            item = self._btn_layout.takeAt(0)
            w = item.widget()
            if w and w is not self._placeholder:
                w.deleteLater()

        if self._placeholder.parent():
            self._placeholder.setParent(None)

        group = self._current_group()
        if group is None or not group["commands"]:
            self._btn_layout.addWidget(self._placeholder)
            self._btn_layout.addStretch()
            return

        for cmd in group["commands"]:
            btn = CommandButton(cmd)
            btn.send_clicked.connect(self.send_requested.emit)
            btn.edit_requested.connect(self._on_edit_command)
            btn.delete_requested.connect(self._on_delete_command)
            btn.copy_requested.connect(self._on_copy_command)
            btn.loop_requested.connect(self._on_loop_command)
            self._btn_layout.addWidget(btn)
            self._buttons.append(btn)
        self._btn_layout.addStretch()

    def _on_collapse_toggle(self):
        self.set_collapsed(not self._collapsed)

    def _on_group_changed(self, index):
        if 0 <= index < len(self._groups):
            self._active_group_id = self._groups[index]["id"]
            self._rebuild_buttons()

    def _on_add_group(self):
        name, ok = QInputDialog.getText(self, "新建命令组", "命令组名称:")
        if ok and name.strip():
            group = {"id": uuid.uuid4().hex[:8], "name": name.strip(), "commands": []}
            self._groups.append(group)
            self._group_combo.blockSignals(True)
            self._group_combo.addItem(group["name"], group["id"])
            self._group_combo.setCurrentIndex(self._group_combo.count() - 1)
            self._group_combo.blockSignals(False)
            self._active_group_id = group["id"]
            self._rebuild_buttons()

    def _on_delete_group(self):
        if len(self._groups) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个命令组")
            return
        group = self._current_group()
        if group is None:
            return
        reply = QMessageBox.question(
            self, "确认删除", f"确定删除命令组「{group['name']}」及其所有命令？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._groups.remove(group)
        self._group_combo.blockSignals(True)
        self._group_combo.removeItem(self._group_combo.currentIndex())
        self._group_combo.blockSignals(False)
        self._active_group_id = self._groups[0]["id"]
        self._group_combo.setCurrentIndex(0)
        self._rebuild_buttons()

    def _on_add_command(self):
        dlg = CommandDialog(self)
        if dlg.exec_():
            cmd = dlg.get_command()
            if cmd:
                group = self._current_group()
                if group is not None:
                    group["commands"].append(cmd)
                    self._rebuild_buttons()

    def _on_edit_command(self, cmd_id):
        group = self._current_group()
        if group is None:
            return
        for i, cmd in enumerate(group["commands"]):
            if cmd["id"] == cmd_id:
                dlg = CommandDialog(self, command=cmd)
                if dlg.exec_():
                    updated = dlg.get_command()
                    if updated:
                        group["commands"][i] = updated
                        self._rebuild_buttons()
                return

    def _on_delete_command(self, cmd_id):
        group = self._current_group()
        if group is None:
            return
        for btn in self._buttons:
            if btn.command["id"] == cmd_id and btn.is_looping:
                btn.stop_loop()
        group["commands"] = [c for c in group["commands"] if c["id"] != cmd_id]
        self._rebuild_buttons()

    def _on_copy_command(self, cmd_id):
        group = self._current_group()
        if group is None:
            return
        for cmd in group["commands"]:
            if cmd["id"] == cmd_id:
                new_cmd = copy.deepcopy(cmd)
                new_cmd["id"] = uuid.uuid4().hex[:8]
                new_cmd["name"] = cmd["name"] + " (副本)"
                group["commands"].append(new_cmd)
                self._rebuild_buttons()
                return

    def _on_loop_command(self, cmd_id):
        for btn in self._buttons:
            if btn.command["id"] == cmd_id:
                if btn.is_looping:
                    btn.stop_loop()
                else:
                    current = btn.command.get("loop_interval_ms", 1000) or 1000
                    dlg = LoopDialog(self, current_interval=current)
                    if dlg.exec_():
                        interval = dlg.get_interval()
                        if interval:
                            btn.start_loop(interval)
                return
