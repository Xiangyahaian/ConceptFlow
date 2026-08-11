"""Project paths and defaults."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BOARDS_FILE = ROOT / "boards.json"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw_fflow"
PACK_FILE = DATA_DIR / "concept_fflow_major.json"
EXAMPLE_PACK = DATA_DIR / "examples" / "concept_fflow_2026-08-10.json"
EXAMPLE_RAW = DATA_DIR / "examples" / "raw_fflow"
EXAMPLE_VIDEO = ROOT / "examples" / "FundFlowOverlay_2026-08-10.mp4"

ASSETS_DIR = ROOT / "assets"
BGM_DIR = ASSETS_DIR / "bgm"
# Legacy single-file path (still supported as fallback)
BGM_FILE = ASSETS_DIR / "bgm.mp3"

OUTPUT_DIR = ROOT / "output"
MEDIA_DIR = ROOT / "media"
SCENES_DIR = ROOT / "scenes"


def output_day_dir(date_str: str) -> Path:
    """Per-day deliverable folder: output/YYYY-MM-DD/"""
    return OUTPUT_DIR / date_str


def video_stem(date_str: str = "", pack: dict | None = None, when: datetime | None = None) -> str:
    """FundFlowOverlay_2026-08-11_124630 — 文件名用产出时的真实日期+时刻（非交易日数据日）."""
    when = when or datetime.now()
    return f"FundFlowOverlay_{when.strftime('%Y-%m-%d_%H%M%S')}"

# Manim portrait render — 竖屏 2K
PIXEL_WIDTH = 1440
PIXEL_HEIGHT = 2560
# 默认 30fps：画面内容不变，渲染帧数约减半（要更丝滑用 run.py --smooth → 60）
FRAME_RATE = int(os.environ.get("FUND_FLOW_FPS", "30"))

def default_cn_font() -> str:
    env = os.environ.get("FUND_FLOW_CN_FONT", "").strip()
    if env:
        return env
    if sys.platform == "darwin":
        return "PingFang SC"
    if sys.platform.startswith("linux"):
        return "Noto Sans CJK SC"
    return "Microsoft YaHei"


# Chinese font — auto by OS; override with FUND_FLOW_CN_FONT
CN_FONT = default_cn_font()

# BGM mix
BGM_VOLUME = 0.55
BGM_FADE_OUT = 1.2

# Expect ~240 one-minute bars for a full A-share session
MIN_POINTS_FULL_DAY = 200
