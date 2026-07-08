"""
WeChat Screenshot Stitcher
将微信聊天截图纵向拼合为长图

用法:
  python stitch.py                    # 拼接最新截图
  python stitch.py calibrate          # 自动检测偏移量
  python stitch.py -o mychat.png      # 指定输出文件名
  python stitch.py -m 50              # 每张长图最多50张截图
"""
import argparse
import sys
import cv2
import numpy as np
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_paths import CHAT_REGION_FILE, SCREENSHOT_DIR, OUTPUT_DIR

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CHAT_REGION_FILE
SCREENSHOT_DIR = SCREENSHOT_DIR
OUTPUT_DIR = OUTPUT_DIR


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"未找到配置文件 {CONFIG_FILE}，请先运行: python capture_chat.py calibrate"
        )
    import json
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def stitch_all(imgs, dy, direction="up"):
    """纵向拼接所有截图。"""
    H, W = imgs[0].shape[:2]
    overlap = abs(dy)
    total_h = H + (len(imgs) - 1) * overlap
    canvas = np.full((total_h, W, 3), 255, dtype=np.uint8)
    if direction == "down":
        for i, img in enumerate(imgs):
            y = i * overlap
            canvas[y:y+H] = img
    else:
        for i, img in enumerate(reversed(imgs)):
            y = i * overlap
            canvas[y:y+H] = img
    return canvas


def calibrate():
    """自动检测偏移量 dy"""
    import json

    dirs = sorted(
        [d for d in OUTPUT_DIR.iterdir()
         if d.is_dir() and d.name.startswith("history_")],
        reverse=True
    )
    if not dirs:
        print("未找到截图目录，请先运行 scrape_history.py")
        return

    latest_dir = dirs[0]
    print(f"使用: {latest_dir.name}")
    files = sorted(
        [f for f in latest_dir.glob("*.png") if f.stem.split("_")[0].isdigit()],
        key=lambda p: int(p.stem.split("_")[0])
    )
    if len(files) < 2:
        print("截图不足2张")
        return

    imgs = [cv2.imread(str(f)) for f in files]

    def orb_dy(a, b):
        orb = cv2.ORB_create(2000)
        kpA, desA = orb.detectAndCompute(a, None)
        kpB, desB = orb.detectAndCompute(b, None)
        if desA is None or desB is None or len(desA) < 20 or len(desB) < 20:
            return None
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(desA, desB)
        if len(matches) < 20:
            return None
        ptsA = np.float32([kpA[m.queryIdx].pt for m in matches])
        ptsB = np.float32([kpB[m.trainIdx].pt for m in matches])
        return int(np.median(ptsB[:, 1] - ptsA[:, 1]))

    dys = []
    for i in range(min(10, len(imgs) - 1)):
        dy = orb_dy(imgs[i], imgs[i + 1])
        if dy is not None:
            dys.append(dy)
            print(f"  {files[i].name} -> {files[i+1].name}: dy={dy}")

    if not dys:
        print("无法计算偏移量")
        return

    from collections import Counter
    dy_common = Counter(dys).most_common(1)[0][0]
    print(f"\n偏移量: dy={dy_common}px")

    cfg = load_config()
    cfg["stitch_dy"] = dy_common
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {CONFIG_FILE}")


def stitch(output_name=None, max_images=50):
    """拼接截图
    Args:
        output_name: 输出文件名（不含序号）
        max_images: 每张长图最多包含的截图数量
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    dy = cfg.get("stitch_dy", 74)

    dirs = sorted(
        [d for d in OUTPUT_DIR.iterdir()
         if d.is_dir() and d.name.startswith("history_")],
        reverse=True
    )
    if not dirs:
        print("未找到截图目录，请先运行 scrape_history.py")
        return

    target_dir = dirs[0]
    files = sorted(
        [f for f in target_dir.glob("*.png") if f.stem.split("_")[0].isdigit()],
        key=lambda p: int(p.stem.split("_")[0])
    )

    # 跳过最后一张（到顶或内容不同的那张）
    n_before = len(files)
    files = [f for f in files if f.stem.split("_")[0] != "0050"]
    n_after = len(files)
    if n_after < n_before:
        print(f"跳过 0050，使用 {n_after} 张")

    print(f"共 {len(files)} 张，偏移 dy={dy}px，每张长图最多 {max_images} 张")

    direction = cfg.get("scrape_direction", "up")

    # 分批处理
    batch_count = (len(files) + max_images - 1) // max_images
    saved_paths = []

    for batch_idx in range(batch_count):
        start = batch_idx * max_images
        end = min(start + max_images, len(files))
        batch_files = files[start:end]

        imgs = [cv2.imread(str(f)) for f in batch_files]
        canvas = stitch_all(imgs, dy, direction)

        if batch_count == 1:
            # 只有一张长图
            name = output_name or f"chat_stitched_{time.strftime('%Y%m%d_%H%M%S')}.png"
        else:
            # 多张长图，加序号
            if output_name:
                name = f"{Path(output_name).stem}_{batch_idx+1}{Path(output_name).suffix}"
            else:
                name = f"chat_stitched_{time.strftime('%Y%m%d_%H%M%S')}_{batch_idx+1}.png"

        out_path = OUTPUT_DIR / name
        cv2.imwrite(str(out_path), canvas)
        saved_paths.append(out_path)
        print(f"已保存: {out_path}  ({canvas.shape[1]}x{canvas.shape[0]}, {len(batch_files)} 张)")

    if len(saved_paths) > 1:
        print(f"\n共生成 {len(saved_paths)} 张长图")


def main():
    parser = argparse.ArgumentParser(description="微信聊天截图拼接工具")
    parser.add_argument("cmd", nargs="?", default="stitch",
                        choices=["calibrate", "stitch"])
    parser.add_argument("-o", "--output", help="输出文件名（默认带时间戳）")
    parser.add_argument("-m", "--max-images", type=int, default=50,
                        help="每张长图最多包含的截图数量（默认50）")
    args = parser.parse_args()

    if args.cmd == "calibrate":
        calibrate()
    else:
        stitch(args.output, args.max_images)


if __name__ == "__main__":
    main()
