# 微信聊天截图工具

微信 PC 版聊天记录截图 + 纵向拼图工具，支持 Windows 和 macOS。

## 版本

| 平台 | 版本 | 目录 |
|------|------|------|
| Windows | v1.1 | `win/` |
| macOS | v1.0 | `mac/` |

## 功能

- **校准** - 框选微信消息列表区域
- **历史回溯** - 向上滚动，抓取历史聊天记录
- **新消息监控** - 向下滚动，抓取最新消息
- **纵向拼图** - 无缝拼接为一张长图

## 使用步骤

### 1. 校准

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

向上滚（历史记录）：
```bash
python scrape_history.py up
```

向下滚（新消息）：
```bash
python scrape_history.py down
```

截图保存在 `screenshots/history_YYYYMMDD_HHMMSS/`。

### 3. 拼接长图

```bash
python stitch.py                    # 拼接，输出带时间戳
python stitch.py calibrate          # 自动检测偏移量
python stitch.py -o mychat.png      # 指定输出文件名
```

输出保存在 `output/`。

## 文件结构

```
wxauto/
├── win/
│   ├── capture_chat.py      # 校准 + 单张截图
│   ├── scrape_history.py    # 滚动抓取
│   ├── stitch.py            # 纵向拼图
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
pip install uiautomation pillow opencv-python numpy
```

**macOS:**
```bash
pip install pyscreenshot pyautogui pillow opencv-python numpy
```

## 注意事项

- Windows 版本使用 `uiautomation` 和 `ctypes` 操作窗口
- macOS 版本使用 `osascript` (AppleScript) 和 `pyautogui`
- `config/chat_region.json` 不需要提交（已加入 .gitignore）
- 每次校准后会记录 `scrape_direction` 参数，拼接时自动识别 up/down 模式
