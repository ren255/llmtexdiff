"""
Usage:
    python -m app.sample.file_run
"""

import io

import numpy as np
from PIL import Image

from app.db import file_manager as fm

RELATIVE_PATH = "sessions/sample/images/test.png"


def make_png() -> bytes:
    """Generate a simple 64x64 RGB gradient image as PNG bytes."""
    arr = np.zeros((64, 64, 3), dtype=np.uint8)
    arr[:, :, 0] = np.linspace(0, 255, 64, dtype=np.uint8)  # R: 横グラデーション
    arr[:, :, 1] = np.linspace(0, 255, 64, dtype=np.uint8)[
        None
    ].T  # G: 縦グラデーション
    arr[:, :, 2] = 128  # B: 固定

    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    # --- 保存 ---
    print("=== SAVE ===")
    png_bytes = make_png()
    saved_abs = fm.save(RELATIVE_PATH, png_bytes)
    print(f"  Relative : {RELATIVE_PATH}")
    print(f"  Absolute : {saved_abs.resolve()}")
    print(f"  Size     : {len(png_bytes)} bytes")
    print(f"  Exists   : {fm.exists(RELATIVE_PATH)}")

    # --- 取得 ---
    print("\n=== LOAD ===")
    loaded = fm.load(RELATIVE_PATH)
    print(f"  Loaded : {len(loaded)} bytes")
    img = Image.open(io.BytesIO(loaded))
    print(f"  Image  : {img.size} {img.mode}")

    # --- ユーザー確認後に削除 ---
    print("\n=== DELETE ===")
    print("  VSCodeで画像を確認してください。")
    ans = input("  削除しますか？ [y/N]: ").strip().lower()
    if ans == "y":
        fm.delete(RELATIVE_PATH)
        print(f"  Deleted: {RELATIVE_PATH}")
        print(f"  Exists : {fm.exists(RELATIVE_PATH)}")
    else:
        print("  スキップしました。")


if __name__ == "__main__":
    main()
