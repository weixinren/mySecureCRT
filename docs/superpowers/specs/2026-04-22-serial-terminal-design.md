# mySecureCRT — 串口终端工具设计文档

## 概述

构建一个类似 SecureCRT 的串口通信工具，提供串口连接、数据收发和终端显示功能。采用 Python + PyQt5 + pyserial 技术栈，侧边栏布局，深色主题。

**目标用户**：需要通过串口与嵌入式设备、单片机等进行通信调试的开发者。

## 技术栈

| 组件     | 选型        | 说明                    |
| -------- | ----------- | ----------------------- |
| 语言     | Python 3.8+ | 跨平台                  |
| GUI 框架 | PyQt5       | 稳定、社区资源丰富      |
| 串口库   | pyserial    | 成熟的 Python 串口库    |
| 配置持久化 | JSON 文件 | 保存用户设置到本地文件  |

## 架构设计

采用模块化 MVC 架构，各模块职责分离：

```
mySecureCRT/
├── main.py              # 应用入口，初始化 QApplication 和主窗口
├── serial_manager.py    # 串口通信管理（连接、断开、收发、线程）
├── terminal_widget.py   # 终端显示控件（文本/HEX 模式、时间戳、方向标记）
├── settings_panel.py    # 左侧设置面板（串口参数、显示设置、操作按钮）
├── config.py            # 配置持久化（读写 JSON 配置文件）
├── logger.py            # 日志记录（保存收发数据到文件）
└── requirements.txt     # 依赖声明
```

### 模块详细说明

#### main.py — 应用入口

- 创建 QApplication，设置全局深色样式
- 创建主窗口 `MainWindow`，采用 `QHBoxLayout` 实现侧边栏布局
- 左侧放置 `SettingsPanel`，右侧放置 `TerminalWidget`，底部状态栏
- 负责将各模块的信号槽连接起来

#### serial_manager.py — 串口通信管理

- `SerialManager` 类继承 `QObject`，通过 Qt 信号通知数据到达
- 使用 `QThread` + 后台读取线程避免阻塞 UI
- 提供方法：
  - `open(port, baudrate, databits, stopbits, parity, flowcontrol)` — 打开串口
  - `close()` — 关闭串口
  - `write(data: bytes)` — 发送数据
  - `list_ports() -> list` — 列出可用串口
- 信号：
  - `data_received(bytes)` — 收到数据时触发
  - `connection_changed(bool)` — 连接状态变化时触发
  - `error_occurred(str)` — 发生错误时触发

#### terminal_widget.py — 终端显示控件

- 基于 `QPlainTextEdit` 自定义控件
- 支持两种显示模式，运行时可切换：
  - **文本模式**：`[HH:MM:SS] RX: Hello World`
  - **HEX 模式**：`[HH:MM:SS] RX: 48 65 6C 6C 6F | Hello`
- 时间戳格式：`[HH:MM:SS]`
- 方向标记：`TX`（橙色）/ `RX`（绿色），用不同颜色区分
- 键盘输入直接发送到串口（SecureCRT 风格），捕获 `keyPressEvent`
- 支持清屏操作
- 自动滚动到底部显示最新数据
- 使用 Consolas/Courier New 等等宽字体

#### settings_panel.py — 左侧设置面板

- 固定宽度 200px 的 QWidget，内含垂直布局
- **串口设置区域**：
  - 端口选择（QComboBox，可刷新）
  - 波特率选择（QComboBox，预设常用值：9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600）
  - 数据位（QComboBox：5, 6, 7, 8）
  - 停止位（QComboBox：1, 1.5, 2）
  - 校验位（QComboBox：None, Even, Odd, Mark, Space）
  - 流控（QComboBox：None, RTS/CTS, XON/XOFF）
- **连接按钮**：连接/断开切换，连接时变色
- **显示设置区域**：
  - 文本/HEX 模式切换按钮组
  - 清屏按钮
  - 保存日志按钮
- **刷新端口按钮**：重新扫描可用串口

#### config.py — 配置持久化

- 配置文件路径：`~/.mySecureCRT/config.json`
- 保存内容：上次使用的串口参数（端口、波特率、数据位、停止位、校验位、流控）、窗口大小和位置、显示模式（文本/HEX）
- 应用启动时自动加载，关闭时自动保存
- 配置文件不存在时使用默认值

#### logger.py — 日志记录

- 用户点击「保存」按钮后，弹出文件选择对话框选择保存路径
- 支持持续记录模式：开启后所有收发数据实时写入文件
- 日志格式与终端显示一致（带时间戳和方向标记）
- 支持 `.log` 和 `.txt` 格式

## UI 设计

### 布局结构

```
┌──────────────────────────────────────────────────┐
│  🔌 mySecureCRT — 串口终端工具                     │
├────────────┬─────────────────────────────────────┤
│ 串口设置    │                                     │
│ ──────     │  [17:20:01] RX: Hello World         │
│ 端口: COM3 │  [17:20:01] RX: Device Ready        │
│ 波特率:    │  [17:20:03] TX: AT                   │
│   115200   │  [17:20:03] RX: OK                   │
│ 数据位: 8  │  [17:20:05] TX: AT+VERSION           │
│ 停止位: 1  │  [17:20:05] RX: V2.0.1              │
│ 校验: None │  █                                   │
│ 流控: None │                                     │
│            │                                     │
│ [🔗 连接]  │                                     │
│ ──────     │                                     │
│ 显示设置    │                                     │
│ [文本][HEX]│                                     │
│ [清屏][保存]│                                     │
│ ──────     │                                     │
│ [🔄 刷新]  │                                     │
├────────────┴─────────────────────────────────────┤
│ 🟢 COM3 已连接 | 115200 8N1 | ↑TX:24 ↓RX:68     │
└──────────────────────────────────────────────────┘
```

### 深色主题配色

| 元素     | 颜色        | 说明             |
| -------- | ----------- | ---------------- |
| 背景     | `#1e1e1e`   | 主背景           |
| 侧边栏   | `#252526`   | 设置面板背景     |
| 输入控件  | `#3c3c3c`   | 下拉框等控件背景 |
| 边框     | `#333333`   | 分割线和边框     |
| 主文字   | `#cccccc`   | 正常文字         |
| RX 数据  | `#569cd6`   | 蓝色，接收数据   |
| TX 数据  | `#ce9178`   | 橙色，发送数据   |
| RX 标签  | `#6a9955`   | 绿色背景标签     |
| TX 标签  | `#ce9178`   | 橙红色背景标签   |
| 强调色   | `#4ec9b0`   | 标题/分类标签    |
| 按钮     | `#0e639c`   | 主操作按钮       |
| 状态栏   | `#007acc`   | 底部状态栏       |

### 状态栏信息

- 连接状态指示（🟢 已连接 / 🔴 未连接）
- 当前串口参数摘要（COM3 | 115200 8N1）
- 收发字节统计（↑TX: 24 bytes | ↓RX: 68 bytes）
- 日志记录状态（📝 日志记录中）

## 数据流

```
键盘输入 → TerminalWidget.keyPressEvent()
         → SerialManager.write(data)
         → pyserial 发送到串口
         → TerminalWidget 显示 TX 数据

串口设备 → pyserial 后台读取线程
         → SerialManager.data_received 信号
         → TerminalWidget 显示 RX 数据
         → Logger 记录到文件（如已开启）
```

## 错误处理

- **串口打开失败**：弹出 QMessageBox 提示错误原因（端口被占用、权限不足等）
- **连接断开**：自动检测串口断开，更新状态栏，终端显示断开提示
- **数据编码错误**：HEX 模式下直接显示字节；文本模式下使用 UTF-8 解码，无法解码的字节显示为占位符

## 配置文件示例

```json
{
  "serial": {
    "port": "COM3",
    "baudrate": 115200,
    "databits": 8,
    "stopbits": 1,
    "parity": "None",
    "flowcontrol": "None"
  },
  "display": {
    "mode": "text"
  },
  "window": {
    "width": 900,
    "height": 600,
    "x": 100,
    "y": 100
  }
}
```

## 范围限制（第一版不包含）

- 多标签/多会话
- SSH/Telnet 连接
- 脚本自动化
- 完整终端仿真（VT100/xterm）
- ANSI 颜色转义序列支持
- 快捷发送面板
- 插件系统
