"""
微信历史聊天记录抓取 (macOS)
支持向上（历史）或向下（新消息）滚动

用法:
  python scrape_history.py up    # 向上滚，抓历史记录
  python scrape_history.py down  # 向下滚，抓新消息
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pyautogui
import pyscreenshot
from PIL import Image, ImageGrab


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "config" / "chat_region.json"
OUTPUT_DIR = SCRIPT_DIR / "screenshots"

SCROLL_INTERVAL = 0.2
SCROLL_TICKS = 3
MAX_NO_CHANGE = 5
MIN_WIN_SIZE = 200


def img_hash(img):
    thumb = img.resize((16, 16), Image.LANCZOS).convert("L")
    return hashlib.sha256(thumb.tobytes()).hex[:16]


def click_to_focus(x, y):
    pyautogui.click(x, y)
    time.sleep(0.2)


def get_wechat_window_bounds():
    script = '''
    tell application "System Events"
        tell process "WeChat"
            if exists window 1 of it then
                set windowBounds to bounding rectangle of window 1
                return item 1 of windowBounds & "," & item 2 of windowBounds & "," & item 3 of windowBounds & "," & item 4 of windowBounds
            end if
        end tell
    end tell
    return ""
    '''
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    output = result.stdout.strip()
    if output and output != "":
        parts = output.split(",")
        if len(parts) == 4:
            return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    return None


def activate_wechat():
    script = '''
    tell application "WeChat"
        activate
    end tell
    '''
    subprocess.run(['osascript', '-e', script])
    time.sleep(0.5)


def grab_screen_region(bbox):
    x1, y1, x2, y2 = bbox
    img = pyscreenshot.grab(bbox=(x1, y1, x2, y2))
    return img


def scrape(direction="up"):
    """direction: 'up' 向上滚（历史），'down' 向下滚（新消息）"""

    if not CONFIG_FILE.exists():
        print(f"[FAIL] 未找到 {CONFIG_FILE}，请先 calibrate")
        return 1

    ratios = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))["ratios"]

    scroll_dir = 1 if direction == "up" else -1
    print("=" * 60)
    print(f"微信历史聊天记录抓取 (macOS)  [{'向上滚 → 历史' if direction == 'up' else '向下滚 → 新消息'}]")
    print("=" * 60)
    print(f"每次滚动: {SCROLL_TICKS} 格  间隔: {SCROLL_INTERVAL}s  "
          f"停止阈值: 连续 {MAX_NO_CHANGE} 次重复")

    print("\n[1/4] 查找微信窗口...")
    bounds = get_wechat_window_bounds()
    if not bounds:
        print("  [FAIL] 未找到微信窗口")
        return 1
    activate_wechat()

    if (bounds[2] - bounds[0]) < MIN_WIN_SIZE or (bounds[3] - bounds[1]) < MIN_WIN_SIZE:
        print("  [FAIL] 微信窗口过小或最小化")
        return 1
    bbox = (
        int(bounds[0] + ratios[0] * (bounds[2] - bounds[0])),
        int(bounds[1] + ratios[1] * (bounds[3] - bounds[1])),
        int(bounds[0] + ratios[2] * (bounds[2] - bounds[0])),
        int(bounds[1] + ratios[3] * (bounds[3] - bounds[1])),
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

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    config["scrape_direction"] = direction
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n[3/4] 开始滚动抓取 (Ctrl+C 停止)...\n")
    last_img = grab_screen_region(bbox)
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
            pyautogui.scroll(scroll_dir * SCROLL_TICKS * 120, x=cx, y=cy)
            time.sleep(SCROLL_INTERVAL)

            img = grab_screen_region(bbox)
            h = img_hash(img)

            if h == last_hash or h in seen:
                no_change += 1
                print(f"[{cycle:04d}] . 无新内容 ({no_change}/{MAX_NO_CHANGE})")
                if no_change >= MAX_NO_CHANGE:
                    msg = "滚到顶" if direction == "up" else "滚到底"
                    print(f"\n  [DONE] {msg}, 无更多消息")
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
