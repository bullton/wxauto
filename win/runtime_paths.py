"""
运行时路径工具 - 统一从 exe 所在目录定位文件
"""
import sys
from pathlib import Path


def get_runtime_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


RUNTIME_DIR = get_runtime_dir()
SCREENSHOT_DIR = RUNTIME_DIR / "screenshots"
OUTPUT_DIR = RUNTIME_DIR / "output"
CONFIG_DIR = RUNTIME_DIR / "config"
CHAT_REGION_FILE = CONFIG_DIR / "chat_region.json"
OFFSET_FILE = CONFIG_DIR / "offset.json"

for d in (SCREENSHOT_DIR, OUTPUT_DIR, CONFIG_DIR):
    d.mkdir(parents=True, exist_ok=True)
