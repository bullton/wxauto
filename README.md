# 微信聊天截图工具

微信 PC 版聊天记录截图 + 纵向拼图工具，支持 Windows 和 macOS。

## 版本

| 平台 | 版本 | 目录 |
|------|------|------|
| Windows | v1.2 | `win/` |
| macOS | v1.0 | `mac/` |

## 功能

- **校准** - 框选微信消息列表区域
- **历史回溯** - 向上滚动，抓取历史聊天记录
- **时间戳检测** - OCR 识别时间戳，滚动到指定日期自动停止
- **新消息监控** - 向下滚动，抓取最新消息
- **纵向拼图** - 无缝拼接为一张长图，支持分卷

## 完整使用流程

### 1. 校正窗口（只需一次）

打开目标聊天窗口，运行：

**Windows:**
```bash
cd win
python capture_chat.py calibrate
```

**macOS:**
```bash
cd mac
python capture_chat.py calibrate
```

拖拽框选聊天消息列表区域（不含标题栏），ESC 取消。

### 2. 抓取截图

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

### 3. 校准偏移量

截图完成后，运行：
```bash
python stitch.py calibrate
```

自动检测截图重叠偏移量，写入配置文件。

### 4. 拼接长图

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

## 时间戳检测说明

OCR 自动识别截图中的时间戳，支持以下格式：

| 格式 | 示例 | 说明 |
|------|------|------|
| 昨天 | 昨天 23:59 | 解析为前一天的 00:00 |
| 星期几 | 星期一 19:30 | 根据当前星期推断实际日期 |
| X月X日 | 7月8日 10:30 | 直接使用该日期 |
| 仅时间 | 19:30 | 视为今天 |

当识别到的时间戳早于或等于截止时间时，自动停止截图。

## 文件结构

```
wxauto/
├── win/
│   ├── capture_chat.py      # 校准 + 单张截图
│   ├── scrape_history.py    # 滚动抓取（支持 OCR 时间戳检测）
│   ├── stitch.py            # 纵向拼图（支持分卷）
│   └── config/              # 配置文件
├── mac/
│   ├── capture_chat.py      # 校准 + 单张截图
│   ├── scrape_history.py    # 滚动抓取
│   └── config/              # 配置文件
├── screenshots/             # 截图存放
└── output/                  # 拼接输出
```

## 依赖

**Windows:**
```bash
pip install uiautomation pillow opencv-python numpy windows
```

**macOS:**
```bash
pip install pyscreenshot pyautogui pillow opencv-python numpy
```

## 注意事项

- Windows 版本使用 `uiautomation` 和 `ctypes` 操作窗口
- Windows OCR 使用 Windows.Media.Ocr（winrt 库），支持中文识别
- macOS 版本使用 `osascript` (AppleScript) 和 `pyautogui`
- `config/chat_region.json` 不需要提交（已加入 .gitignore）
- 每次校准后会记录 `scrape_direction` 参数，拼接时自动识别 up/down 模式
