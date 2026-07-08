# 微信聊天截图工具

微信 PC 版聊天记录截图 + 纵向拼图工具，支持 Windows 和 macOS。

## 版本

| 平台 | 版本 | 目录 | 发布形态 |
|------|------|------|---------|
| Windows | v1.3 | `win/` | PyInstaller 单文件 exe (~72 MB) |
| macOS | v1.0 | `mac/` | Python 脚本 |

## 功能

- **校准** - 框选微信消息列表区域
- **历史回溯** - 向上滚动，抓取历史聊天记录
- **时间戳检测** - OCR 识别时间戳，滚动到指定日期自动停止
- **新消息监控** - 向下滚动，抓取最新消息
- **纵向拼图** - 无缝拼接为一张长图，支持分卷

---

## 🚀 Windows 零环境部署（推荐）

无需安装 Python，直接使用预打包好的 exe。

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 1809 (2018年10月更新) 及以上 / Windows 11 |
| 微信 | 微信 PC 版 3.x（必须安装并登录） |
| 屏幕分辨率 | ≥ 1280×720 |
| DPI 缩放 | 支持任意缩放（已自动适配） |
| 用户权限 | 普通用户权限即可 |

### 安装步骤

1. **下载 exe**
   - 从 [Releases](../../releases) 下载 `微信聊天截图工具.exe`（约 72 MB）
   - 或从仓库 `win/dist/微信聊天截图工具.exe` 直接获取

2. **放置到任意目录**
   - 例如：`D:\Tools\`、`C:\Users\你的用户名\Desktop\` 均可
   - 目录需要可写权限（用于保存配置和截图）

3. **启动微信 PC 版**
   - 登录微信
   - 打开要截图的目标聊天窗口

4. **双击运行 exe**
   - 首次运行会自动创建 `config/`、`screenshots/`、`output/` 子目录

5. **完成三步操作**
   - 点击「校正窗口」→ 拖拽框选聊天区域
   - 点击「开始截图 (含校准+拼图)」→ 自动完成截图+拼图全程
   - 结果在 `output/` 目录下

### 零环境运行原理

PyInstaller 将以下组件打包到单个 exe 中：

- ✅ Python 解释器（v3.14）
- ✅ 所有 Python 依赖（uiautomation、PIL、opencv、winrt 等）
- ✅ 项目脚本（gui.py、scrape_history.py、stitch.py 等）

操作系统层依赖（必须满足）：

- ✅ **Windows.Media.Ocr API**：Windows 10 1809+ 自带
- ✅ **UIAutomation 框架**：Windows Vista+ 自带
- ✅ **DPI 感知 API**：Windows 10 1703+ 自带
- ⚠️ **Visual C++ Redistributable 2015-2022**：几乎所有现代电脑都已预装

如 OCR 报"未安装中文语言包"错误，需在 Windows 设置 → 时间和语言 → 区域和语言 → 添加中文（简体）语言包。

---

## 💻 源码运行（开发者）

适合需要自定义或调试的用户。

### 安装依赖

**Windows:**
```bash
pip install uiautomation pillow opencv-python numpy windows
```

**macOS:**
```bash
pip install pyscreenshot pyautogui pillow opencv-python numpy
```

### 完整使用流程

#### 1. 校正窗口（只需一次）

打开目标聊天窗口，运行：

**Windows:**
```bash
cd win
python gui.py          # 启动 GUI（含校准/截图/拼图所有功能）
# 或：
python capture_chat.py calibrate   # 独立校准
```

**macOS:**
```bash
cd mac
python capture_chat.py calibrate
```

拖拽框选聊天消息列表区域（不含标题栏），ESC 取消。

#### 2. 抓取截图

向上滚（历史记录）到指定日期停止：
```bash
# 截取到昨天 0 点停止
python scrape_history.py up --yesterday

# 截取到指定日期 0 点停止
python scrape_history.py up --stop=2026-07-01

# 截取到指定时间停止
python scrape_history.py up --stop="2026-07-01 08:00"
```

向下滚（新消息）：
```bash
python scrape_history.py down
```

截图保存在 `screenshots/history_YYYYMMDD_HHMMSS/`。

#### 3. 校准偏移量

截图完成后，运行：
```bash
python stitch.py calibrate
```

自动检测截图重叠偏移量，写入配置文件。

#### 4. 拼接长图

```bash
# 每 50 张拼一张（默认）
python stitch.py

# 每 30 张拼一张
python stitch.py -m 30

# 指定输出文件名
python stitch.py -o mychat.png

# 指定输出文件名 + 每30张拼一张
python stitch.py -o mychat.png -m 30
```

输出保存在 `output/`。

---

## ⏱ 时间戳检测说明

OCR 自动识别截图中的时间戳，支持以下格式：

| 格式 | 示例 | 说明 |
|------|------|------|
| 昨天 | 昨天 23:59 | 解析为前一天的具体时间 |
| 星期几 | 星期一 19:30 | 根据当前星期推断实际日期 |
| X月X日 | 7月8日 10:30 | 直接使用该日期 |
| 仅时间 | 19:30 | 视为今天 |

当识别到的时间戳早于或等于截止时间时，自动停止截图。

---

## 📁 文件结构

```
wxauto/
├── win/
│   ├── dist/                                  # 预打包的 exe
│   │   └── 微信聊天截图工具.exe                # (~72 MB)
│   ├── capture_chat.py                        # 校准 + 单张截图
│   ├── scrape_history.py                      # 滚动抓取（支持 OCR 时间戳检测）
│   ├── stitch.py                              # 纵向拼图（支持分卷）
│   ├── gui.py                                 # 图形界面
│   ├── runtime_paths.py                       # 路径管理（exe模式自动用exe目录）
│   ├── wxauto.spec                            # PyInstaller 打包配置
│   ├── config/                                # 配置文件（运行时创建）
│   ├── screenshots/                           # 截图存放（运行时创建）
│   └── output/                                # 拼接输出（运行时创建）
└── mac/
    ├── capture_chat.py                        # 校准 + 单张截图
    ├── scrape_history.py                      # 滚动抓取
    └── config/                                # 配置文件（运行时创建）
```

---

## 🔧 常见问题

### exe 双击后闪退？

- **系统版本过低**：需要 Windows 10 1809+
- **杀毒软件拦截**：将 exe 添加到杀毒软件白名单
- **UAC 权限问题**：右键 → 以管理员身份运行

### OCR 识别不到文字？

- **缺少中文 OCR 语言包**：
  1. 打开「设置」→「时间和语言」→「区域和语言」
  2. 添加语言 → 中文（简体）
  3. 等待 Windows Update 安装 OCR 引擎
- **截图分辨率过低**：建议微信窗口不小于 1280×720

### 滚动点击打开了图片/小程序？

本工具已做了规避：自动点击聊天区右上角空白区域。如果还遇到：
- 让微信窗口大一些（不要最小化）
- 确保聊天区右侧 1/6 没有重要内容

### 截图区域坐标不对？

- 重新运行「校正窗口」，仔细框选聊天消息区域
- 多显示器时，确保微信窗口在主显示器（避免跨屏）

---

## 📌 注意事项

- Windows 版本使用 `uiautomation` 和 `ctypes` 操作窗口
- Windows OCR 使用 Windows.Media.Ocr（winrt 库），支持中文识别
- macOS 版本使用 `osascript` (AppleScript) 和 `pyautogui`
- `config/chat_region.json` 不需要提交（已加入 .gitignore）
- 每次校准后会记录 `scrape_direction` 参数，拼接时自动识别 up/down 模式
- exe 模式首次运行会在 exe 所在目录创建 `config/`、`screenshots/`、`output/`

---

## 📄 许可证

MIT
