"""
微信聊天窗口截图工具
支持校准、向上滚动（历史）、向下滚动（新消息）

用法:
  python capture_chat.py calibrate     # 校准截图区域
  python capture_chat.py capture       # 单张截图
  python scrape_history.py up          # 向上滚动抓历史
  python scrape_history.py down        # 向下滚动抓新消息
"""
import ctypes
import json
import sys
import time
from pathlib import Path

import uiautomation as auto
from PIL import Image, ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_paths import CONFIG_DIR, CHAT_REGION_FILE, OUTPUT_DIR as RUNTIME_OUTPUT_DIR


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CHAT_REGION_FILE
OUTPUT_DIR = RUNTIME_OUTPUT_DIR
RENDER_CLASSNAME = "MMUIRenderSubWindowHW"
WECHAT_CLASSNAMES = ("Qt51514QWindowIcon", "WeChatMainWndForPC", "WeChat")


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def find_wechat_window(timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for cls in WECHAT_CLASSNAMES:
            win = auto.WindowControl(searchDepth=1, ClassName=cls)
            if win.Exists(maxSearchSeconds=0.3):
                return win
        try:
            root = auto.GetRootControl()
            for top in root.GetChildren():
                try:
                    name = top.Name or ""
                    cls = top.ClassName or ""
                    if "微信" in name or "WeChat" in name or any(h in cls for h in WECHAT_CLASSNAMES):
                        return top
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(0.5)
    return None


def find_render_window(wechat):
    for c in wechat.GetChildren():
        try:
            if (c.ClassName or "") == RENDER_CLASSNAME:
                return c
        except Exception:
            continue
    return None


def activate_wechat(wechat):
    hwnd = wechat.NativeWindowHandle
    if not hwnd:
        return False
    try:
        minimized = bool(wechat.IsMinimize())
    except Exception:
        minimized = False
    if minimized:
        auto.ShowWindow(hwnd, auto.SW.Restore)
    else:
        auto.ShowWindow(hwnd, auto.SW.ShowNormal)
    time.sleep(0.6)
    try:
        auto.SwitchToThisWindow(hwnd)
    except Exception:
        pass
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    return True


def get_render_rect(wechat):
    render = find_render_window(wechat)
    if render:
        r = render.BoundingRectangle
        if r.width() > 100 and r.height() > 100:
            return r
    r = wechat.BoundingRectangle
    return r


def cmd_capture():
    print("=" * 60)
    print("微信聊天窗口截图")
    print("=" * 60)

    if not CONFIG_FILE.exists():
        print(f"\n[FAIL] 未找到配置文件 {CONFIG_FILE}")
        print("       请先运行: python capture_chat.py calibrate")
        return 1

    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    ratios = cfg["ratios"]

    print("\n[1/3] 查找微信窗口...")
    wechat = find_wechat_window(timeout=10)
    if not wechat:
        print("  [FAIL] 未找到微信窗口")
        return 1
    print(f"  [OK] 命中: {wechat.ClassName}")

    print("\n[2/3] 激活窗口...")
    if not activate_wechat(wechat):
        print("  [WARN] 激活窗口失败")

    rr = get_render_rect(wechat)
    print(f"  [OK] 渲染区: x={rr.left} y={rr.top} w={rr.width()} h={rr.height()}")

    print("\n[3/3] 按比例裁剪截图...")
    left = int(rr.left + ratios[0] * rr.width())
    top = int(rr.top + ratios[1] * rr.height())
    right = int(rr.left + ratios[2] * rr.width())
    bottom = int(rr.top + ratios[3] * rr.height())
    print(f"  截图区域: ({left},{top}) -> ({right},{bottom})  "
          f"size={right-left}x{bottom-top}")

    bbox = (left, top, right, bottom)
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_path = OUTPUT_DIR / f"chat_{time.strftime('%Y%m%d_%H%M%S')}.png"
    img.save(save_path, "PNG")
    print(f"  [OK] 保存: {save_path.resolve()}")
    print(f"  [OK] 尺寸: {img.size[0]} x {img.size[1]}")
    return 0


def cmd_calibrate(tk_parent=None):
    import tkinter as tk

    print("=" * 60)
    print("校准模式 - 框选聊天消息列表区域")
    print("=" * 60)

    wechat = find_wechat_window(timeout=10)
    if not wechat:
        print("[FAIL] 未找到微信窗口")
        return 1

    if not activate_wechat(wechat):
        print("[WARN] 激活窗口失败, 请手动激活微信窗口")

    rr = get_render_rect(wechat)
    print(f"渲染区屏幕坐标: x={rr.left} y={rr.top} w={rr.width()} h={rr.height()}")

    bbox = (rr.left, rr.top, rr.right, rr.bottom)
    bg_img = ImageGrab.grab(bbox=bbox, all_screens=True)
    img_w, img_h = bg_img.size
    print(f"截图原尺寸: {img_w} x {img_h}")

    if tk_parent:
        root = tk.Toplevel(tk_parent)
    else:
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
    enable_dpi_awareness()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "capture"
    if cmd == "calibrate":
        return cmd_calibrate()
    if cmd == "capture":
        return cmd_capture()
    print(f"未知命令: {cmd}\n用法: python capture_chat.py [capture|calibrate]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
