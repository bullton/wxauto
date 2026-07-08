"""
微信历史聊天记录抓取
支持向上（历史）或向下（新消息）滚动

用法:
  python scrape_history.py up    # 向上滚，抓历史记录
  python scrape_history.py down  # 向下滚，抓新消息
"""
import ctypes
import hashlib
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path

import uiautomation as auto
from PIL import Image, ImageGrab

from capture_chat import (
    CONFIG_FILE,
    OUTPUT_DIR,
    activate_wechat,
    enable_dpi_awareness,
    find_wechat_window,
    get_render_rect,
)


SCROLL_INTERVAL = 0.2
SCROLL_TICKS = 3
MAX_NO_CHANGE = 5
MIN_WIN_SIZE = 200

INPUT_MOUSE = 0
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("mi", MOUSEINPUT),
    ]


def send_mouse_wheel(x, y, ticks):
    """在屏幕坐标 (x, y) 发送滚轮事件。ticks>0 向上，ticks<0 向下"""
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    time.sleep(0.02)
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.mouseData = wintypes.DWORD(ticks * WHEEL_DELTA)
    inp.mi.dwFlags = MOUSEEVENTF_WHEEL
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def img_hash(img):
    thumb = img.resize((16, 16), Image.LANCZOS).convert("L")
    return hashlib.sha256(thumb.tobytes()).hexdigest()[:16]


def click_to_focus(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(0x0002 | 0x0004, 0, 0, 0, 0)
    time.sleep(0.2)


def scrape(direction="up"):
    """direction: 'up' 向上滚（历史），'down' 向下滚（新消息）"""
    enable_dpi_awareness()

    if not CONFIG_FILE.exists():
        print(f"[FAIL] 未找到 {CONFIG_FILE}，请先 calibrate")
        return 1

    ratios = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))["ratios"]

    scroll_dir = 1 if direction == "up" else -1
    print("=" * 60)
    print(f"微信历史聊天记录抓取  [{'向上滚 → 历史' if direction == 'up' else '向下滚 → 新消息'}]")
    print("=" * 60)
    print(f"每次滚动: {SCROLL_TICKS} 格  间隔: {SCROLL_INTERVAL}s  "
          f"停止阈值: 连续 {MAX_NO_CHANGE} 次重复")

    print("\n[1/4] 查找微信窗口...")
    wechat = find_wechat_window(timeout=10)
    if not wechat:
        print("  [FAIL] 未找到微信窗口")
        return 1
    if not activate_wechat(wechat):
        print("  [WARN] 激活窗口失败")

    rr = get_render_rect(wechat)
    if rr.width() < MIN_WIN_SIZE or rr.height() < MIN_WIN_SIZE:
        print("  [FAIL] 微信窗口过小或最小化")
        return 1
    bbox = (
        int(rr.left + ratios[0] * rr.width()),
        int(rr.top + ratios[1] * rr.height()),
        int(rr.left + ratios[2] * rr.width()),
        int(rr.top + ratios[3] * rr.height()),
    )
    cx = (bbox[0] + bbox[2]) // 2
    cy = (bbox[1] + bbox[3]) // 2
    print(f"  [OK] 聊天区: {bbox}  中心: ({cx}, {cy})")

    print("\n[2/4] 点击聊天区获取焦点...")
    click_to_focus(cx, cy)
    print("  [OK]")

    out_dir = OUTPUT_DIR / f"history_{time.strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  输出目录: {out_dir}")

    print("\n[3/4] 开始滚动抓取 (Ctrl+C 停止)...\n")
    last_img = ImageGrab.grab(bbox=bbox, all_screens=True)
    last_hash = img_hash(last_img)
    seen = {last_hash}

    first_path = out_dir / "0000_initial.png"
    last_img.save(first_path)
    print(f"[0000] 初始截图 -> {first_path.name}")

    cycle = 0
    saved = 0
    no_change = 0
    try:
        while True:
            cycle += 1
            send_mouse_wheel(cx, cy, scroll_dir * SCROLL_TICKS)
            time.sleep(SCROLL_INTERVAL)

            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            h = img_hash(img)

            if h == last_hash or h in seen:
                no_change += 1
                print(f"[{cycle:04d}] . 无新内容 ({no_change}/{MAX_NO_CHANGE})")
                if no_change >= MAX_NO_CHANGE:
                    print("\n  [DONE] 滚到顶, 无更多历史消息")
                    break
                continue

            no_change = 0
            ts = time.strftime("%H%M%S")
            path = out_dir / f"{cycle:04d}_{ts}.png"
            img.save(path)
            saved += 1
            seen.add(h)
            last_img = img
            last_hash = h
            print(f"[{cycle:04d}] + 新内容 -> {path.name}")
    except KeyboardInterrupt:
        print("\n\n用户中断")

    print(f"\n[4/4] 汇总")
    print(f"  滚动周期: {cycle}")
    print(f"  新内容截图: {saved} 张")
    print(f"  初始截图: 1 张")
    print(f"  输出目录: {out_dir}")
    return 0


def main():
    direction = sys.argv[1] if len(sys.argv) > 1 else "up"
    if direction not in ("up", "down"):
        print("用法: python scrape_history.py [up|down]")
        return 1
    return scrape(direction)


if __name__ == "__main__":
    sys.exit(main())
