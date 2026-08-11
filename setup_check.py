#!/usr/bin/env python3
"""环境自检：依赖 / FFmpeg / 字体提示。"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    print("ConceptFlow 环境检查")
    print("=" * 40)
    print("Python:", sys.version.split()[0])
    ok = True

    for mod in ("manim", "numpy"):
        try:
            __import__(mod)
            print(f"[OK] {mod}")
        except ImportError:
            print(f"[缺失] {mod}  →  pip install -r requirements.txt")
            ok = False

    for cmd in ("ffmpeg", "ffprobe"):
        path = shutil.which(cmd)
        if path:
            print(f"[OK] {cmd}: {path}")
        else:
            print(f"[缺失] {cmd}  →  安装 FFmpeg 并加入 PATH")
            ok = False

    bgm = ROOT / "assets" / "bgm.mp3"
    boards = ROOT / "boards.json"
    sample = ROOT / "data" / "examples" / "concept_fflow_2026-08-10.json"
    for p, name in ((bgm, "BGM"), (boards, "boards.json"), (sample, "案例数据")):
        print(f"[{'OK' if p.exists() else '缺失'}] {name}: {p}")
        ok = ok and p.exists()

    print("=" * 40)
    if ok:
        print("环境就绪。可运行：")
        print("  python run.py --sample --ql --yes")
        print("  python run.py --yes")
        return 0
    print("请先补齐缺失项后再运行。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
