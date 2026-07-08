# 微信聊天截图工具 v1.0

微信 PC 版聊天记录截图 + 纵向拼图工具，可独立运行。

## 功能

- **校准** - 框选微信消息列表区域
- **历史回溯** - 向上滚动，抓取历史聊天记录
- **新消息监控** - 向下滚动，抓取最新消息
- **纵向拼图** - 无缝拼接为一张长图

## 使用步骤

### 1. 校准

打开目标聊天窗口，运行：

```
python capture_chat.py calibrate
```

拖拽框选聊天消息列表区域（不含标题栏），回车确认。

### 2. 抓取截图

向上滚（历史记录）：
```
python scrape_history.py up
```

向下滚（新消息）：
```
python scrape_history.py down
```

截图保存在 `screenshots/history_YYYYMMDD_HHMMSS/`。

### 3. 拼接长图

```
python stitch.py                    # 拼接，输出带时间戳
python stitch.py calibrate          # 自动检测偏移量
python stitch.py -o mychat.png      # 指定输出文件名
```

输出保存在 `output/`。

## 文件结构

```
release/
├── capture_chat.py      # 校准 + 单张截图
├── scrape_history.py    # 滚动抓取
├── stitch.py            # 纵向拼图
├── config/
│   └── chat_region.json # 校准配置
├── screenshots/         # 截图存放
└── output/              # 拼接输出
```

## 依赖

```
pip install uiautomation pillow opencv-python numpy
```
