#!/usr/bin/env python3
"""换 BGM：最常用的是直接覆盖 assets/bgm.mp3。

也可从曲库选用：
  python switch_bgm.py 2
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bgm import (  # noqa: E402
    ACTIVE_BGM,
    LIBRARY_DIR,
    ensure_library,
    print_library,
    resolve_active,
    use_from_library,
)


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", str(path)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def main() -> int:
    ap = argparse.ArgumentParser(description="更换背景音乐")
    ap.add_argument("choice", nargs="?", default="", help="从曲库选：序号或文件名")
    ap.add_argument("--list", "-l", action="store_true", help="只列出")
    ap.add_argument("--open", "-o", action="store_true", help="打开文件夹")
    args = ap.parse_args()

    ensure_library()

    print()
    print("====== 更换 BGM（正常做法）======")
    print("1. 准备好你的 mp3")
    print(f"2. 复制它，覆盖这个文件：")
    print(f"     {ACTIVE_BGM}")
    print("3. 再运行「一键生成」即可")
    print()
    print(f"备选歌可以先丢进：{LIBRARY_DIR}")
    print("================================")
    print()

    if args.open or (not args.choice and not args.list):
        open_folder(ASSETS := ACTIVE_BGM.parent)
        print(f"已打开文件夹：{ASSETS}")
        print("把新歌粘贴进来，改名为 bgm.mp3（覆盖旧的）就行。")
        if args.open and not args.choice:
            return 0

    if args.list or not args.choice:
        print_library()
        try:
            print(f"\n当前实际使用: {resolve_active()}")
        except SystemExit as e:
            print(e)
        if not args.choice:
            return 0

    path = use_from_library(args.choice)
    print(f"已从曲库选用并设为当前：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
