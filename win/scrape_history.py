"""
微信历史聊天记录抓取
支持向上（历史）或向下（新消息）滚动
支持按日期停止（截取到指定日期0点）

用法:
  python scrape_history.py up              # 向上滚，抓历史记录
  python scrape_history.py up --yesterday  # 向上滚，截取到昨天0点停止
  python scrape_history.py down            # 向下滚，抓新消息
"""
import ctypes
import hashlib
import json
import re
import sys
import threading
import time
from ctypes import wintypes
from datetime import datetime, timedelta, time as dt_time
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

try:
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream
    HAS_WINRT = True
except ImportError:
    HAS_WINRT = False


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


_ocr_result = None
_ocr_lock = threading.Lock()

def ocr_image(img):
    """使用 Windows.Media.Ocr 识别图片中的文字（在后台线程执行）"""
    global _ocr_result
    if not HAS_WINRT:
        return None

    import io
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes = img_bytes.getvalue()

    def _do_ocr():
        global _ocr_result
        try:
            mem_stream = InMemoryRandomAccessStream()
            writer = DataWriter(mem_stream)
            writer.write_bytes(img_bytes)
            writer.store_async().get()

            decoder = BitmapDecoder.create_async(mem_stream).get()
            frame = decoder.get_frame_async(0).get()
            bitmap = frame.get_software_bitmap_async().get()

            try:
                from winrt.windows.globalization import Language
                zh_lang = Language('zh-Hans-CN')
                engine = OcrEngine.try_create_from_language(zh_lang)
            except Exception:
                engine = OcrEngine.try_create_from_user_profile_languages()
            if engine is None:
                _ocr_result = None
                return

            result = engine.recognize_async(bitmap).get()
            _ocr_result = result.text if result else None
        except Exception as e:
            _ocr_result = None

    t = threading.Thread(target=_do_ocr)
    t.start()
    t.join(timeout=5.0)
    return _ocr_result


def parse_wechat_timestamp(text):
    """解析微信时间戳文本，返回 datetime 或 None

    支持格式:
    - 2023年12月15日 上午 10:30
    - 12月15日 上午 10:30
    - 昨天 / 昨天 23:12
    - 星期一 19:30 (根据当前星期几推断实际日期)
    - 上午 10:30 / 下午 3:45
    - 19:30 (视为今天)
    """
    now = datetime.now()
    today = now.date()
    current_weekday = today.weekday()

    text = text.replace('：', ':').replace(' ', '')

    weekday_map = {'星期一': 0, '星期二': 1, '星期三': 2, '星期四': 3, '星期五': 4, '星期六': 5, '星期日': 6}

    if '昨天' in text:
        yesterday = today - timedelta(days=1)
        m = re.search(r'昨天\D*?(\d{1,2})\D*?(\d{1,2})', text)
        if m:
            h, mi = int(m[1]), int(m[2])
            if h < 24 and mi < 60:
                return datetime.combine(yesterday, dt_time(h, mi))
        return datetime.combine(yesterday, datetime.min.time())

    patterns = [
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日", lambda m: datetime(int(m[0]), int(m[1]), int(m[2])).date()),
        (r"(\d{1,2})月(\d{1,2})日", lambda m: datetime(now.year, int(m[0]), int(m[1])).date()),
    ]

    date_result = None

    for pattern, parser in patterns:
        m = re.search(pattern, text)
        if m:
            try:
                result = parser(m.groups())
                if result is not None:
                    date_result = result
                    break
            except Exception:
                continue

    week_match = re.search(r"星期[一二三四五六日]", text)
    if week_match and date_result is None:
        weekday_name = week_match.group(0)
        target_weekday = weekday_map.get(weekday_name)
        if target_weekday is not None:
            days_diff = (current_weekday - target_weekday) % 7
            date_result = today - timedelta(days=days_diff)

    if date_result is None:
        date_result = today

    time_patterns = [
        (r"上午\s*(\d{1,2}):(\d{2})", lambda m: (int(m[0]), int(m[1]))),
        (r"下午\s*(\d{1,2}):(\d{2})", lambda m: (int(m[0]) + 12 if int(m[0]) < 12 else int(m[0]), int(m[1]))),
        (r"(\d{1,2}):(\d{2})", lambda m: (int(m[0]), int(m[1]))),
    ]

    time_result = None
    for pattern, parser in time_patterns:
        m = re.search(pattern, text)
        if m:
            try:
                h, mi = parser(m.groups())
                if 0 <= h <= 23 and 0 <= mi <= 59:
                    time_result = (h, mi)
                    break
            except Exception:
                continue

    if time_result is None:
        return None

    return datetime.combine(date_result, datetime.min.time().replace(hour=time_result[0], minute=time_result[1]))


def is_reached_target_date(ocr_text, stop_datetime):
    """判断 OCR 文本中的时间戳是否已达到截止时间

    Args:
        ocr_text: OCR 识别的文本
        stop_datetime: 截止时间（datetime 对象）

    Returns:
        True 如果已到达截止时间（即时间戳早于或等于截止时间）
        False 如果尚未到达
        None 如果无法解析时间戳
    """
    if not ocr_text:
        return None

    ts = parse_wechat_timestamp(ocr_text)
    if ts is None:
        return None

    return ts <= stop_datetime


def click_to_focus(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(0x0002 | 0x0004, 0, 0, 0, 0)
    time.sleep(0.2)


def safe_click_top_area(bbox):
    """点击聊天区右侧靠上位置（避开中部可能的图片/小程序）"""
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    click_x = bbox[2] - width // 6
    click_y = bbox[1] + height // 6
    click_to_focus(click_x, click_y)


def scrape(direction="up", stop_datetime=None):
    """direction: 'up' 向上滚（历史），'down' 向下滚（新消息）
       stop_datetime: 截止时间（datetime 对象），到达该时间时停止抓取
    """
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

    print("\n[2/4] 点击聊天区顶部获取焦点（避开图片/小程序）...")
    safe_click_top_area(bbox)
    print("  [OK]")

    out_dir = OUTPUT_DIR / f"history_{time.strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  输出目录: {out_dir}")

    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    config["scrape_direction"] = direction
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    stop_info = ""
    if stop_datetime:
        stop_info = f"  截止时间: {stop_datetime}"
        print(f"[INFO] 将检测时间戳，到达 {stop_datetime} 时停止")

    print(f"\n[3/4] 开始滚动抓取 (Ctrl+C 停止){stop_info}...\n")
    last_img = ImageGrab.grab(bbox=bbox, all_screens=True)
    last_hash = img_hash(last_img)
    seen = {last_hash}

    first_path = out_dir / "0000_initial.png"
    last_img.save(first_path)
    print(f"[0000] 初始截图 -> {first_path.name}")

    cycle = 0
    saved = 0
    no_change = 0
    date_reached = False
    try:
        while True:
            cycle += 1
            send_mouse_wheel(cx, cy, scroll_dir * SCROLL_TICKS)
            time.sleep(SCROLL_INTERVAL)

            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            h = img_hash(img)

            if stop_datetime and (h != last_hash and h not in seen):
                try:
                    ocr_text = ocr_image(img)
                    ts_parsed = parse_wechat_timestamp(ocr_text) if ocr_text else None
                    reached = is_reached_target_date(ocr_text, stop_datetime)
                    print(f"  [OCR] {repr(ocr_text)[:120] if ocr_text else None} -> ts={ts_parsed}, reached={reached}")
                    if reached is True:
                        ts = time.strftime("%H%M%S")
                        path = out_dir / f"{cycle:04d}_{ts}.png"
                        img.save(path)
                        saved += 1
                        seen.add(h)
                        last_img = img
                        last_hash = h
                        date_reached = True
                        print(f"\n[{cycle:04d}] + 到达 {stop_datetime} -> {path.name}")
                        print(f"\n  [DONE] 已到达 {stop_datetime}，停止截取")
                        break
                except Exception:
                    pass

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
    direction = "up"
    stop_datetime = None

    for arg in sys.argv[1:]:
        if arg in ("up", "down"):
            direction = arg
        elif arg == "--yesterday":
            stop_datetime = datetime.combine(
                (datetime.now() - timedelta(days=1)).date(),
                datetime.min.time()
            )
        elif arg.startswith("--stop="):
            date_str = arg.split("=", 1)[1]
            try:
                stop_datetime = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                try:
                    stop_datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    print(f"[ERROR] 无效的日期格式: {date_str}")
                    print("用法: python scrape_history.py [up|down] [--yesterday] [--stop=YYYY-MM-DD] [--stop=YYYY-MM-DD HH:MM]")
                    return 1
        elif arg.startswith("--date="):
            date_str = arg.split("=", 1)[1]
            try:
                stop_datetime = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                print(f"[ERROR] 无效的日期格式: {date_str}")
                print("用法: python scrape_history.py [up|down] [--yesterday] [--date=YYYY-MM-DD]")
                return 1

    if direction not in ("up", "down"):
        print("用法: python scrape_history.py [up|down] [--yesterday] [--stop=YYYY-MM-DD] [--stop=YYYY-MM-DD HH:MM]")
        return 1

    if stop_datetime:
        print(f"[INFO] 将截取到 {stop_datetime} 停止")
    return scrape(direction, stop_datetime=stop_datetime)


if __name__ == "__main__":
    sys.exit(main())
