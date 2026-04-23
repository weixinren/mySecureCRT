# mySecureCRT 多标签/多会话功能设计文档

## 概述

为 mySecureCRT 串口终端工具添加多标签（Multi-tab）支持，允许用户在同一窗口中同时打开和管理多个串口连接（4-8 个设备），适用于多模块系统联调场景。

## 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 标签栏位置 | 终端区域上方（类似浏览器） | 用户熟悉，布局自然 |
| 侧边栏策略 | 共享侧边栏，跟随活动标签切换 | 界面简洁，改动小 |
| 显示模式 | 每个标签独立 | 联调时不同设备用不同模式 |
| 会话持久化 | 保存所有标签配置，启动时恢复 | 免重复配置 |
| 标签命名 | 自动用端口名，支持双击重命名 | 快速识别设备 |

## 架构设计

### Session 模型

引入 `Session` 数据类，将现有的单实例组件封装为可多实例的会话单元。新增 `session.py` 文件。

```
Session（每个标签页一个实例）
├── id: str                         # 唯一标识（UUID）
├── name: str                       # 标签名（默认=端口名）
├── serial_manager: SerialManager   # 独立串口连接
├── terminal: TerminalWidget        # 独立终端显示
├── logger: DataLogger              # 独立日志记录
└── config: dict                    # 该会话的串口参数 + 显示模式
```

每个 Session 内部管理自己的信号连接：
- `serial_manager.data_received` → Session 内部处理 → `terminal.append_data`
- `serial_manager.connection_changed` → 通知 MainWindow 更新 UI
- `serial_manager.error_occurred` → 通知 MainWindow 显示错误
- `terminal.key_pressed` → `serial_manager.write`

### MainWindow 变化

**之前（V1）：**
```
MainWindow
├── SettingsPanel (唯一)
├── TerminalWidget (唯一)
├── SerialManager (唯一)
├── DataLogger (唯一)
└── StatusBar
```

**之后（V2）：**
```
MainWindow
├── SettingsPanel (唯一，共享)
├── QTabWidget
│   ├── Tab 0 → Session 0 (SerialManager + TerminalWidget + DataLogger)
│   ├── Tab 1 → Session 1 (SerialManager + TerminalWidget + DataLogger)
│   └── Tab N → Session N (...)
└── StatusBar (显示活动 Session 信息)
```

MainWindow 通过 `_active_session` 引用管理当前活动的 Session。切换标签时：
1. 断开旧 Session 与侧边栏/状态栏的关联
2. 建立新 Session 与侧边栏/状态栏的关联
3. 侧边栏控件加载新 Session 的配置值

### 信号连接管理

MainWindow 维护一个 `_active_connections` 列表，存储当前活动 Session 的信号连接。切换标签时先 disconnect 所有旧连接，再 connect 新的：

```python
def _switch_session(self, new_session):
    # 断开旧连接
    for conn in self._active_connections:
        conn.disconnect()
    self._active_connections.clear()

    self._active_session = new_session

    # 建立新连接
    self._active_connections = [
        new_session.serial_manager.connection_changed.connect(self._on_connection_changed),
        new_session.serial_manager.error_occurred.connect(self._on_error),
        # ...
    ]

    # 同步侧边栏
    self.settings_panel.apply_session_config(new_session.config)
    self.settings_panel.set_connected(new_session.serial_manager.is_connected)
```

## 标签栏设计

### UI 规格

- 使用 `QTabWidget`，`tabsClosable=True`
- 标签栏右侧有 **「＋」按钮**（通过 `setCornerWidget` 实现）
- 标签文本格式：`{状态图标} {名称}`，例如 `🟢 COM3`、`🔴 新会话`
- 双击标签触发重命名（弹出 QInputDialog）

### 交互行为

| 操作 | 行为 |
|------|------|
| 点击「＋」或 Ctrl+T | 创建新标签（未连接，名称"新会话"） |
| 点击标签×或 Ctrl+W | 如已连接先断开串口，再关闭标签并销毁 Session |
| 双击标签 | 弹出重命名对话框 |
| Ctrl+Tab | 切换到下一个标签 |
| Ctrl+Shift+Tab | 切换到上一个标签 |
| 连接成功 | 如未手动重命名，自动改名为端口名 |
| 最后一个标签关闭 | 自动创建一个新的空标签（保证至少有一个标签） |

## 侧边栏联动

SettingsPanel 保持单实例，不做大结构改动。新增以下方法：

```python
def apply_session_config(self, config: dict):
    """加载指定 Session 的完整配置到所有控件"""
    # 串口参数
    self._set_combo(self.port_combo, config.get('port', ''))
    self._set_combo(self.baud_combo, str(config.get('baudrate', 115200)))
    # ... 其他参数
    # 显示模式
    mode = config.get('display_mode', 'terminal')
    self._set_display_mode(mode)
    # 字体大小
    self.font_spin.setValue(config.get('font_size', 14))

def get_session_config(self) -> dict:
    """从当前控件状态导出为 Session 配置"""
    settings = self.get_settings()
    settings['display_mode'] = self._current_display_mode()
    settings['font_size'] = self.font_spin.value()
    return settings
```

侧边栏的信号（connect_clicked、display_mode_changed 等）仍然连接到 MainWindow，由 MainWindow 转发到 `_active_session`。

## 配置持久化

### 新的 JSON 结构

```json
{
  "sessions": [
    {
      "id": "a1b2c3d4",
      "name": "COM3",
      "renamed": false,
      "serial": {
        "port": "COM3",
        "baudrate": 115200,
        "databits": 8,
        "stopbits": 1,
        "parity": "None",
        "flowcontrol": "None"
      },
      "display": {
        "mode": "terminal",
        "font_size": 14
      }
    }
  ],
  "active_session": "a1b2c3d4",
  "window": {
    "width": 1200,
    "height": 700,
    "x": 100,
    "y": 100
  }
}
```

`renamed` 字段用于判断连接时是否自动更新标签名。用户手动重命名后 `renamed=true`，连接成功不再覆盖名称。

### 向后兼容

ConfigManager 加载时检测旧格式（无 `sessions` 键），自动迁移：

```python
def _migrate_v1_config(self, old_config):
    """将 V1 单会话格式迁移为 V2 多会话格式"""
    session = {
        "id": str(uuid.uuid4())[:8],
        "name": old_config.get("serial", {}).get("port", "新会话"),
        "renamed": False,
        "serial": old_config.get("serial", {}),
        "display": old_config.get("display", {})
    }
    return {
        "sessions": [session],
        "active_session": session["id"],
        "window": old_config.get("window", {})
    }
```

### 存取行为

- **启动时**：加载 config.json → 为每个 session 创建 Tab → 激活 active_session
- **关闭时**：遍历所有 Tab → 收集每个 Session 的当前配置 → 保存
- **不保存连接状态**：启动时所有标签均为未连接状态，需用户手动连接

## 状态栏

状态栏显示当前活动 Session 的信息，切换标签时更新：

```
🟢 COM3 已连接 | 115200 8N1 | ↑TX:24 ↓RX:512 | 3 个会话
```

最右侧新增"N 个会话"计数。

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `session.py` | **新增** | Session 类，封装 SerialManager + TerminalWidget + DataLogger |
| `main.py` | **重构** | QTabWidget 替代单个 TerminalWidget，Session 管理，标签操作 |
| `settings_panel.py` | **修改** | 新增 apply_session_config / get_session_config 方法 |
| `config.py` | **修改** | 多会话 JSON 结构，向后兼容迁移 |
| `terminal_widget.py` | **不变** | 接口不变，多实例化即可 |
| `serial_manager.py` | **不变** | 接口不变，多实例化即可 |
| `logger.py` | **不变** | 接口不变，多实例化即可 |
| `tests/test_session.py` | **新增** | Session 创建/销毁测试 |
| `tests/test_config.py` | **修改** | 新增多会话配置、迁移测试 |

## 测试策略

### 新增测试

**test_session.py:**
- Session 创建时正确初始化三个子组件
- Session 销毁时正确断开连接和清理资源
- 多个 Session 实例互不干扰

**test_config.py 新增用例:**
- 多会话配置的存取
- V1 → V2 格式自动迁移
- 空 sessions 列表时创建默认会话

### 现有测试不变

`test_serial_manager.py`、`test_logger.py`、`test_terminal_widget.py` 的所有测试保持不变，因为这些模块的公开接口没有变化。

## 不在本次范围内

- 标签拖拽排序
- 分屏显示（同时查看多个终端）
- 会话分组/文件夹
- 自动重连
