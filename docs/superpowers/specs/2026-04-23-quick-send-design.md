# 快捷发送面板设计文档

## 概述

为 mySecureCRT 添加快捷发送面板，支持预设常用命令一键发送，适用于嵌入式调试场景。面板位于终端区域右侧，支持文本和 HEX 两种命令类型，支持命令分组管理和循环定时发送。

**目标用户场景**：嵌入式开发者需要反复发送调试命令（如 `help`、`reboot`、`log level`）和协议测试帧（如 HEX 心跳包），不同项目有不同的命令集。

## UI 设计

### 布局

右侧独立面板，与左侧设置面板对称。三栏布局：

```
┌──────────┬─────────────────────────────┬──────────┐
│ 串口设置  │ [🟢 COM3] [🔴 COM5] [＋新建] │ ⚡快捷发送│
│ 端口 COM3 │                             │ 调试命令 ▾│
│ 波特率... │  #DK> help                  │ ┌────────┐│
│           │  misc  - misc test          │ │📝 help  ││
│ 显示设置  │  log   - log level          │ │📝 reboot││
│ [终端]... │  #DK> _                     │ │📝 log 3 ││
│           │                             │ │🔁 心跳包││
│ [清屏]    │                             │ │🔢 AA 55 ││
│ [保存]    │                             │ └────────┘│
│           │                             │ [＋添加命令]│
├──────────┴─────────────────────────────┴──────────┤
│ 🟢 已连接  COM3 | 115200 8N1   ↑TX:6 ↓RX:512     │
└───────────────────────────────────────────────────┘
```

### 面板结构（从上到下）

1. **标题栏**：「⚡ 快捷发送」+ 折叠按钮 ◀/▶
2. **命令组选择器**：QComboBox 下拉选择命令组，旁边「＋」按钮新建组、「🗑️」删除组
3. **命令按钮列表**：垂直排列的 CommandButton，可滚动
4. **添加按钮**：底部「＋ 添加命令」按钮

### 命令按钮样式

- **文本命令**：📝 图标 + 命令名称，深灰背景 `#3c3c3c`
- **HEX 命令**：🔢 图标 + HEX 数据预览，紫色文字 `#e8a0e8`
- **循环发送中**：🔁 图标，绿色边框 + 深绿背景 `#0d4f3c`，⏹ 停止图标

### 交互

- **左键单击**：立即发送命令到当前活动标签页
- **右键菜单**：
  - ✏️ 编辑命令...
  - 📋 复制命令
  - ───────────
  - 🔁 设置循环发送...
  - ───────────
  - 🗑️ 删除
- **循环发送中的按钮**：左键点击停止循环
- **折叠按钮**：◀ 折叠面板（隐藏内容，仅保留窄条）/ ▶ 展开

### 命令编辑对话框（CommandDialog）

弹出 QDialog，包含：
- **名称**：QLineEdit，必填
- **数据**：QLineEdit / QTextEdit，必填
- **类型**：QComboBox，选项：「文本」/「HEX」
- **追加换行**：QCheckBox，仅文本类型可用，默认勾选
- **HEX 格式校验**：实时校验，非法字符红色提示

### 循环发送设置对话框

简单弹窗：
- **间隔(ms)**：QSpinBox，范围 100~60000，默认 1000
- **确定 / 取消**

## 架构设计

### 新增文件

```
mySecureCRT/
├── quick_send_panel.py      # QuickSendPanel + CommandButton
├── quick_send_dialog.py     # CommandDialog + LoopDialog
├── tests/
│   ├── test_quick_send_panel.py
│   └── test_quick_send_dialog.py
```

### 修改文件

```
├── config.py                # DEFAULT_CONFIG 增加 quick_send 字段
├── main.py                  # 右侧布局加入 QuickSendPanel
├── tests/test_config.py     # 新增 quick_send 配置测试
```

### QuickSendPanel（QWidget）

```python
class QuickSendPanel(QWidget):
    send_requested = pyqtSignal(bytes)  # 编码后的数据，MainWindow 路由到活动 session

    def __init__(self):
        # 标题栏 + 折叠按钮
        # 命令组 QComboBox + 新建/删除组按钮
        # QScrollArea 包含命令按钮列表
        # 底部「＋ 添加命令」按钮

    def set_groups(self, groups):
        """从 config 加载命令组列表"""

    def get_groups(self):
        """导出当前命令组为 config 格式"""

    def active_group_id(self):
        """当前选中的命令组 ID"""

    def stop_all_loops(self):
        """停止所有循环发送（关闭标签时调用）"""

    def set_collapsed(self, collapsed):
        """折叠/展开面板"""
```

### CommandButton（QPushButton）

```python
class CommandButton(QPushButton):
    send_clicked = pyqtSignal(bytes)     # 左键点击发送
    edit_requested = pyqtSignal(str)     # 请求编辑（传 command id）
    delete_requested = pyqtSignal(str)   # 请求删除
    copy_requested = pyqtSignal(str)     # 请求复制

    def __init__(self, command_config):
        # command_config: {"id", "name", "data", "type", "append_newline", "loop_interval_ms"}
        self._timer = QTimer()           # 循环发送用
        self._looping = False

    def start_loop(self, interval_ms):
        """启动循环发送"""

    def stop_loop(self):
        """停止循环发送"""

    def encode_data(self):
        """根据 type 编码数据：text → bytes (+ optional \\r\\n), hex → bytes"""

    def contextMenuEvent(self, event):
        """右键菜单：编辑/复制/循环设置/删除"""
```

### CommandDialog（QDialog）

```python
class CommandDialog(QDialog):
    def __init__(self, parent=None, command=None):
        # command=None 为新建，否则为编辑
        # 名称 QLineEdit
        # 数据 QLineEdit
        # 类型 QComboBox ("text" / "hex")
        # 追加换行 QCheckBox（文本类型时可用）

    def get_command(self):
        """返回 command dict 或 None（取消）"""

    def _validate_hex(self, text):
        """实时校验 HEX 格式，非法时红色边框"""
```

### 数据流

```
用户左键点击 CommandButton
  → CommandButton.encode_data() → bytes
  → CommandButton.send_clicked.emit(bytes)
  → QuickSendPanel.send_requested.emit(bytes)
  → MainWindow._on_quick_send(data: bytes)
    → self._active_session.serial_manager.write(data)

循环发送：
  QTimer.timeout → CommandButton.encode_data() → send_clicked.emit(bytes)
  （同上路径）

循环发送始终发到当前活动标签页：
  MainWindow._on_quick_send 使用 self._active_session。
  如果用户切换标签，循环数据跟随发到新的活动标签。
  绑定到特定 session 的需求留待后续版本。
```

### Config 扩展

在 `config.py` 的 `DEFAULT_CONFIG` 中增加：

```python
DEFAULT_CONFIG = {
    "sessions": [...],
    "active_session": "",
    "window": {...},
    "quick_send": {
        "collapsed": False,
        "groups": [
            {
                "id": "default",
                "name": "默认命令组",
                "commands": []
            }
        ],
        "active_group": "default"
    }
}
```

每个 command 结构：

```python
{
    "id": "uuid8",          # uuid4().hex[:8]
    "name": "help",         # 显示名称
    "data": "help",         # 发送数据（文本或 HEX 字符串）
    "type": "text",         # "text" 或 "hex"
    "append_newline": True, # 仅 text 类型有效
    "loop_interval_ms": 0   # 0=不循环，>0=循环间隔
}
```

### MainWindow 修改

```python
# _init_ui 中，终端区域右侧加入 QuickSendPanel
self.quick_send_panel = QuickSendPanel()
main_layout.addWidget(self.quick_send_panel)

# 连接信号
self.quick_send_panel.send_requested.connect(self._on_quick_send)

def _on_quick_send(self, data: bytes):
    session = self._active_session
    if session and session.serial_manager.is_connected:
        session.serial_manager.write(data)

# _save_config 中保存 quick_send
self.config.set("quick_send", {
    "collapsed": self.quick_send_panel.is_collapsed,
    "groups": self.quick_send_panel.get_groups(),
    "active_group": self.quick_send_panel.active_group_id()
})

# closeEvent 中停止所有循环
self.quick_send_panel.stop_all_loops()
```

## 测试策略

### QuickSendPanel 测试（test_quick_send_panel.py）

1. **test_set_get_groups** — set_groups 加载后 get_groups 返回相同数据
2. **test_add_command** — 添加命令后按钮出现在列表中
3. **test_delete_command** — 删除命令后按钮从列表移除
4. **test_switch_group** — 切换命令组后按钮列表更新
5. **test_send_text_command** — 点击文本命令按钮，send_requested 发出正确 bytes
6. **test_send_hex_command** — 点击 HEX 命令按钮，send_requested 发出正确 bytes
7. **test_send_text_with_newline** — append_newline=True 时追加 \r\n
8. **test_loop_start_stop** — 循环发送启动/停止，验证 timer 状态
9. **test_stop_all_loops** — stop_all_loops 停止所有活跃的循环

### CommandDialog 测试（test_quick_send_dialog.py）

1. **test_new_command_dialog** — 新建模式，各控件默认值正确
2. **test_edit_command_dialog** — 编辑模式，控件填入已有数据
3. **test_hex_validation_valid** — 合法 HEX（"AA 55 01"）通过校验
4. **test_hex_validation_invalid** — 非法 HEX（"GG ZZ"）校验失败
5. **test_append_newline_disabled_for_hex** — HEX 类型时换行复选框禁用

### Config 测试（追加到 test_config.py）

1. **test_default_config_has_quick_send** — 默认配置包含 quick_send 字段
2. **test_quick_send_save_and_load** — 保存后重新加载数据一致

## 边界情况

| 场景 | 处理方式 |
|------|---------|
| 未连接时发送 | 静默忽略，不弹错误 |
| HEX 格式错误 | 编辑对话框实时校验，红色边框提示，确定按钮禁用 |
| 循环发送时关闭标签 | 循环继续（发到新的活动标签），关闭应用时 stop_all_loops |
| 空命令组 | 显示占位文字"点击下方按钮添加命令" |
| 面板折叠状态 | 持久化到 config，重启恢复 |
| 删除正在循环的命令 | 先停止 timer，再删除 |
| 删除命令组 | 确认对话框，删除后切换到第一个组；至少保留一个组 |
| 极长命令名 | 按钮文字 elide（省略号截断） |

## 样式

继承现有 DARK_THEME，新增：

```css
QuickSendPanel {
    background-color: #252526;
    border-left: 1px solid #333333;
}
```

命令按钮和循环状态样式通过 Python setStyleSheet 动态设置，与现有 QPushButton 主题保持一致。

## 范围限制（本版不包含）

- 命令导入/导出（JSON/CSV）
- 序列发送（多命令按顺序依次发送）
- 拖拽排序命令
- 发送目标选择（指定标签页）
- 命令快捷键绑定
