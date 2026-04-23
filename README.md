# 🔌 mySecureCRT — 串口终端工具

<p align="center">
  <img src="串口工具图标.png" width="128" alt="mySecureCRT">
</p>

<p align="center">
  一款类似 SecureCRT 的轻量级串口终端工具，基于 Python + PyQt5 开发，支持 VT100 终端仿真。
</p>

---

## ✨ 功能特性

- **多标签/多会话**
  - 🗂️ 同时连接多个串口设备（支持 4-8 个标签页）
  - 🔄 共享侧边栏，自动跟随活动标签切换设置
  - ⌨️ Ctrl+T 新建 / Ctrl+W 关闭 / 双击重命名标签
  - 💾 所有标签页配置自动持久化，下次启动恢复

- **三种显示模式**
  - 🖥️ **终端模式** — 完整 VT100 仿真，支持光标移动、Shell 交互，体验与 SecureCRT 一致
  - 📋 **监控模式** — 带时间戳的 RX/TX 逐行日志，适合查看串口通信记录
  - 🔢 **HEX 模式** — 十六进制 dump 显示原始字节数据

- **日志级别着色**
  - 🔵 `<I>` 信息 — 蓝色
  - 🟡 `<W>` 警告 — 黄色
  - 🔴 `<E>` 错误 — 红色

- **串口配置**
  - 支持波特率：9600 ~ 921600
  - 数据位：5/6/7/8
  - 停止位：1/1.5/2
  - 校验位：None/Even/Odd/Mark/Space
  - 流控：None/RTS-CTS/XON-XOFF

- **其他功能**
  - 🔤 动态字体大小调节（Ctrl+滚轮 或侧边栏控件，8~48pt）
  - 💾 串口日志保存到文件
  - ⚙️ 配置自动持久化（窗口位置、串口参数、字体大小等）
  - 🎨 VS Code 风格深色主题
  - ⌨️ 方向键、Home/End/Delete 等快捷键支持

## 📸 界面预览

```
┌──────────────────────────────────────────────────────────┐
│  串口设置    │ [🟢 COM3] [🟢 COM5] [🔴 COM8] [＋]       │
│  端口 COM3   │                                            │
│  波特率 115200│  [0.270] <I> Entering Startup State       │
│  数据位 8    │  [0.471] <W> deserial chip link not locked│
│  ...         │  [1.571] <E> Set error code 0x00000100    │
│  显示设置    │  #DK> help                                │
│  [终端][监控] │  misc     - misc test                     │
│  [HEX]       │  log      - global log level              │
│  字号 14pt   │  help     - print command description     │
│  [清屏][保存] │  #DK> _                                   │
├──────────────┴────────────────────────────────────────────┤
│  🟢 已连接  COM3 | 115200 8N1    ↑TX: 6  ↓RX: 512 | 3 个会话│
└──────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 方式一：直接运行 exe（推荐）

从 [Releases](https://github.com/weixinren/mySecureCRT/releases) 下载 `mySecureCRT.exe`，双击运行即可，无需安装 Python 环境。

### 方式二：从源码运行

```bash
# 克隆仓库
git clone https://github.com/weixinren/mySecureCRT.git
cd mySecureCRT

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 从源码打包 exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name mySecureCRT --icon=app_icon.ico --add-data "app_icon.ico;." --hidden-import pyte --hidden-import serial --hidden-import serial.tools.list_ports main.py
```

打包后的 exe 位于 `dist/mySecureCRT.exe`。

## 🧪 运行测试

```bash
python -m pytest tests/ -v
```

## 📁 项目结构

```
mySecureCRT/
├── main.py              # 主窗口（多标签 QTabWidget）、深色主题、信号连接
├── session.py           # 会话管理（多标签 Session 封装）
├── terminal_widget.py   # 终端组件（VT100仿真 + 监控 + HEX）
├── settings_panel.py    # 侧边栏设置面板
├── serial_manager.py    # 串口管理器 + 读取线程
├── config.py            # 配置管理（JSON 持久化，V2 多会话 schema）
├── logger.py            # 数据日志记录器
├── requirements.txt     # Python 依赖
├── app_icon.ico         # 应用图标
└── tests/               # 单元测试
    ├── test_config.py
    ├── test_session.py
    ├── test_settings_panel.py
    ├── test_logger.py
    ├── test_serial_manager.py
    └── test_terminal_widget.py
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| GUI 框架 | PyQt5 |
| 串口通信 | pyserial |
| 终端仿真 | pyte (VT100) |
| 打包工具 | PyInstaller |
| 测试框架 | pytest |

## 📄 配置文件

配置自动保存在 `~/.mySecureCRT/config.json`，包含：
- 多会话配置（每个标签页的串口参数、显示设置）
- 活动会话标识（重启后恢复到上次的标签）
- 显示模式和字体大小
- 窗口位置和尺寸

## 📝 许可证

MIT License
