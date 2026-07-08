"""
微信聊天截图工具 - 图形界面
"""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import threading
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from runtime_paths import SCREENSHOT_DIR, OUTPUT_DIR, CHAT_REGION_FILE, RUNTIME_DIR

ERROR_LOG = RUNTIME_DIR / "gui_error.log"


class WeChatScreenshotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("微信聊天截图工具 v1.3")
        self.root.geometry("560x720")
        self.root.minsize(520, 600)
        self.root.resizable(True, True)

        self.screenshot_dir = None
        self.status_text = tk.StringVar(value="就绪")
        self.calibrating = False

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main_frame, text="微信聊天截图工具", font=("Microsoft YaHei", 14, "bold"))
        title.pack(pady=(0, 15))

        frame1 = ttk.LabelFrame(main_frame, text="步骤1: 校正窗口", padding="8")
        frame1.pack(fill=tk.X, pady=5)
        ttk.Label(frame1, text="框选聊天消息列表区域（不含标题栏）").pack(anchor=tk.W)
        ttk.Button(frame1, text="校正窗口", command=self.calibrate_window).pack(anchor=tk.W, pady=3)

        frame2 = ttk.LabelFrame(main_frame, text="步骤2: 截图（完成自动拼图）", padding="8")
        frame2.pack(fill=tk.X, pady=5)

        opt_frame = ttk.Frame(frame2)
        opt_frame.pack(fill=tk.X)
        ttk.Label(opt_frame, text="截止时间:").pack(side=tk.LEFT)
        self.stop_option = tk.StringVar(value="yesterday")
        ttk.Radiobutton(opt_frame, text="昨天0点", variable=self.stop_option, value="yesterday").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(opt_frame, text="自定义", variable=self.stop_option, value="custom").pack(side=tk.LEFT)

        custom_frame = ttk.Frame(frame2)
        custom_frame.pack(fill=tk.X, pady=5)
        ttk.Label(custom_frame, text="日期:").pack(side=tk.LEFT)
        self.custom_date = tk.StringVar(value=time.strftime("%Y-%m-%d"))
        ttk.Entry(custom_frame, textvariable=self.custom_date, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Label(custom_frame, text="时间:").pack(side=tk.LEFT, padx=(10, 0))
        self.custom_time = tk.StringVar(value="00:00")
        ttk.Entry(custom_frame, textvariable=self.custom_time, width=8).pack(side=tk.LEFT, padx=5)

        stitch_opt = ttk.Frame(frame2)
        stitch_opt.pack(fill=tk.X, pady=5)
        ttk.Label(stitch_opt, text="每张长图:").pack(side=tk.LEFT)
        self.max_images = tk.IntVar(value=30)
        ttk.Spinbox(stitch_opt, from_=10, to=100, textvariable=self.max_images, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(stitch_opt, text="张截图（拼接数量）").pack(side=tk.LEFT)

        btn_frame = ttk.Frame(frame2)
        btn_frame.pack(fill=tk.X, pady=3)
        ttk.Button(btn_frame, text="开始截图 (含校准+拼图)", command=self.start_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="仅拼图", command=self.stitch_images).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="校准偏移量", command=self.calibrate_offset).pack(side=tk.LEFT)

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=10)
        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_text, foreground="blue").pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)

        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(log_frame, text="日志:").pack(anchor=tk.W)
        scroll = ttk.Scrollbar(log_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text = tk.Text(log_frame, height=15, state=tk.DISABLED, font=("Consolas", 8), yscrollcommand=scroll.set)
        self.log_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.log_text.yview)

    def log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()

    def run_in_thread(self, func, *args):
        def wrapper():
            try:
                func(*args)
            except Exception:
                traceback.print_exc()
        t = threading.Thread(target=wrapper, daemon=True)
        t.start()
        return t

    def calibrate_window(self):
        if self.calibrating:
            return
        self.calibrating = True
        self.status_text.set("校正窗口中...")
        self.log("请在新窗口中框选聊天消息列表区域...")
        self.root.withdraw()
        self.root.update()

        import subprocess
        result = subprocess.run(
            [sys.executable, "--calibrate"],
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )

        self.root.deiconify()
        self.calibrating = False
        if result.returncode == 0:
            self.status_text.set("校正完成")
            self.log("校正完成")
        elif result.returncode == 1:
            self.status_text.set("校正取消")
            self.log("校正已取消")
        else:
            self.status_text.set(f"错误 (code={result.returncode})")
            self.log(f"校正失败，代码: {result.returncode}")

    def start_screenshot(self):
        from datetime import datetime, timedelta

        stop_option = self.stop_option.get()
        if stop_option == "yesterday":
            stop_datetime = datetime.combine(
                (datetime.now() - timedelta(days=1)).date(),
                datetime.min.time()
            )
            stop_desc = "昨天0点"
        else:
            date_str = self.custom_date.get()
            time_str = self.custom_time.get()
            try:
                stop_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                stop_desc = f"{date_str} {time_str}"
            except ValueError:
                messagebox.showerror("错误", "日期或时间格式不正确")
                return

        max_imgs = self.max_images.get()
        self.status_text.set(f"截图到{stop_desc}停止...")
        self.log(f"开始截图，截止时间: {stop_desc}")
        self.progress.start(10)

        def do_workflow():
            try:
                import io
                import contextlib
                log_buf = io.StringIO()
                with contextlib.redirect_stdout(log_buf), contextlib.redirect_stderr(log_buf):
                    import scrape_history
                    scrape_history.scrape(direction="up", stop_datetime=stop_datetime)

                output = log_buf.getvalue()
                RUNTIME_DIR.joinpath("scrape.log").write_text(output, encoding="utf-8")

                dirs = sorted([d for d in OUTPUT_DIR.iterdir() if d.is_dir() and d.name.startswith("history_")], reverse=True)
                if dirs:
                    self.screenshot_dir = dirs[0]

                self.root.after(0, lambda: self.log(f"✓ 截图完成: {self.screenshot_dir}"))

                self.root.after(0, lambda: self.status_text.set("校准偏移量中..."))
                import stitch
                stitch.calibrate()
                self.root.after(0, lambda: self.log("✓ 偏移量校准完成"))

                self.root.after(0, lambda: self.status_text.set(f"拼接中（每张{max_imgs}张）..."))
                stitch.stitch(output_name=None, max_images=max_imgs)
                files = list(OUTPUT_DIR.glob("*.png"))
                latest = sorted(files)[-1] if files else None

                self.root.after(0, lambda: self.progress.stop())
                self.root.after(0, lambda: self.status_text.set("完成"))
                self.root.after(0, lambda: self.log(f"✓ 拼接完成: {OUTPUT_DIR}"))
                if latest:
                    self.root.after(0, lambda: self.log(f"最新文件: {latest.name}"))

            except Exception as e:
                self.root.after(0, lambda: self.progress.stop())
                err = traceback.format_exc()
                err_full = err + "\n\n=== scrape_history 输出 ===\n" + log_buf.getvalue()
                ERROR_LOG.write_text(err_full, encoding="utf-8")
                self.root.after(0, lambda: self.status_text.set(f"错误: {e}"))
                self.root.after(0, lambda: self.log(f"错误: {e}"))
                self.root.after(0, lambda: self.log(f"详情已写入: {ERROR_LOG}"))

        self.run_in_thread(do_workflow)

    def calibrate_offset(self):
        self.status_text.set("校准偏移量中...")
        self.log("正在校准偏移量...")
        self.progress.start(10)

        def do_calibrate():
            try:
                import stitch
                stitch.calibrate()
                self.root.after(0, lambda: self.progress.stop())
                self.root.after(0, lambda: self.status_text.set("校准完成"))
                self.root.after(0, lambda: self.log("校准完成，偏移量已保存"))
            except Exception as e:
                self.root.after(0, lambda: self.progress.stop())
                err = traceback.format_exc()
                ERROR_LOG.write_text(err, encoding="utf-8")
                self.root.after(0, lambda: self.status_text.set(f"错误: {e}"))
                self.root.after(0, lambda: self.log(f"错误: {e}"))
                self.root.after(0, lambda: self.log(f"详情已写入: {ERROR_LOG}"))

        self.run_in_thread(do_calibrate)

    def stitch_images(self):
        max_imgs = self.max_images.get()
        self.status_text.set(f"拼接中（每张{max_imgs}张）...")
        self.log(f"开始拼接，每张长图{max_imgs}张...")
        self.progress.start(10)

        def do_stitch():
            try:
                import stitch
                stitch.stitch(output_name=None, max_images=max_imgs)
                files = list(OUTPUT_DIR.glob("*.png"))
                latest = sorted(files)[-1] if files else None

                self.root.after(0, lambda: self.progress.stop())
                self.root.after(0, lambda: self.status_text.set("拼接完成"))
                self.root.after(0, lambda: self.log(f"拼接完成: {OUTPUT_DIR}"))
                if latest:
                    self.root.after(0, lambda: self.log(f"最新文件: {latest.name}"))
            except Exception as e:
                self.root.after(0, lambda: self.progress.stop())
                err = traceback.format_exc()
                ERROR_LOG.write_text(err, encoding="utf-8")
                self.root.after(0, lambda: self.status_text.set(f"错误: {e}"))
                self.root.after(0, lambda: self.log(f"错误: {e}"))
                self.root.after(0, lambda: self.log(f"详情已写入: {ERROR_LOG}"))

        self.run_in_thread(do_stitch)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--calibrate":
        from capture_chat import cmd_calibrate as _cmd_calibrate
        sys.exit(_cmd_calibrate())

    root = tk.Tk()
    app = WeChatScreenshotGUI(root)
    root.mainloop()
