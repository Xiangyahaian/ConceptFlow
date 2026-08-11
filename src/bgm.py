"""BGM: 默认用 assets/bgm.mp3；曲库里可多存几首备选。"""

from __future__ import annotations

import shutil
from pathlib import Path

from config import ASSETS_DIR, ROOT

# 当前正在使用的那一首（换歌就覆盖它）
ACTIVE_BGM = ASSETS_DIR / "bgm.mp3"
# 备选曲库（只存放，不自动播放）
LIBRARY_DIR = ASSETS_DIR / "bgm_library"
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}

# 兼容旧版 assets/bgm/ 目录
OLD_LIB = ASSETS_DIR / "bgm"


def ensure_library() -> Path:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    # 迁移旧曲库
    if OLD_LIB.is_dir():
        for p in OLD_LIB.iterdir():
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
                dest = LIBRARY_DIR / p.name
                if not dest.exists():
                    shutil.copy2(p, dest)
        default_old = OLD_LIB / "default.mp3"
        if default_old.exists() and not ACTIVE_BGM.exists():
            shutil.copy2(default_old, ACTIVE_BGM)
    return LIBRARY_DIR


def resolve_active() -> Path:
    ensure_library()
    if ACTIVE_BGM.exists():
        return ACTIVE_BGM.resolve()
    # 曲库里随便找一首顶上
    tracks = list_library()
    if tracks:
        shutil.copy2(tracks[0], ACTIVE_BGM)
        return ACTIVE_BGM.resolve()
    raise SystemExit(
        f"还没有背景音乐。\n"
        f"请把一首 mp3 复制到这里并命名为 bgm.mp3：\n  {ACTIVE_BGM}"
    )


def list_library() -> list[Path]:
    ensure_library()
    return [
        p
        for p in sorted(LIBRARY_DIR.iterdir(), key=lambda x: x.name.lower())
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS
    ]


def use_from_library(choice: str) -> Path:
    """把曲库里的某一首复制成 assets/bgm.mp3（设为当前）。"""
    tracks = list_library()
    choice = (choice or "").strip().strip('"').strip("'")
    if not tracks:
        raise SystemExit(f"曲库是空的，请先把 mp3 放进：{LIBRARY_DIR}")

    if choice.isdigit():
        idx = int(choice)
        if not (1 <= idx <= len(tracks)):
            raise SystemExit(f"序号无效：{choice}")
        src = tracks[idx - 1]
    else:
        src = None
        key = choice.lower()
        p = Path(choice).expanduser()
        if p.exists() and p.is_file():
            src = p.resolve()
        else:
            for t in tracks:
                if t.name.lower() == key or t.stem.lower() == key or key in t.stem.lower():
                    src = t
                    break
        if src is None:
            raise SystemExit(f"曲库里找不到：{choice}")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, ACTIVE_BGM)
    return ACTIVE_BGM.resolve()


def resolve_choice(choice: str) -> Path:
    """本次渲染用哪首：空=当前 bgm.mp3；否则路径/曲库名/序号。"""
    choice = (choice or "").strip().strip('"').strip("'")
    if not choice:
        return resolve_active()

    p = Path(choice).expanduser()
    if p.exists() and p.is_file():
        return p.resolve()
    for base in (Path.cwd(), ROOT, LIBRARY_DIR, ASSETS_DIR):
        cand = (base / choice).resolve()
        if cand.exists() and cand.is_file():
            return cand

    # 曲库序号或名字（仅本次，不改写 bgm.mp3）
    tracks = list_library()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(tracks):
            return tracks[idx - 1]
    key = choice.lower()
    for t in tracks:
        if t.name.lower() == key or t.stem.lower() == key or key in t.stem.lower():
            return t

    raise SystemExit(f"找不到 BGM：{choice}")


def print_library(*, mark_active: bool = True) -> list[Path]:
    tracks = list_library()
    print(f"当前使用: {ACTIVE_BGM}")
    print(f"  -> {ACTIVE_BGM.name if ACTIVE_BGM.exists() else '（还没有，请放一个 bgm.mp3）'}")
    print(f"备选曲库: {LIBRARY_DIR}")
    if not tracks:
        print("  （空）")
        return tracks
    for i, t in enumerate(tracks, 1):
        print(f"  [{i}] {t.name}")
    return tracks
