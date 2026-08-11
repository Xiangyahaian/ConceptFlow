#!/usr/bin/env python3
"""一键生成「概念板块主力资金流向」竖屏视频。

用法（在本目录下）:
  python run.py              # 拉取最新数据 → 渲染 → 配乐
  python run.py --sample     # 不联网，用内置 2026-08-10 案例数据
  python run.py --yes        # 非今日数据时不询问，直接继续
  python run.py --ql         # 低清预览（更快）
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    BGM_FADE_OUT,
    BGM_VOLUME,
    BOARDS_FILE,
    EXAMPLE_PACK,
    EXAMPLE_RAW,
    EXAMPLE_VIDEO,
    FRAME_RATE,
    MEDIA_DIR,
    MIN_POINTS_FULL_DAY,
    PACK_FILE,
    RAW_DIR,
    SCENES_DIR,
    output_day_dir,
    video_stem,
)
from src.build_data import build_pack  # noqa: E402
from src.date_check import confirm_use_data  # noqa: E402
from src.fetch import (  # noqa: E402
    download_boards_fflow,
    load_boards,
    peek_data_date,
    peek_point_count,
)
from src.bgm import ACTIVE_BGM, ensure_library, print_library, resolve_active, resolve_choice  # noqa: E402
from src.mux_audio import mux_bgm, which  # noqa: E402


def check_environment() -> None:
    print("[env] Python", sys.version.split()[0])
    try:
        import manim  # noqa: F401
        import numpy  # noqa: F401

        print("[env] manim / numpy OK")
    except ImportError as e:
        raise SystemExit(
            f"缺少 Python 依赖: {e}\n请先执行: pip install -r requirements.txt"
        ) from e

    if not which("ffmpeg") or not which("ffprobe"):
        raise SystemExit(
            "未检测到 ffmpeg/ffprobe。\n"
            "请安装 FFmpeg 并确保命令行可运行 ffmpeg：\n"
            "  https://ffmpeg.org/download.html"
        )
    print("[env] ffmpeg OK")

    if not BOARDS_FILE.exists():
        raise SystemExit(f"缺少板块名单: {BOARDS_FILE}")
    ensure_library()
    try:
        cur = resolve_active()
        print(f"[env] 当前 BGM: {cur}  （换歌：覆盖 assets\\bgm.mp3）")
    except SystemExit:
        print(f"[env] 警告: 缺少 {ACTIVE_BGM}，将输出无声视频")


def use_sample_data() -> None:
    """Copy bundled 2026-08-10 example into working data dirs."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if EXAMPLE_RAW.exists():
        for p in EXAMPLE_RAW.glob("fflow_BK*.json"):
            shutil.copy2(p, RAW_DIR / p.name)
        print(f"[sample] raw <- {EXAMPLE_RAW}")
    if EXAMPLE_PACK.exists():
        shutil.copy2(EXAMPLE_PACK, PACK_FILE)
        print(f"[sample] pack <- {EXAMPLE_PACK}")
    else:
        raise SystemExit(f"缺少案例数据: {EXAMPLE_PACK}")


def render_video(quality: str, fps: int) -> Path:
    """Run Manim and return path to silent mp4."""
    scene = SCENES_DIR / "fund_flow_overlay.py"
    if not scene.exists():
        raise SystemExit(f"缺少场景文件: {scene}")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["FUND_FLOW_DATA"] = str(PACK_FILE)
    env["FUND_FLOW_FPS"] = str(fps)

    cmd = [
        sys.executable,
        "-m",
        "manim",
        quality,
        "--fps",
        str(fps),
        "--disable_caching",
        "--media_dir",
        str(MEDIA_DIR),
        str(scene),
        "FundFlowOverlay",
    ]
    print("[render]", " ".join(cmd))
    est = "约 8–18 分钟" if fps <= 30 else "约 15–30 分钟"
    print(f"[render] 2K（1440×2560 @{fps}fps），{est}，请耐心等待…")
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)

    # Manim CE names folder by pixel_height + fps, e.g. 2560p60
    candidates = sorted(
        MEDIA_DIR.glob("videos/fund_flow_overlay/*/FundFlowOverlay.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit("渲染完成但未找到输出 mp4，请检查 media/ 目录。")
    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="生成概念板块主力资金流向竖屏视频")
    ap.add_argument("--sample", action="store_true", help="使用内置 2026-08-10 案例，不联网")
    ap.add_argument("--yes", "-y", action="store_true", help="日期不符时不询问，直接继续")
    ap.add_argument("--force-fetch", action="store_true", help="强制重新下载（忽略本地缓存）")
    ap.add_argument("--no-render", action="store_true", help="只拉数/打包，不渲染")
    ap.add_argument("--no-bgm", action="store_true", help="不混合背景音乐")
    ap.add_argument(
        "--bgm",
        type=str,
        default="",
        help="本次 BGM：序号/文件名/路径（默认用曲库当前选择）",
    )
    ap.add_argument("--list-bgm", action="store_true", help="列出 assets/bgm 曲库后退出")
    ap.add_argument("--ql", action="store_true", help="低清快速预览")
    ap.add_argument("--qh", action="store_true", help="高清（默认）")
    ap.add_argument(
        "--smooth",
        action="store_true",
        help="60fps（更丝滑，渲染约慢一倍；默认 30fps）",
    )
    ap.add_argument(
        "--keep-silent",
        action="store_true",
        help="额外保留无声 mp4（默认只留带 BGM 成片）",
    )
    args = ap.parse_args()

    if args.list_bgm:
        print_library()
        print(f"当前默认: {resolve_active().name}")
        return 0

    print("=" * 48)
    print("  概念板块主力资金流向 · 日更视频")
    print("=" * 48)
    check_environment()

    boards = load_boards(BOARDS_FILE)
    print(f"[boards] 固定跟踪 {len(boards)} 个概念板块（见 boards.json）")

    if args.sample:
        use_sample_data()
        # rebuild pack from sample raw so title/date stay consistent
        pack = build_pack(boards, RAW_DIR, PACK_FILE)
    else:
        print("[fetch] 正在从东方财富拉取分时主力净流入…")
        ok, failed = download_boards_fflow(
            boards, RAW_DIR, force=args.force_fetch
        )
        if len(ok) < max(8, len(boards) // 2):
            print(
                f"\n[fetch] 成功过少（{len(ok)}/{len(boards)}）。\n"
                "网络可能被断开。可稍后重试，或先用案例：\n"
                "  python run.py --sample\n"
            )
            if failed:
                print("失败代码:", ", ".join(failed[:12]), ("…" if len(failed) > 12 else ""))
            return 1
        if failed:
            print(f"[fetch] 警告: {len(failed)} 个板块失败，将用成功的继续。")

        data_date = peek_data_date(RAW_DIR)
        n_points = peek_point_count(RAW_DIR)
        if not data_date:
            raise SystemExit("无法从原始数据解析交易日期。")
        if not confirm_use_data(
            data_date,
            n_points=n_points,
            min_full=MIN_POINTS_FULL_DAY,
            assume_yes=args.yes,
        ):
            return 2
        pack = build_pack(boards, RAW_DIR, PACK_FILE, date=data_date)

    date = pack["date"]
    day_dir = output_day_dir(date)
    day_dir.mkdir(parents=True, exist_ok=True)
    # Archive today's pack beside the video for easy handoff
    pack_archive = day_dir / "concept_fflow_major.json"
    shutil.copy2(PACK_FILE, pack_archive)
    print(f"[output] 日期目录: {day_dir}")

    if args.no_render:
        print("[done] 已生成数据，跳过渲染。")
        print(f"  工作数据: {PACK_FILE}")
        print(f"  归档数据: {pack_archive}")
        return 0

    quality = "-ql" if args.ql else "-qh"
    fps = 60 if args.smooth else FRAME_RATE
    silent = render_video(quality, fps=fps)
    stem = video_stem()  # e.g. FundFlowOverlay_2026-08-11_124630（产出真实日期+时刻）
    final_out = day_dir / f"{stem}.mp4"
    silent_out = day_dir / f"{stem}_silent.mp4"

    if args.no_bgm:
        shutil.copy2(silent, final_out)
        print(f"[done] 无声成片: {final_out}")
    else:
        try:
            bgm_path = resolve_choice(args.bgm) if args.bgm else resolve_active()
        except SystemExit as e:
            print(f"[env] {e}")
            shutil.copy2(silent, final_out)
            print(f"[done] 无声成片: {final_out}")
        else:
            print(f"[mux] BGM: {bgm_path.name}")
            # 直接从 Manim 输出混音，避免多拷一份
            mux_bgm(
                silent,
                bgm_path,
                final_out,
                volume=BGM_VOLUME,
                fade_out=BGM_FADE_OUT,
            )
            print(f"[done] 成片: {final_out}")
            if args.keep_silent:
                shutil.copy2(silent, silent_out)
                print(f"[done] 无声备份: {silent_out}")

    if EXAMPLE_VIDEO.exists():
        print(f"[tip] 案例参考（2026-08-10）: {EXAMPLE_VIDEO}")
    print(f"完成。请查看: {day_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
