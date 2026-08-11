"""Mux BGM onto silent Manim output with ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def probe_duration(video: Path) -> float:
    ffprobe = which("ffprobe")
    if not ffprobe:
        raise SystemExit("未找到 ffprobe，请安装 FFmpeg 并加入 PATH。")
    out = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video),
        ],
        text=True,
    ).strip()
    return float(out)


def mux_bgm(
    silent_video: Path,
    bgm: Path,
    out_video: Path,
    *,
    volume: float = 0.55,
    fade_out: float = 1.2,
) -> Path:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("未找到 ffmpeg，请安装 FFmpeg 并加入 PATH。")
    if not silent_video.exists():
        raise FileNotFoundError(silent_video)
    if not bgm.exists():
        raise FileNotFoundError(bgm)

    dur = probe_duration(silent_video)
    fade_start = max(0.0, dur - fade_out)
    out_video.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_video.with_suffix(".tmp.mp4")

    filter_complex = (
        f"[1:a]atrim=0:{dur:.3f},afade=t=out:st={fade_start:.3f}:d={fade_out:.3f},"
        f"volume={volume}[a]"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(bgm),
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(tmp),
    ]
    print("[mux]", " ".join(cmd))
    subprocess.run(cmd, check=True)
    tmp.replace(out_video)
    print(f"[mux] -> {out_video}")
    return out_video
