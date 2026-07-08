"""
微信聊天窗口截图工具 (macOS)
支持校准、向上滚动（历史）、向下滚动（新消息）

用法:
  python capture_chat.py calibrate     # 校准截图区域
  python capture_chat.py capture       # 单张截图
  python scrape_history.py up          # 向上滚动抓历史
  python scrape_history.py down        # 向下滚动抓新消息
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pyscreenshot
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "config" / "chat_region.json"
OUTPUT_DIR = SCRIPT_DIR / "screenshots"


def enable_dpi_awareness():
    pass


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


def get_render_bounds():
    bounds = get_wechat_window_bounds()
    return bounds


def grab_screen_region(bbox):
    x1, y1, x2, y2 = bbox
    img = pyscreenshot.grab(bbox=(x1, y1, x2, y2))
    return img


def cmd_capture():
    print("=" * 60)
    print("微信聊天窗口截图 (macOS)")
    print("=" * 60)

    if not CONFIG_FILE.exists():
        print(f"\n[FAIL] 未找到配置文件 {CONFIG_FILE}")
        print("       请先运行: python capture_chat.py calibrate")
        return 1

    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    ratios = cfg["ratios"]

    print("\n[1/3] 查找微信窗口...")
    bounds = get_render_bounds()
    if not bounds:
        print("  [FAIL] 未找到微信窗口")
        return 1
    print(f"  [OK] 窗口区域: {bounds}")

    print("\n[2/3] 激活窗口...")
    activate_wechat()

    print("\n[3/3] 按比例裁剪截图...")
    left = int(bounds[0] + ratios[0] * (bounds[2] - bounds[0]))
    top = int(bounds[1] + ratios[1] * (bounds[3] - bounds[1]))
    right = int(bounds[0] + ratios[2] * (bounds[2] - bounds[0]))
    bottom = int(bounds[1] + ratios[3] * (bounds[3] - bounds[1]))
    print(f"  截图区域: ({left},{top}) -> ({right},{bottom})  "
          f"size={right-left}x{bottom-top}")

    bbox = (left, top, right, bottom)
    img = grab_screen_region(bbox)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_path = OUTPUT_DIR / f"chat_{time.strftime('%Y%m%d_%H%M%S')}.png"
    img.save(save_path, "PNG")
    print(f"  [OK] 保存: {save_path.resolve()}")
    print(f"  [OK] 尺寸: {img.size[0]} x {img.size[1]}")
    return 0


def cmd_calibrate():
    import tkinter as tk

    print("=" * 60)
    print("校准模式 - 框选聊天消息列表区域 (macOS)")
    print("=" * 60)

    bounds = get_render_bounds()
    if not bounds:
        print("[FAIL] 未找到微信窗口")
        return 1

    activate_wechat()
    print(f"渲染区屏幕坐标: x={bounds[0]} y={bounds[1]} w={bounds[2]-bounds[0]} h={bounds[3]-bounds[1]}")

    bg_img = grab_screen_region(bounds)
    img_w, img_h = bg_img.size
    print(f"截图原尺寸: {img_w} x {img_h}")

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(cursor="crosshair")
    root.title("微信区域校准 - 拖拽框选消息列表, ESC 取消")

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    print(f"屏幕物理尺寸: {screen_w} x {screen_h}")

    fit = bg_img.resize((screen_w, screen_h), Image.LANCZOS)
    from PIL import ImageTk
    tk_img = ImageTk.PhotoImage(fit)

    canvas = tk.Canvas(root, width=screen_w, height=screen_h,
                       highlightthickness=0, bd=0)
    canvas.pack()
    canvas.create_image(0, 0, image=tk_img, anchor="nw")

    overlay = canvas.create_rectangle(0, 0, 0, 0,
                                      outline="#FF1744", width=3, dash=(8, 4))
    hint = canvas.create_text(screen_w // 2, 30,
                              text="拖拽框选「消息列表」区域, 松开确认, ESC 取消",
                              fill="#FF1744", font=("Microsoft YaHei", 18, "bold"))

    state = {"x0": 0, "y0": 0, "x1": 0, "y1": 0}

    def on_press(e):
        state["x0"], state["y0"] = e.x, e.y
        canvas.coords(overlay, e.x, e.y, e.x, e.y)

    def on_drag(e):
        canvas.coords(overlay, state["x0"], state["y0"], e.x, e.y)

    def on_release(e):
        state["x1"], state["y1"] = e.x, e.y
        root.quit()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", lambda e: root.destroy())

    print("\n请在屏幕上拖拽框选「聊天消息列表」区域...")
    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass

    if state["x1"] == 0 and state["y1"] == 0:
        print("[FAIL] 未框选区域, 取消")
        return 1

    sx0, sy0, sx1, sy1 = state["x0"], state["y0"], state["x1"], state["y1"]
    if sx1 < sx0:
        sx0, sx1 = sx1, sx0
    if sy1 < sy0:
        sy0, sy1 = sy1, sy0

    scale_x = img_w / screen_w
    scale_y = img_h / screen_h
    ox0, oy0, ox1, oy1 = (sx0 * scale_x, sy0 * scale_y,
                          sx1 * scale_x, sy1 * scale_y)

    ratios = [ox0 / img_w, oy0 / img_h, ox1 / img_w, oy1 / img_h]

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    else:
        cfg = {}
    cfg["ratios"] = ratios
    cfg["screen_size"] = [img_w, img_h]
    cfg["description"] = "left/top/right/bottom 相对微信渲染窗口的比例 (0~1)"
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    print(f"\n[OK] 已保存校准到 {CONFIG_FILE.resolve()}")
    print(f"     比例: L={ratios[0]:.4f}  T={ratios[1]:.4f}  "
          f"R={ratios[2]:.4f}  B={ratios[3]:.4f}")
    print(f"     原图坐标: ({int(ox0)},{int(oy0)}) -> ({int(ox1)},{int(oy1)})")
    print(f"\n下一步: python scrape_history.py up  (或 down)")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "capture"
    if cmd == "calibrate":
        return cmd_calibrate()
    if cmd == "capture":
        return cmd_capture()
    print(f"未知命令: {cmd}\n用法: python capture_chat.py [capture|calibrate]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
